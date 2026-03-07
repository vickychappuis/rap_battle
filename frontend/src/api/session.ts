/**
 * API client for session management.
 */

export interface SessionResponse {
  session_id: string;
  bpm: number;
  bars_per_turn: number;
  turns_per_player: number;
  record_duration: number;
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

const API_BASE = '/api/session';

export async function createSession(opponentName?: string): Promise<SessionResponse> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ opponent_name: opponentName }),
  });

  if (!response.ok) {
    if (response.status === 429) {
      const err = await response.json().catch(() => ({ detail: 'Rate limit exceeded' }));
      throw new Error(err.detail || 'Too many battles. Try again later.');
    }
    throw new Error(`Failed to create session: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadRecording(sessionId: string, audioBlob: Blob): Promise<void> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');

  const response = await fetch(`${API_BASE}/${sessionId}/recording`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to upload recording');
  }
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  const response = await fetch(`${API_BASE}/${sessionId}/status`);

  if (!response.ok) {
    throw new Error(`Failed to get session status: ${response.statusText}`);
  }

  return response.json();
}

export async function retryTurn(sessionId: string): Promise<{ status: string; retry_count?: number; message?: string }> {
  const response = await fetch(`${API_BASE}/${sessionId}/retry`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to retry');
  }

  return response.json();
}
