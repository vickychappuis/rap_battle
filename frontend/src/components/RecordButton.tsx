/**
 * RecordButton - Main action button for battle flow.
 *
 * Handles: Start Battle, Record, Retry, Start Over, New Battle
 */

import type { SessionState } from '../hooks/useSession';

interface RecordButtonProps {
  state: SessionState;
  hasSession: boolean;
  currentRound: number;
  retryCount: number;
  onStartBattle: () => void;
  onStartRecording: () => void;
  onRetry: () => void;
  onStartOver: () => void;
}

export function RecordButton({
  state,
  hasSession,
  currentRound,
  retryCount,
  onStartBattle,
  onStartRecording,
  onRetry,
  onStartOver,
}: RecordButtonProps) {
  const isIdle = state === 'idle';
  const isAwaitingUser = state === 'awaiting_user';
  const isComplete = state === 'complete';
  const isError = state === 'error';

  const canStartBattle = isIdle && !hasSession;
  const canRecord = (isIdle && hasSession) || isAwaitingUser;
  const canRestart = isComplete;
  // retryCount > 0 means backend pipeline failed (can retry)
  // retryCount === 0 means frontend error (just try recording again)
  const canRetry = isError && retryCount > 0 && retryCount < 2;
  const canStartOver = isError && retryCount >= 2;
  const canTryAgain = isError && retryCount === 0; // Frontend-only error

  const isDisabled = !canStartBattle && !canRecord && !canRestart && !canRetry && !canStartOver && !canTryAgain;

  const handleClick = () => {
    if (canStartBattle || canRestart) {
      onStartBattle();
    } else if (canRecord || canTryAgain) {
      onStartRecording();
    } else if (canRetry) {
      onRetry();
    } else if (canStartOver) {
      onStartOver();
    }
  };

  const getLabel = () => {
    if (canStartBattle) return 'Start Battle';
    if (canRecord) {
      return currentRound === 1 && !hasSession
        ? 'Record'
        : `Record Round ${currentRound}`;
    }
    if (canRestart) return 'New Battle';
    if (canTryAgain) return 'Try Again';
    if (canRetry) return 'Retry';
    if (canStartOver) return 'Start Over';
    if (state === 'recording') return 'Recording...';
    if (state === 'processing') return 'Processing...';
    if (state === 'playing_response') return 'Playing...';
    return 'Wait...';
  };

  // Show secondary "Start Over" button when retry/try again is available
  const showStartOverSecondary = isError && retryCount < 2;

  const primaryClasses = [
    'btn-primary',
    'animate-in',
    state === 'recording' ? 'recording' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={handleClick}
        disabled={isDisabled}
        className={`${primaryClasses} w-full`}
      >
        {getLabel()}
      </button>

      {showStartOverSecondary && (
        <button
          onClick={onStartOver}
          className="btn-secondary animate-in animate-in--delay-1 w-full"
        >
          Start Over
        </button>
      )}
    </div>
  );
}
