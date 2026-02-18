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
    <div className="card">
      <h2 className="mb-4">Pipeline Progress</h2>
      <div className="flex flex-col gap-2">
        {STEPS.map((step, index) => {
          const isActive = index === currentIndex;
          const isComplete = index < currentIndex;
          const isPending = index > currentIndex;

          return (
            <div
              key={step.key}
              className={`flex items-center gap-2 ${isActive ? 'recording' : ''}`}
              style={{ opacity: isPending ? 0.4 : 1 }}
            >
              <span className="mono text-sm" style={{ width: '1.5rem' }}>
                {isComplete ? '[x]' : isActive ? '[>]' : '[ ]'}
              </span>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>
      {currentIndex >= 0 && currentIndex < STEPS.length - 1 && (
        <div className="progress-bar mt-4">
          <div
            className="progress-bar-fill"
            style={{ width: `${((currentIndex + 1) / STEPS.length) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}
