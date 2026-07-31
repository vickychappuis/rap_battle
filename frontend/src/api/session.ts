/**
 * API client for session management.
 */

export interface SessionResponse {
  session_id: string;
  bpm: number;
  bars_per_turn: number;
  turns_per_player: number;
  record_duration: number;
  /** Turn retry budget; the backend rejects POST /retry beyond this count. */
  max_turn_retries: number;
  base_track_url: string;
}

export interface TurnData {
  turn_number: number;
  player: 'user' | 'ai';
  transcription?: string;
  lyrics?: string;
  audio_url?: string;
}

export interface SessionStatus {
  step:
    | 'idle'
    | 'awaiting_user'
    | 'recording'
    | 'transcribing'
    | 'generating_lyrics'
    | 'generating_audio'
    | 'playing_response'
    | 'judging'
    | 'complete'
    | 'error';
  current_turn: number;
  turns_per_player: number;
  turn_history: TurnData[];
  transcription?: string;
  lyrics?: string;
  ai_audio_url?: string;
  error?: string;
  retry_count?: number;
  winner?: string;
  judge_reason?: string;
}

/**
 * Error carrying the HTTP status of a failed API response, so callers can tell
 * a permanent failure (404 - session gone) from a transient one (500, network).
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const API_BASE = '/api/session';

/**
 * Shown when the API cannot be reached at all, as opposed to answering with a
 * problem. Two cases produce it: a rejected fetch (nothing on the other end)
 * and a 502/503/504, which comes from the proxy in front of the API rather
 * than from the API itself. A free backend that has been suspended or has
 * spun down looks exactly like this, and "Service Unavailable" is not
 * something a player should be asked to read.
 */
const ARENA_DOWN_MESSAGE =
  'The arena is closed right now — the battle server is down. Try again later.';

function isArenaDown(status: number): boolean {
  return status === 502 || status === 503 || status === 504;
}

/** fetch(), but a transport failure reads as "the arena is closed". */
async function reachApi(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error(ARENA_DOWN_MESSAGE);
  }
}

/**
 * The AI opponent's character sheet, in the snake_case shape the API expects.
 * Every field is optional server-side, and the whole object may be omitted -
 * a session created without one just battles a nameless MC.
 */
export interface OpponentPersonaPayload {
  name?: string;
  age?: number;
  claims?: string;
  reality?: string;
  extra_info?: string;
}

export async function createSession(
  opponent?: OpponentPersonaPayload
): Promise<SessionResponse> {
  const response = await reachApi(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // `opponent_name` is sent alongside the persona so older/simpler clients
    // (and the backend's fallback path) keep working unchanged.
    body: JSON.stringify({ opponent_name: opponent?.name, opponent }),
  });

  if (!response.ok) {
    if (response.status === 429) {
      const err = await response.json().catch(() => ({ detail: 'Rate limit exceeded' }));
      throw new Error(err.detail || 'Too many battles. Try again later.');
    }
    if (isArenaDown(response.status)) throw new Error(ARENA_DOWN_MESSAGE);
    throw new Error(`Failed to create session: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadRecording(sessionId: string, audioBlob: Blob): Promise<void> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');

  const response = await reachApi(`${API_BASE}/${sessionId}/recording`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    if (isArenaDown(response.status)) throw new Error(ARENA_DOWN_MESSAGE);
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to upload recording');
  }
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  const response = await fetch(`${API_BASE}/${sessionId}/status`);

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(
      error?.detail || `Failed to get session status: ${response.statusText}`,
      response.status
    );
  }

  return response.json();
}

export async function retryTurn(sessionId: string): Promise<{ status: string; retry_count?: number; message?: string }> {
  const response = await reachApi(`${API_BASE}/${sessionId}/retry`, {
    method: 'POST',
  });

  if (!response.ok) {
    if (isArenaDown(response.status)) throw new Error(ARENA_DOWN_MESSAGE);
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to retry');
  }

  return response.json();
}
