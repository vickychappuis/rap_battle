/**
 * AudioEngine - Web Audio graph for playback and scheduling.
 *
 * Web Audio Graph:
 * BaseTrackSource (loop=true) -> GainNode -> MasterGain -> destination
 * AIResponseSource (scheduled) -> GainNode -> MasterGain -> destination
 */

import { BeatTracker } from './BeatTracker';

export class AudioEngine {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private baseTrackSource: AudioBufferSourceNode | null = null;
  private baseTrackBuffer: AudioBuffer | null = null;
  private aiResponseSource: AudioBufferSourceNode | null = null;
  private beatTracker: BeatTracker | null = null;

  private isPlaying = false;
  private baseTrackGain: GainNode | null = null;
  private aiResponseGain: GainNode | null = null;

  /**
   * Initialize the AudioContext (must be called after user gesture).
   */
  async init(): Promise<void> {
    if (this.ctx) return;

    this.ctx = new AudioContext();

    // Create master gain
    this.masterGain = this.ctx.createGain();
    this.masterGain.connect(this.ctx.destination);

    // Create gain nodes for mixing
    this.baseTrackGain = this.ctx.createGain();
    this.baseTrackGain.connect(this.masterGain);

    this.aiResponseGain = this.ctx.createGain();
    this.aiResponseGain.connect(this.masterGain);
  }

  /**
   * Load and decode an audio file.
   */
  async loadAudio(url: string): Promise<AudioBuffer> {
    if (!this.ctx) throw new Error('AudioContext not initialized');

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load audio: ${response.statusText}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    return this.ctx.decodeAudioData(arrayBuffer);
  }

  /**
   * Load and start the base track looping.
   *
   * @param url - URL of the base track
   * @param bpm - Beats per minute for beat tracking
   */
  async startBaseTrack(url: string, bpm: number): Promise<void> {
    if (!this.ctx || !this.baseTrackGain) {
      await this.init();
    }

    if (this.isPlaying) {
      console.warn('Base track already playing');
      return;
    }

    // Load the base track
    this.baseTrackBuffer = await this.loadAudio(url);

    // Create and configure source
    this.baseTrackSource = this.ctx!.createBufferSource();
    this.baseTrackSource.buffer = this.baseTrackBuffer;
    this.baseTrackSource.loop = true;
    this.baseTrackSource.connect(this.baseTrackGain!);

    // Create beat tracker
    this.beatTracker = new BeatTracker(bpm, this.ctx!);

    // Start playback
    this.baseTrackSource.start();
    this.beatTracker.start();
    this.isPlaying = true;
  }

  /**
   * Schedule AI response to play at the next bar boundary.
   *
   * @param url - URL of the AI response audio
   * @returns Promise that resolves when the audio finishes playing
   */
  async scheduleAiResponse(url: string): Promise<void> {
    if (!this.ctx || !this.beatTracker || !this.aiResponseGain) {
      throw new Error('AudioEngine not initialized or base track not playing');
    }

    // Load the AI response audio
    const buffer = await this.loadAudio(url);

    // Calculate when to start (next bar boundary)
    const waitMs = this.beatTracker.msUntilNextBar(500); // 0.5s guard threshold
    const scheduleTime = this.ctx.currentTime + (waitMs / 1000);

    // Create and schedule source
    this.aiResponseSource = this.ctx.createBufferSource();
    this.aiResponseSource.buffer = buffer;
    this.aiResponseSource.connect(this.aiResponseGain);

    // Schedule playback (sample-accurate via Web Audio clock)
    this.aiResponseSource.start(scheduleTime);

    // Return a promise that resolves when playback ends
    return new Promise((resolve) => {
      const duration = buffer.duration * 1000; // Convert to ms
      const totalWait = waitMs + duration;
      setTimeout(resolve, totalWait);
    });
  }

  /**
   * Get the beat tracker instance.
   */
  getBeatTracker(): BeatTracker | null {
    return this.beatTracker;
  }

  /**
   * Get the AudioContext instance.
   */
  getContext(): AudioContext | null {
    return this.ctx;
  }

  /**
   * Check if the base track is playing.
   */
  getIsPlaying(): boolean {
    return this.isPlaying;
  }

  /**
   * Stop all playback and clean up.
   */
  stop(): void {
    if (this.baseTrackSource) {
      try {
        this.baseTrackSource.stop();
      } catch {
        // Already stopped
      }
      this.baseTrackSource = null;
    }

    if (this.aiResponseSource) {
      try {
        this.aiResponseSource.stop();
      } catch {
        // Already stopped
      }
      this.aiResponseSource = null;
    }

    this.isPlaying = false;
    this.beatTracker = null;
  }

  /**
   * Close the AudioContext entirely.
   */
  async close(): Promise<void> {
    this.stop();
    if (this.ctx) {
      await this.ctx.close();
      this.ctx = null;
      this.masterGain = null;
      this.baseTrackGain = null;
      this.aiResponseGain = null;
    }
  }
}
