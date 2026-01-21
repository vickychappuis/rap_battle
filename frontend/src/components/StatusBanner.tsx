/**
 * StatusBanner - Displays current session state and turn info.
 */

import type { SessionState } from '../hooks/useSession';

interface StatusBannerProps {
  state: SessionState;
  countdown: number;
  currentRound: number;
  turnsPerPlayer: number;
}

const STATE_LABELS: Record<SessionState, string> = {
  idle: 'Ready',
  awaiting_user: 'Your Turn',
  recording: 'Recording',
  processing: 'Processing',
  playing_response: 'AI Responding',
  complete: 'Battle Complete',
  error: 'Error',
};

export function StatusBanner({
  state,
  countdown,
  currentRound,
  turnsPerPlayer,
}: StatusBannerProps) {
  const label = STATE_LABELS[state];
  const isRecording = state === 'recording';
  const isError = state === 'error';
  const showTurnIndicator = state !== 'idle' && state !== 'complete';

  return (
    <div className="card text-center">
      <span
        className={`stamp ${isRecording ? 'recording text-red' : ''} ${isError ? 'text-red' : ''}`}
      >
        {label}
      </span>

      {showTurnIndicator && (
        <div className="turn-indicator mt-2" style={{ fontSize: '0.9rem' }}>
          <span className="text-gray">
            Round {currentRound} of {turnsPerPlayer}
          </span>
          {state === 'awaiting_user' && (
            <span style={{ marginLeft: '0.5rem' }}>- Your Turn</span>
          )}
          {state === 'processing' && (
            <span style={{ marginLeft: '0.5rem' }}>- AI Thinking...</span>
          )}
          {state === 'playing_response' && (
            <span style={{ marginLeft: '0.5rem' }}>- AI's Turn</span>
          )}
        </div>
      )}

      {isRecording && countdown > 0 && (
        <div className="mt-2">
          <div className="countdown-circle recording">{countdown}</div>
        </div>
      )}
    </div>
  );
}
