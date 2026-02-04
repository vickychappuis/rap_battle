import { useSession } from '../hooks/useSession';

export function RecordingSection() {
  const { startRecording, state, countdown, sessionData, turnHistory, currentRound } = useSession();

  const isRecording = state === 'recording';

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
        onClick={!isRecording ? startRecording : undefined}
        style={{
          cursor: isRecording ? 'default' : 'pointer',
          backgroundColor: isRecording ? 'rgba(230, 28, 76, 0.1)' : 'transparent',
        }}
      >
        <img src="/mic.png" alt="Microphone" className="recording-grid__mic-img" />
        <p className="recording-grid__mic-label">
          {isRecording ? 'Recording...' : 'Start Recording'}
        </p>
      </div>

      {/* Top-right: Timer / Stats */}
      <div className="recording-grid__timer">
        {isRecording ? (
          <>
            <span className="recording-grid__countdown">{countdown}</span>
            <span className="recording-grid__countdown-label">seconds left</span>
          </>
        ) : (
          <>
            <div className="recording-grid__stat">
              <span className="recording-grid__stat-value">{sessionData?.bpm ?? '--'}</span>
              <span className="recording-grid__stat-label">BPM</span>
            </div>
            <div className="recording-grid__stat">
              <span className="recording-grid__stat-value">{sessionData?.bars_per_turn ?? '--'}</span>
              <span className="recording-grid__stat-label">Bars</span>
            </div>
          </>
        )}
      </div>

      {/* Bottom-right: Opponent response */}
      <div className="recording-grid__response">
        {opponentLyrics ? (
          <>
            <span className="recording-grid__response-label">Opponent's last verse:</span>
            <p className="recording-grid__response-text">{opponentLyrics}</p>
          </>
        ) : (
          <p className="recording-grid__taunt">{randomTaunt}</p>
        )}
      </div>
    </div>
  );
}
