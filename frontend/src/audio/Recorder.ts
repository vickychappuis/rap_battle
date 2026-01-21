/**
 * Recorder - MediaRecorder wrapper for capturing user audio.
 *
 * Uses MediaRecorder with audio/webm;codecs=opus (Chrome) or audio/mp4 (Safari).
 * No client-side WAV conversion - backend accepts WebM/MP4 directly.
 */

export class Recorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];

  /**
   * Request microphone access and prepare for recording.
   */
  async init(): Promise<void> {
    if (this.stream) return;

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100,
      },
    });
  }

  /**
   * Get the preferred MIME type for recording.
   */
  private getMimeType(): string {
    // Chrome/Firefox prefer webm
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      return 'audio/webm;codecs=opus';
    }
    // Safari prefers mp4
    if (MediaRecorder.isTypeSupported('audio/mp4')) {
      return 'audio/mp4';
    }
    // Fallback
    if (MediaRecorder.isTypeSupported('audio/webm')) {
      return 'audio/webm';
    }
    return '';
  }

  /**
   * Start recording for a fixed duration.
   *
   * @param durationMs - Recording duration in milliseconds
   * @returns Promise that resolves with the recorded Blob
   */
  async record(durationMs: number): Promise<Blob> {
    if (!this.stream) {
      await this.init();
    }

    return new Promise((resolve, reject) => {
      this.chunks = [];

      const mimeType = this.getMimeType();
      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};

      try {
        this.mediaRecorder = new MediaRecorder(this.stream!, options);
      } catch (err) {
        reject(new Error(`Failed to create MediaRecorder: ${err}`));
        return;
      }

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          this.chunks.push(e.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: mimeType || 'audio/webm' });
        resolve(blob);
      };

      this.mediaRecorder.onerror = (e) => {
        reject(new Error(`MediaRecorder error: ${e}`));
      };

      // Start recording
      this.mediaRecorder.start(100); // Collect data every 100ms

      // Auto-stop after duration
      setTimeout(() => {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
          this.mediaRecorder.stop();
        }
      }, durationMs);
    });
  }

  /**
   * Stop recording early.
   */
  stop(): void {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }
  }

  /**
   * Check if currently recording.
   */
  isRecording(): boolean {
    return this.mediaRecorder?.state === 'recording';
  }

  /**
   * Release microphone access.
   */
  dispose(): void {
    this.stop();
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.chunks = [];
  }
}
