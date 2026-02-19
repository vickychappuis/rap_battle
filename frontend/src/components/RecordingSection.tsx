import type { SessionState, UseSessionReturn } from '../hooks/useSession';

interface RecordingSectionProps {
  state: SessionState;
  countdown: number;
  sessionData: UseSessionReturn['sessionData'];
  turnHistory: UseSessionReturn['turnHistory'];
  error: UseSessionReturn['error'];
  startBattle: UseSessionReturn['startBattle'];
  startRecording: UseSessionReturn['startRecording'];
}

export function RecordingSection({
  state,
  countdown,
  sessionData,
  turnHistory,
  error,
  startBattle,
  startRecording,
}: RecordingSectionProps) {
  const isRecording = state === 'recording';
  const isConnecting = state === 'connecting';
  const isProcessing = state === 'processing' || state === 'playing_response';
  const isClickable = !isRecording && !isConnecting && !isProcessing;
  const hasSession = sessionData !== null;

  // Calculate bars from BPM and record duration
  const bpm = sessionData?.bpm ?? 0;
  const recordDuration = sessionData?.record_duration ?? 0;
  const calculatedBars = bpm > 0 ? Math.round((bpm * recordDuration) / 240) : 0;

  // Get the last AI response from turn history
  const lastAiTurn = [...turnHistory].reverse().find((turn) => turn.player === 'ai');
  const opponentLyrics = lastAiTurn?.lyrics;

  // Taunts for round 1 when there's no opponent response yet
  const round1Taunts = [
    "Think you got bars? Prove it.",
    "The mic is waiting...",
    "Show 'em what you got.",
    "Your opponent is ready. Are you?",
  ];
  const randomTaunt = round1Taunts[Math.floor(Math.random() * round1Taunts.length)];

  const micLabel = () => {
    if (isConnecting) return 'Starting...';
    if (isRecording) return 'Recording...';
    if (state === 'processing') return 'Processing...';
    if (state === 'playing_response') return 'AI Responding...';
    if (hasSession) return 'Start Recording';
    return 'Start Battle';
  };

  return (
    <div className="recording-grid">
      {/* Left: Mic area (square, clickable) */}
      <div
        className="recording-grid__mic"
        onClick={isClickable ? (hasSession ? startRecording : startBattle) : undefined}
        style={{
          cursor: isClickable ? 'pointer' : 'default',
          backgroundColor: isRecording ? 'rgba(230, 28, 76, 0.1)' : 'transparent',
          opacity: isConnecting || isProcessing ? 0.6 : 1,
        }}
      >
        <img src="/mic.png" alt="Microphone" className={`recording-grid__mic-img${hasSession && !isRecording ? ' recording-grid__mic-img--cta' : ''}`} />
        <p className="recording-grid__mic-label">{micLabel()}</p>
      </div>

      {/* Top-right: Timer / Stats */}
      <div className="recording-grid__timer">
        {isRecording ? (
          <>
            <span className="recording-grid__countdown">{countdown}</span>
            <span className="recording-grid__countdown-label">seconds left</span>
          </>
        ) : isProcessing ? (
          <p className="recording-grid__taunt">Generating response...</p>
        ) : hasSession ? (
          <>
            <div className="recording-grid__stat">
              <span className="recording-grid__stat-value">{bpm}</span>
              <span className="recording-grid__stat-label">BPM</span>
            </div>
            <div className="recording-grid__stat">
              <span className="recording-grid__stat-value">{calculatedBars}</span>
              <span className="recording-grid__stat-label">Bars</span>
            </div>
          </>
        ) : (
          <p className="recording-grid__taunt">Click to drop the beat</p>
        )}
      </div>

      {/* Bottom-right: Opponent response */}
      <div className="recording-grid__response">
        {opponentLyrics ? (
          <>
            <span className="recording-grid__response-label">Opponent's last verse:</span>
            <p className="recording-grid__response-text">{opponentLyrics}</p>
          </>
        ) : hasSession ? (
          <p className="recording-grid__taunt">{randomTaunt}</p>
        ) : (
          <p className="recording-grid__taunt">Your opponent awaits...</p>
        )}
      </div>

      {error && (
        <div style={{ gridColumn: '1 / -1', color: 'red', fontWeight: 'bold', padding: '8px' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}
