import { useState } from 'react';
import type { SessionState, UseSessionReturn } from '../hooks/useSession';
import type { SessionStatus } from '../api/session';
import { OPPONENTS } from '../data/opponents';
import { PlayerCard } from './PlayerCard';

interface RecordingSectionProps {
  state: SessionState;
  countdown: number;
  sessionData: UseSessionReturn['sessionData'];
  turnHistory: UseSessionReturn['turnHistory'];
  status: SessionStatus | null;
  error: UseSessionReturn['error'];
  startBattle: UseSessionReturn['startBattle'];
  startRecording: UseSessionReturn['startRecording'];
}

type PipelineStep = 'transcribing' | 'generating_lyrics' | 'generating_audio' | 'complete';

const PIPELINE_STEPS: { key: PipelineStep; label: string }[] = [
  { key: 'transcribing', label: 'Transcribing' },
  { key: 'generating_lyrics', label: 'Generating Lyrics' },
  { key: 'generating_audio', label: 'Generating Audio' },
  { key: 'complete', label: 'Complete' },
];

function getPipelineStepIndex(step: string | undefined): number {
  if (!step) return -1;
  const index = PIPELINE_STEPS.findIndex((s) => s.key === step);
  if (index >= 0) return index;
  if (step === 'complete') return PIPELINE_STEPS.length - 1;
  return -1;
}

/**
 * Break a wall-of-text into lines of roughly `wordsPerLine` words.
 * If the text already contains newlines, respect them.
 */
function formatLyrics(text: string, wordsPerLine = 8): string {
  if (text.includes('\n')) return text;
  const words = text.split(/\s+/);
  const lines: string[] = [];
  for (let i = 0; i < words.length; i += wordsPerLine) {
    lines.push(words.slice(i, i + wordsPerLine).join(' '));
  }
  return lines.join('\n');
}

export function RecordingSection({
  state,
  countdown,
  sessionData,
  turnHistory,
  status,
  error,
  startBattle,
  startRecording,
}: RecordingSectionProps) {
  const [opponent] = useState(() => {
    const randomIndex = Math.floor(Math.random() * OPPONENTS.length);
    return OPPONENTS[randomIndex];
  });

  const isRecording = state === 'recording';
  const isConnecting = state === 'connecting';
  const isProcessing = state === 'processing' || state === 'playing_response';
  const isComplete = state === 'complete';
  const isClickable = !isRecording && !isConnecting && !isProcessing;
  const hasSession = sessionData !== null;

  const bpm = sessionData?.bpm ?? 0;
  const recordDuration = sessionData?.record_duration ?? 0;
  const calculatedBars = bpm > 0 ? Math.round((bpm * recordDuration) / 240) : 0;

  const lastAiTurn = [...turnHistory].reverse().find((turn) => turn.player === 'ai');
  const rawLyrics = lastAiTurn?.lyrics;
  const opponentLyrics = rawLyrics ? formatLyrics(rawLyrics) : undefined;

  const currentStepIndex = getPipelineStepIndex(status?.step);
  const showPipeline = currentStepIndex >= 0;

  const micLabel = () => {
    if (isConnecting) return 'Starting...';
    if (isRecording) return 'Recording...';
    if (state === 'processing') return 'Processing...';
    if (state === 'playing_response') return 'AI Responding...';
    if (isComplete) return 'New Battle';
    if (hasSession) return 'Start Recording';
    return 'Start Battle';
  };

  // Left-bottom content changes based on pipeline stage
  const renderLeftBottom = () => {
    // Stage 2: Processing - show pipeline progress (not when already complete)
    if (isProcessing && showPipeline && status?.step !== 'complete') {
      return (
        <div className="battle-grid__status-content">
          <div className="pipeline">
            {PIPELINE_STEPS.map((step, index) => {
              const isActive = index === currentStepIndex;
              const isComplete = index < currentStepIndex;
              const isPending = index > currentStepIndex;
              const isLast = index === PIPELINE_STEPS.length - 1;
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
        </div>
      );
    }

    // Recording state - show countdown (and opponent lyrics if available)
    if (isRecording) {
      return (
        <div className="battle-grid__status-content">
          {opponentLyrics ? (
            <>
              <span className="battle-grid__response-label">Opponent's last verse:</span>
              <p className="battle-grid__response-text">{opponentLyrics}</p>
              <div className="battle-grid__countdown-inline">
                <span className="battle-grid__countdown">{countdown}</span>
                <span className="battle-grid__countdown-label">seconds left</span>
              </div>
            </>
          ) : (
            <div className="battle-grid__status-content--centered">
              <span className="battle-grid__countdown">{countdown}</span>
              <span className="battle-grid__countdown-label">seconds left</span>
            </div>
          )}
        </div>
      );
    }

    // Stage 3: Response text available
    if (opponentLyrics) {
      return (
        <div className="battle-grid__status-content">
          <span className="battle-grid__response-label">Opponent's last verse:</span>
          <p className="battle-grid__response-text">{opponentLyrics}</p>
        </div>
      );
    }

    // Stage 1: Default - show stats
    return (
      <div className="battle-grid__status-content battle-grid__status-content--centered">
        <div className="battle-grid__stats">
          <div className="battle-grid__stat">
            <span className="battle-grid__stat-value">{bpm || 90}</span>
            <span className="battle-grid__stat-label">BPM</span>
          </div>
          <div className="battle-grid__stat">
            <span className="battle-grid__stat-value">{calculatedBars || 16}</span>
            <span className="battle-grid__stat-label">Bars</span>
          </div>
          <div className="battle-grid__stat">
            <span className="battle-grid__stat-value">{recordDuration || 42}</span>
            <span className="battle-grid__stat-label">Secs</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="battle-grid">
      {/* Left top: Opponent info */}
      <div className="battle-grid__opponent">
        <PlayerCard opponent={opponent} />
      </div>

      {/* Left bottom: Pipeline status (stats / generating / response) */}
      <div className="battle-grid__status">
        {renderLeftBottom()}
      </div>

      {/* Right: Mic (full height) */}
      <div
        className="battle-grid__mic"
        onClick={isClickable ? (isComplete ? startBattle : hasSession ? startRecording : startBattle) : undefined}
        style={{
          cursor: isClickable ? 'pointer' : 'default',
          backgroundColor: isRecording ? 'rgba(230, 28, 76, 0.1)' : 'transparent',
          opacity: isConnecting || isProcessing ? 0.6 : 1,
        }}
      >
        <img
          src="/mic.png"
          alt="Microphone"
          className={`battle-grid__mic-img${hasSession && !isRecording ? ' battle-grid__mic-img--cta' : ''}`}
        />
        <p className="battle-grid__mic-label">{micLabel()}</p>
      </div>

      {error && (
        <div style={{ gridColumn: '1 / -1', color: 'red', fontWeight: 'bold', padding: '8px' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}
