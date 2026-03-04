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
  createSession,
  uploadRecording,
  getSessionStatus,
  retryTurn as retryTurnApi,
} from '../api/session';
import type { SessionResponse, SessionStatus, TurnData } from '../api/session';
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
  startBattle: () => Promise<void>;
  startRecording: () => Promise<void>;
  retryTurn: () => Promise<void>;
  startOver: () => void;
}

const POLL_INTERVAL_MS = 1000;

export function useSession(): UseSessionReturn {
  const [state, setState] = useState<SessionState>('idle');
  const [sessionData, setSessionData] = useState<SessionResponse | null>(null);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);

  const pollIntervalRef = useRef<number | null>(null);
  const { startBaseTrack, recordAudio, scheduleAiResponse } = useAudioEngine();

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

  // Clear polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Poll for status updates
  const startPolling = useCallback(
    (sessionId: string) => {
      stopPolling();

      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const newStatus = await getSessionStatus(sessionId);
          setStatus(newStatus);

          // Handle step transitions
          if (newStatus.step === 'judging') {
            if (newStatus.ai_audio_url && state !== 'judging') {
              setState('playing_response');
              await scheduleAiResponse(newStatus.ai_audio_url);
            }
            setState('judging');
          } else if (newStatus.step === 'complete') {
            stopPolling();
            if (state !== 'judging' && newStatus.ai_audio_url) {
              setState('playing_response');
              await scheduleAiResponse(newStatus.ai_audio_url);
            }
            setState('complete');
          } else if (newStatus.step === 'awaiting_user') {
            stopPolling();
            // AI finished, waiting for next user turn
            if (newStatus.ai_audio_url) {
              setState('playing_response');
              await scheduleAiResponse(newStatus.ai_audio_url);
            }
            setState('awaiting_user');
          } else if (newStatus.step === 'error') {
            stopPolling();
            setError(newStatus.error || 'Unknown error');
            setState('error');
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling, scheduleAiResponse]
  );

  // Shared recording logic — takes session directly to avoid React state timing issues
  const doRecording = useCallback(async (session: SessionResponse) => {
    setState('recording');

    const durationSec = session.record_duration;
    setCountdown(durationSec);

    const countdownInterval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    const audioBlob = await recordAudio(durationSec * 1000);
    await uploadRecording(session.session_id, audioBlob);

    setState('processing');
    startPolling(session.session_id);
  }, [recordAudio, startPolling]);

  // Start a new battle (creates session + starts base track + immediately starts recording)
  const startBattle = useCallback(async () => {
    try {
      setError(null);
      setState('connecting');
      setStatus(null);
      setSessionData(null);

      const session = await createSession();
      setSessionData(session);

      await startBaseTrack(session.base_track_url, session.bpm);
      await doRecording(session);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start battle';
      setError(message);
      setState('error');
    }
  }, [startBaseTrack, doRecording]);

  // Start recording for subsequent turns
  const startRecording = useCallback(async () => {
    if (!sessionData) {
      setError('No session created');
      setState('error');
      return;
    }

    try {
      setError(null);
      await doRecording(sessionData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recording failed');
      setState('error');
    }
  }, [sessionData, doRecording]);

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
        // Audio expired, need to re-record
        setState('awaiting_user');
        setError(result.message || 'Please record again');
      } else {
        // Pipeline restarted
        setState('processing');
        startPolling(sessionData.session_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retry failed');
      setState('error');
    }
  }, [sessionData, startPolling]);

  // Start over (reset everything)
  const startOver = useCallback(() => {
    stopPolling();
    setState('idle');
    setSessionData(null);
    setStatus(null);
    setError(null);
    setCountdown(0);
  }, [stopPolling]);

  // Cleanup on unmount
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
