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
  connecting: 'Starting...',
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
  if (state === 'idle') return null;
  if (state === 'connecting') return <div className="card text-center"><span className="stamp">Starting...</span></div>;

  const label = STATE_LABELS[state];
  const isRecording = state === 'recording';
  const isError = state === 'error';
  const showTurnIndicator = state !== 'complete';

  return (
    <div className="card text-center">
      <span
        className={`stamp ${isRecording ? 'recording text-spray-paint-red' : ''} ${isError ? 'text-spray-paint-red' : ''}`}
      >
        {label}
      </span>

      {showTurnIndicator && (
        <div className="turn-indicator mt-4 text-sm">
          <span className="text-xerox-gray">
            Round {currentRound} of {turnsPerPlayer}
          </span>
          {state === 'awaiting_user' && (
            <span className="ml-2">- Your Turn</span>
          )}
          {state === 'processing' && (
            <span className="ml-2">- AI Thinking...</span>
          )}
          {state === 'playing_response' && (
            <span className="ml-2">- AI's Turn</span>
          )}
        </div>
      )}

      {isRecording && countdown > 0 && (
        <div className="mt-4">
          <div className="countdown-circle recording">{countdown}</div>
        </div>
      )}
    </div>
  );
}
