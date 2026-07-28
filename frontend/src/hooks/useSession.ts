/**
 * useSession - State machine hook for multi-turn session management.
 *
 * State flow:
 * idle
 *   -> recording (turn 1, user clicks "Start Battle")
 *   -> processing
 *   -> playing_response
 *   -> awaiting_user (turn 2, user clicks "Record")
 *   -> recording
 *   -> processing
 *   -> playing_response
 *   -> ... (repeat for remaining turns)
 *   -> complete
 *
 * At any processing step:
 *   -> error (with retry_count)
 *     -> processing (if retry)
 *     -> idle (if start over)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  ApiError,
  createSession,
  uploadRecording,
  getSessionStatus,
  retryTurn as retryTurnApi,
} from '../api/session';
import type {
  OpponentPersonaPayload,
  SessionResponse,
  SessionStatus,
  TurnData,
} from '../api/session';
import { useAudioEngine } from './useAudioEngine';

export type SessionState =
  | 'idle'
  | 'connecting'
  | 'awaiting_user'
  | 'recording'
  | 'processing'
  | 'playing_response'
  | 'judging'
  | 'complete'
  | 'error';

export interface UseSessionReturn {
  state: SessionState;
  sessionData: SessionResponse | null;
  status: SessionStatus | null;
  error: string | null;
  countdown: number;

  // Multi-turn fields
  currentTurn: number;
  totalTurns: number;
  turnHistory: TurnData[];
  currentRound: number;
  isUserTurn: boolean;
  isFinalRound: boolean;
  retryCount: number;
  winner: string | null;
  judgeReason: string | null;

  // Actions
  startBattle: (opponent?: OpponentPersonaPayload) => Promise<void>;
  startRecording: () => Promise<void>;
  retryTurn: () => Promise<void>;
  startOver: () => void;
}

const POLL_INTERVAL_MS = 1000;

/**
 * Polling resilience: a single failed status request is usually a blip (server
 * restart, flaky wifi), so we retry with exponential backoff instead of killing
 * a battle in progress. After MAX_POLL_FAILURES consecutive failures the
 * backend is considered down and the error is surfaced to the player.
 * Delays: 1s, 2s, 4s, 8s -> ~15s of tolerance before giving up.
 */
const MAX_POLL_FAILURES = 5;
const MAX_POLL_BACKOFF_MS = 8000;

/**
 * Retry budget for a failed turn. Mirrors the backend, which rejects
 * POST /retry once retry_count reaches 2 ("Maximum retries exceeded").
 */
export const MAX_TURN_RETRIES = 2;

const SESSION_GONE_MESSAGE = 'This battle expired. Start a new battle to keep rapping.';
const CONNECTION_LOST_MESSAGE =
  'Lost connection to the battle server. Check your connection and try again.';

/** Exponential backoff for the Nth consecutive failure (1-indexed). */
function pollBackoffMs(consecutiveFailures: number): number {
  return Math.min(POLL_INTERVAL_MS * 2 ** (consecutiveFailures - 1), MAX_POLL_BACKOFF_MS);
}

/**
 * True for failures that retrying cannot fix (session gone, bad request).
 * Network/parse errors carry no status and are treated as transient, as are
 * 408 (timeout), 429 (rate limit) and every 5xx.
 */
function isFatalPollError(err: unknown): err is ApiError {
  if (!(err instanceof ApiError)) return false;
  if (err.status === 408 || err.status === 429) return false;
  return err.status >= 400 && err.status < 500;
}

export function useSession(): UseSessionReturn {
  const [state, setState] = useState<SessionState>('idle');
  const [sessionData, setSessionData] = useState<SessionResponse | null>(null);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);

  const pollTimeoutRef = useRef<number | null>(null);
  // Epoch token: bumped by every stopPolling()/startPolling(). A poll chain
  // captures it and re-checks it after each await, so a chain that was
  // cancelled (or superseded by a newer session) can never write state again.
  const pollGenerationRef = useRef(0);
  const pollFailuresRef = useRef(0);
  const stateRef = useRef<SessionState>('idle');
  const audioScheduledForTurnRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);
  const { startBaseTrack, recordAudio, scheduleAiResponse, stop: stopAudio } = useAudioEngine();

  // Derived multi-turn values
  const currentTurn = status?.current_turn ?? 1;
  const turnsPerPlayer = sessionData?.turns_per_player ?? 2;
  const totalTurns = turnsPerPlayer * 2;
  const turnHistory = status?.turn_history ?? [];
  const currentRound = Math.ceil(currentTurn / 2);
  const isUserTurn = currentTurn % 2 === 1;
  const isFinalRound = currentRound === turnsPerPlayer;
  const retryCount = status?.retry_count ?? 0;
  const winner = status?.winner ?? null;
  const judgeReason = status?.judge_reason ?? null;

  const setStateTracked = useCallback((next: SessionState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const startCountdown = useCallback((seconds: number) => {
    if (countdownIntervalRef.current !== null) {
      clearInterval(countdownIntervalRef.current);
    }
    setCountdown(seconds);
    countdownIntervalRef.current = window.setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownIntervalRef.current!);
          countdownIntervalRef.current = null;
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const clearCountdown = useCallback(() => {
    if (countdownIntervalRef.current !== null) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  }, []);

  // Clear polling: cancels the pending timer and invalidates any in-flight poll
  const stopPolling = useCallback(() => {
    pollGenerationRef.current += 1;
    if (pollTimeoutRef.current !== null) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
    clearCountdown();
  }, [clearCountdown]);

  // Poll for status updates using serialized setTimeout chain
  const startPolling = useCallback(
    (sessionId: string) => {
      stopPolling();
      pollFailuresRef.current = 0;

      // This chain owns the current epoch until something else bumps it.
      let generation = pollGenerationRef.current;
      const isCurrent = () => generation === pollGenerationRef.current;

      // End the chain from inside itself (terminal step reached) while keeping
      // ownership, so the code after the awaits below still gets to run.
      const endChain = () => {
        stopPolling();
        generation = pollGenerationRef.current;
      };

      const pollOnce = async () => {
        if (!isCurrent()) return;

        let nextDelayMs = POLL_INTERVAL_MS;

        try {
          const newStatus = await getSessionStatus(sessionId);
          if (!isCurrent()) return;

          pollFailuresRef.current = 0;
          setStatus(newStatus);

          const shouldPlayAudio =
            newStatus.ai_audio_url &&
            audioScheduledForTurnRef.current !== newStatus.current_turn;

          // Plays the AI verse and waits it out. Returns false if this chain
          // was cancelled while the audio was playing.
          const playResponse = async (url: string, turn: number) => {
            audioScheduledForTurnRef.current = turn;
            setStateTracked('playing_response');
            const { durationSec, done } = await scheduleAiResponse(url);
            if (!isCurrent()) return false;
            startCountdown(durationSec);
            await done;
            return isCurrent();
          };

          if (newStatus.step === 'judging') {
            if (shouldPlayAudio && stateRef.current !== 'judging') {
              if (!(await playResponse(newStatus.ai_audio_url!, newStatus.current_turn))) return;
            }
            setStateTracked('judging');
          } else if (newStatus.step === 'complete') {
            endChain();
            if (shouldPlayAudio && stateRef.current !== 'judging') {
              if (!(await playResponse(newStatus.ai_audio_url!, newStatus.current_turn))) return;
            }
            setStateTracked('complete');
            return;
          } else if (newStatus.step === 'awaiting_user') {
            endChain();
            if (shouldPlayAudio) {
              if (!(await playResponse(newStatus.ai_audio_url!, newStatus.current_turn))) return;
            }
            setStateTracked('awaiting_user');
            return;
          } else if (newStatus.step === 'error') {
            endChain();
            // With retries left the beat keeps looping, so a /retry resumes
            // into the same musical timeline. Once the budget is spent the
            // only way forward is a brand new battle, so stop the music
            // rather than loop it under a dead-end banner.
            if ((newStatus.retry_count ?? 0) >= MAX_TURN_RETRIES) {
              stopAudio();
            }
            setError(newStatus.error || 'Unknown error');
            setStateTracked('error');
            return;
          }
        } catch (err) {
          console.error('Polling error:', err);

          // Terminal transport failure: the battle cannot continue. Kill the
          // beat, drop the session so the only offered action is a fresh
          // battle (which re-arms the audio engine via startBaseTrack).
          const failBattle = (message: string) => {
            endChain();
            stopAudio();
            setSessionData(null);
            setError(message);
            setStateTracked('error');
          };

          // The session no longer exists server-side (evicted / TTL expired).
          if (err instanceof ApiError && err.status === 404) {
            failBattle(SESSION_GONE_MESSAGE);
            return;
          }

          // Other client errors won't succeed on retry either.
          if (isFatalPollError(err)) {
            failBattle(err.message);
            return;
          }

          // Transient: back off, and give up once the backend stays unreachable.
          pollFailuresRef.current += 1;
          if (pollFailuresRef.current >= MAX_POLL_FAILURES) {
            failBattle(CONNECTION_LOST_MESSAGE);
            return;
          }
          nextDelayMs = pollBackoffMs(pollFailuresRef.current);
        }

        // Schedule next poll only after this one fully completes
        if (isCurrent()) {
          pollTimeoutRef.current = window.setTimeout(pollOnce, nextDelayMs);
        }
      };

      pollTimeoutRef.current = window.setTimeout(pollOnce, POLL_INTERVAL_MS);
    },
    [stopPolling, scheduleAiResponse, setStateTracked, startCountdown, stopAudio]
  );

  // Shared recording logic — takes session directly to avoid React state timing issues
  const doRecording = useCallback(async (session: SessionResponse) => {
    setStateTracked('recording');
    startCountdown(session.record_duration);

    const audioBlob = await recordAudio(session.record_duration * 1000);
    await uploadRecording(session.session_id, audioBlob);

    setStateTracked('processing');
    startPolling(session.session_id);
  }, [recordAudio, startPolling, setStateTracked, startCountdown]);

  // Start a new battle (creates session + starts base track + immediately starts recording)
  const startBattle = useCallback(async (opponent?: OpponentPersonaPayload) => {
    try {
      setError(null);
      setStateTracked('connecting');
      setStatus(null);
      setSessionData(null);
      audioScheduledForTurnRef.current = null;

      const session = await createSession(opponent);
      setSessionData(session);

      await startBaseTrack(session.base_track_url, session.bpm);
      await doRecording(session);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start battle';
      setError(message);
      setStateTracked('error');
    }
  }, [startBaseTrack, doRecording, setStateTracked]);

  // Start recording for subsequent turns
  const startRecording = useCallback(async () => {
    if (!sessionData) {
      setError('No session created');
      setStateTracked('error');
      return;
    }

    try {
      setError(null);
      await doRecording(sessionData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recording failed');
      setStateTracked('error');
    }
  }, [sessionData, doRecording, setStateTracked]);

  // Retry current turn after error
  const retryTurn = useCallback(async () => {
    if (!sessionData) {
      setError('No session created');
      return;
    }

    try {
      setError(null);
      const result = await retryTurnApi(sessionData.session_id);

      if (result.status === 'need_rerecord') {
        setStateTracked('awaiting_user');
        setError(result.message || 'Please record again');
      } else {
        setStateTracked('processing');
        startPolling(sessionData.session_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retry failed');
      setStateTracked('error');
    }
  }, [sessionData, startPolling, setStateTracked]);

  // Start over (reset everything)
  const startOver = useCallback(() => {
    stopPolling();
    stopAudio();
    setStateTracked('idle');
    setSessionData(null);
    setStatus(null);
    setError(null);
    setCountdown(0);
    audioScheduledForTurnRef.current = null;
  }, [stopPolling, stopAudio, setStateTracked]);

  // Cleanup on unmount (stopPolling also clears the countdown interval and
  // invalidates any in-flight poll waiting on audio playback)
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    state,
    sessionData,
    status,
    error,
    countdown,

    // Multi-turn fields
    currentTurn,
    totalTurns,
    turnHistory,
    currentRound,
    isUserTurn,
    isFinalRound,
    retryCount,
    winner,
    judgeReason,

    // Actions
    startBattle,
    startRecording,
    retryTurn,
    startOver,
  };
}
