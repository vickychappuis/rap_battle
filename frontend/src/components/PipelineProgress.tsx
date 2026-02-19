/**
 * PipelineProgress - Shows STT -> Lyrics -> Audio progress steps.
 */

import type { SessionStatus } from '../api/session';

interface PipelineProgressProps {
  status: SessionStatus | null;
}

type Step = 'transcribing' | 'generating_lyrics' | 'generating_audio' | 'complete';

const STEPS: { key: Step; label: string }[] = [
  { key: 'transcribing', label: 'Transcribing' },
  { key: 'generating_lyrics', label: 'Generating Lyrics' },
  { key: 'generating_audio', label: 'Generating Audio' },
  { key: 'complete', label: 'Complete' },
];

function getStepIndex(step: string | undefined): number {
  if (!step) return -1;
  const index = STEPS.findIndex((s) => s.key === step);
  if (index >= 0) return index;
  // Map 'complete' to last step
  if (step === 'complete') return STEPS.length - 1;
  return -1;
}

export function PipelineProgress({ status }: PipelineProgressProps) {
  const currentStep = status?.step;
  const currentIndex = getStepIndex(currentStep);
  const showProgress = currentIndex >= 0;

  if (!showProgress) {
    return null;
  }

  return (
    <div className="pipeline">
      {STEPS.map((step, index) => {
        const isActive = index === currentIndex;
        const isComplete = index < currentIndex;
        const isPending = index > currentIndex;
        const isLast = index === STEPS.length - 1;

        return (
          <div
            key={step.key}
            className={`pipeline__step ${isActive ? 'pipeline__step--active' : ''} ${isComplete ? 'pipeline__step--complete' : ''} ${isPending ? 'pipeline__step--pending' : ''}`}
          >
            <div className="pipeline__indicator">
              <div className="pipeline__dot">
                {isComplete ? '\u2713' : isActive ? '\u25B6' : ''}
              </div>
              {!isLast && <div className={`pipeline__line ${isComplete ? 'pipeline__line--filled' : ''}`} />}
            </div>
            <span className="pipeline__label">{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}
