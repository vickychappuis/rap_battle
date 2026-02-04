import { useSession } from '../hooks/useSession';

export function RecordingSection() {
  const { startBattle, startRecording, state, countdown, sessionData, turnHistory } = useSession();

  const isRecording = state === 'recording';
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

  return (
    <div className="recording-grid">
      {/* Left: Mic area (square, clickable) */}
      <div
        className="recording-grid__mic"
        onClick={!isRecording ? (hasSession ? startRecording : startBattle) : undefined}
        style={{
          cursor: isRecording ? 'default' : 'pointer',
          backgroundColor: isRecording ? 'rgba(230, 28, 76, 0.1)' : 'transparent',
        }}
      >
        <img src="/mic.png" alt="Microphone" className={`recording-grid__mic-img${hasSession && !isRecording ? ' recording-grid__mic-img--cta' : ''}`} />
        <p className="recording-grid__mic-label">
          {isRecording ? 'Recording...' : hasSession ? 'Start Recording' : 'Start Battle'}
        </p>
      </div>

      {/* Top-right: Timer / Stats */}
      <div className="recording-grid__timer">
        {isRecording ? (
          <>
            <span className="recording-grid__countdown">{countdown}</span>
            <span className="recording-grid__countdown-label">seconds left</span>
          </>
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
    </div>
  );
}
