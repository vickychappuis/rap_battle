/**
 * LyricsDisplay - Shows the AI-generated lyrics (plain_take only).
 */

interface LyricsDisplayProps {
  lyrics: string | null | undefined;
}

export function LyricsDisplay({ lyrics }: LyricsDisplayProps) {
  if (!lyrics) {
    return null;
  }

  return (
    <div className="card">
      <h2 className="mb-1">AI Response</h2>
      <p style={{ fontSize: '1.1rem', lineHeight: 1.6, fontStyle: 'italic' }}>
        "{lyrics}"
      </p>
    </div>
  );
}
