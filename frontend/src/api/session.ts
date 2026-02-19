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
}

const API_BASE = '/api/session';

export function getInviteCode(): string | null {
  return localStorage.getItem('invite_code');
}

export async function validateInviteCode(code: string): Promise<void> {
  const response = await fetch('/api/access/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ invite_code: code }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Invalid invite code');
  }
}

export async function createSession(): Promise<SessionResponse> {
  const code = getInviteCode();
  if (!code) {
    throw new Error('No invite code. Please authenticate first.');
  }

  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Invite-Code': code,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('invite_code');
      throw new Error('Invalid invite code. Please try again.');
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
