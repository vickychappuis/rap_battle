/**
 * BeatTracker - Tracks current beat/bar position via elapsed time.
 *
 * Port of Python audio_player.py:33-82
 */

export class BeatTracker {
  private bpm: number;
  private msPerBeat: number;
  private msPerBar: number;
  private ctx: AudioContext;
  private startTime: number | null = null;

  constructor(bpm: number, ctx: AudioContext) {
    this.bpm = bpm;
    this.msPerBeat = 60000 / bpm;
    this.msPerBar = this.msPerBeat * 4; // 4 beats per bar
    this.ctx = ctx;
  }

  /**
   * Mark playback start time using AudioContext.currentTime.
   */
  start(): void {
    this.startTime = this.ctx.currentTime * 1000; // Convert to ms
  }

  /**
   * Get elapsed time since start in milliseconds.
   */
  getElapsedMs(): number {
    if (this.startTime === null) {
      return 0;
    }
    return (this.ctx.currentTime * 1000) - this.startTime;
  }

  /**
   * Calculate wait time to next bar boundary (4 beats).
   *
   * @param guardMs - Minimum ms threshold. If remaining time is less, skip to next bar.
   * @returns Milliseconds until the next bar starts
   */
  msUntilNextBar(guardMs: number = 500): number {
    const elapsedMs = this.getElapsedMs();
    const currentBarPosition = elapsedMs % this.msPerBar;
    let msToNextBar = this.msPerBar - currentBarPosition;

    // If we're too close to the next bar, skip to the one after
    if (msToNextBar < guardMs) {
      msToNextBar += this.msPerBar;
    }

    return msToNextBar;
  }

  /**
   * Get current beat number (1-indexed).
   */
  getCurrentBeat(): number {
    const elapsedMs = this.getElapsedMs();
    return Math.floor(elapsedMs / this.msPerBeat) + 1;
  }

  /**
   * Get current bar number (1-indexed).
   */
  getCurrentBar(): number {
    const elapsedMs = this.getElapsedMs();
    return Math.floor(elapsedMs / this.msPerBar) + 1;
  }

  /**
   * Get BPM value.
   */
  getBpm(): number {
    return this.bpm;
  }

  /**
   * Get milliseconds per bar.
   */
  getMsPerBar(): number {
    return this.msPerBar;
  }
}
