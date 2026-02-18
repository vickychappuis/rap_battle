/**
 * TranscriptionDisplay - Shows the transcribed user input.
 */

interface TranscriptionDisplayProps {
  transcription: string | null | undefined;
}

export function TranscriptionDisplay({ transcription }: TranscriptionDisplayProps) {
  if (!transcription) {
    return null;
  }

  return (
    <div className="card">
      <h2 className="mb-2">Your Bars</h2>
      <p className="mono" style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
        "{transcription}"
      </p>
    </div>
  );
}
