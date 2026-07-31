/**
 * Tests for the useSession state machine: battle flow, polling resilience
 * and error recovery. The API client and the audio engine are mocked; the
 * hook's real state transitions and timers run under fake timers.
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';

import { useSession } from './useSession';
import {
  ApiError,
  createSession,
  getSessionStatus,
  uploadRecording,
} from '../api/session';
import type { SessionResponse, SessionStatus } from '../api/session';

vi.mock('../api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/session')>();
  return {
    ...actual,
    createSession: vi.fn(),
    uploadRecording: vi.fn(),
    getSessionStatus: vi.fn(),
    retryTurn: vi.fn(),
  };
});

const audioEngine = vi.hoisted(() => ({
  startBaseTrack: vi.fn<(url: string, bpm: number) => Promise<void>>(),
  recordAudio: vi.fn<(ms: number) => Promise<Blob>>(),
  scheduleAiResponse:
    vi.fn<(url: string) => Promise<{ durationSec: number; done: Promise<void> }>>(),
  stop: vi.fn<() => void>(),
}));

vi.mock('./useAudioEngine', () => ({
  useAudioEngine: () => audioEngine,
}));

function makeSession(overrides: Partial<SessionResponse> = {}): SessionResponse {
  return {
    session_id: 'session-1',
    bpm: 90,
    bars_per_turn: 16,
    turns_per_player: 2,
    record_duration: 43,
    max_turn_retries: 2,
    base_track_url: '/static/tracks/base_90bpm.mp3',
    ...overrides,
  };
}

function makeStatus(overrides: Partial<SessionStatus> = {}): SessionStatus {
  return {
    step: 'transcribing',
    current_turn: 1,
    turns_per_player: 2,
    turn_history: [],
    ...overrides,
  };
}

/** Run one scheduled poll (the chain schedules the next poll itself). */
async function advancePoll(ms = 1000) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function startBattle(hook: { current: ReturnType<typeof useSession> }) {
  await act(async () => {
    await hook.current.startBattle();
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  (createSession as Mock).mockResolvedValue(makeSession());
  (uploadRecording as Mock).mockResolvedValue(undefined);
  audioEngine.startBaseTrack.mockResolvedValue(undefined);
  audioEngine.recordAudio.mockResolvedValue(new Blob(['audio']));
  audioEngine.scheduleAiResponse.mockResolvedValue({
    durationSec: 5,
    done: Promise.resolve(),
  });
});

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe('useSession', () => {
  it('starts idle with no session', () => {
    const { result } = renderHook(() => useSession());

    expect(result.current.state).toBe('idle');
    expect(result.current.sessionData).toBeNull();
  });

  it('startBattle records a turn and moves into processing', async () => {
    const { result } = renderHook(() => useSession());

    await startBattle(result);

    expect(createSession).toHaveBeenCalledTimes(1);
    expect(audioEngine.startBaseTrack).toHaveBeenCalledWith(
      '/static/tracks/base_90bpm.mp3',
      90
    );
    expect(audioEngine.recordAudio).toHaveBeenCalledWith(43 * 1000);
    expect(uploadRecording).toHaveBeenCalledWith('session-1', expect.any(Blob));
    expect(result.current.state).toBe('processing');
  });

  it('exposes the retry budget reported by the backend', async () => {
    (createSession as Mock).mockResolvedValue(makeSession({ max_turn_retries: 5 }));
    const { result } = renderHook(() => useSession());

    await startBattle(result);

    expect(result.current.maxTurnRetries).toBe(5);
  });

  it('plays the AI verse and hands the mic back on awaiting_user', async () => {
    (getSessionStatus as Mock).mockResolvedValue(
      makeStatus({
        step: 'awaiting_user',
        current_turn: 3,
        ai_audio_url: '/static/generated/turn2.mp3',
      })
    );
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll();

    expect(audioEngine.scheduleAiResponse).toHaveBeenCalledWith(
      '/static/generated/turn2.mp3'
    );
    expect(result.current.state).toBe('awaiting_user');
  });

  it('finishes the battle when the backend reports complete', async () => {
    (getSessionStatus as Mock).mockResolvedValue(
      makeStatus({
        step: 'complete',
        current_turn: 5,
        winner: 'user',
        judge_reason: 'you had the harder bars',
      })
    );
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll();

    expect(result.current.state).toBe('complete');
    expect(result.current.winner).toBe('user');
    expect(result.current.judgeReason).toBe('you had the harder bars');
  });

  it('ends the battle with a friendly message when the session is gone', async () => {
    (getSessionStatus as Mock).mockRejectedValue(
      new ApiError('Session not found', 404)
    );
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll();

    expect(result.current.state).toBe('error');
    expect(result.current.error).toMatch(/expired/i);
    expect(result.current.sessionData).toBeNull();
    expect(audioEngine.stop).toHaveBeenCalled();
  });

  it('rides out transient poll failures with backoff', async () => {
    (getSessionStatus as Mock)
      .mockRejectedValueOnce(new TypeError('network down'))
      .mockRejectedValueOnce(new TypeError('network down'))
      .mockResolvedValue(makeStatus({ step: 'awaiting_user', current_turn: 3 }));
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll(1000); // failure 1 -> retry in 1s
    await advancePoll(1000); // failure 2 -> retry in 2s
    await advancePoll(2000); // success

    expect(result.current.state).toBe('awaiting_user');
  });

  it('gives up after enough consecutive poll failures', async () => {
    (getSessionStatus as Mock).mockRejectedValue(new TypeError('network down'));
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    // Backoff schedule: 1s, then retries after 1s, 2s, 4s, 8s -> 5th failure.
    await advancePoll(1000);
    await advancePoll(1000);
    await advancePoll(2000);
    await advancePoll(4000);
    await advancePoll(8000);

    expect(result.current.state).toBe('error');
    expect(result.current.error).toMatch(/lost connection/i);
    expect(audioEngine.stop).toHaveBeenCalled();
  });

  it('keeps the beat looping while the turn can still be retried', async () => {
    (getSessionStatus as Mock).mockResolvedValue(
      makeStatus({ step: 'error', error: 'Attempt 1 failed', retry_count: 1 })
    );
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll();

    expect(result.current.state).toBe('error');
    expect(audioEngine.stop).not.toHaveBeenCalled();
  });

  it('stops the beat once the retry budget is spent', async () => {
    (getSessionStatus as Mock).mockResolvedValue(
      makeStatus({ step: 'error', error: 'Failed after 2 attempts', retry_count: 2 })
    );
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    await advancePoll();

    expect(result.current.state).toBe('error');
    expect(audioEngine.stop).toHaveBeenCalled();
  });

  it('startOver resets everything to idle', async () => {
    const { result } = renderHook(() => useSession());

    await startBattle(result);
    act(() => {
      result.current.startOver();
    });

    expect(result.current.state).toBe('idle');
    expect(result.current.sessionData).toBeNull();
    expect(result.current.error).toBeNull();
    expect(audioEngine.stop).toHaveBeenCalled();
  });
});
