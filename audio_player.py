"""
Audio playback and mixing module for rap battle system.

Provides:
- BeatTracker: Tracks current beat/bar position via elapsed time
- AudioMixer: Handles continuous playback with real-time mixing
- load_audio_file: Load MP3/WAV into numpy array for mixing
"""

import os
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Optional
from pathlib import Path


# ============================================================================
# CONSTANTS
# ============================================================================

SAMPLE_RATE = 44100  # Standard audio sample rate
CHANNELS = 2  # Stereo output
DUCK_FACTOR = float(os.environ.get("DUCK_FACTOR", 0.7))  # Volume reduction for base track during overlay


# ============================================================================
# BEAT TRACKER
# ============================================================================

class BeatTracker:
    """Tracks current beat/bar position via elapsed time."""

    def __init__(self, bpm: int):
        """
        Initialize beat tracker.

        Args:
            bpm: Beats per minute
        """
        self.bpm = bpm
        self.ms_per_beat = 60000 / bpm
        self.ms_per_bar = self.ms_per_beat * 4  # 4 beats per bar
        self.start_time: Optional[float] = None

    def start(self) -> None:
        """Mark playback start time."""
        self.start_time = time.time()

    def get_elapsed_ms(self) -> float:
        """Get elapsed time since start in milliseconds."""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000

    def get_playback_position_samples(self) -> int:
        """Get current sample position in playback."""
        elapsed_ms = self.get_elapsed_ms()
        return int(elapsed_ms * SAMPLE_RATE / 1000)

    def ms_until_next_bar(self) -> float:
        """
        Calculate wait time to next bar boundary (4 beats).

        Returns:
            Milliseconds until the next bar starts
        """
        elapsed_ms = self.get_elapsed_ms()
        current_bar_position = elapsed_ms % self.ms_per_bar
        return self.ms_per_bar - current_bar_position

    def get_current_beat(self) -> int:
        """Get current beat number (1-indexed)."""
        elapsed_ms = self.get_elapsed_ms()
        return int(elapsed_ms / self.ms_per_beat) + 1

    def get_current_bar(self) -> int:
        """Get current bar number (1-indexed)."""
        elapsed_ms = self.get_elapsed_ms()
        return int(elapsed_ms / self.ms_per_bar) + 1


# ============================================================================
# AUDIO MIXER
# ============================================================================

class AudioMixer:
    """
    Handles continuous playback with real-time mixing.

    Uses sounddevice.OutputStream with callback for sample-level control.
    Base track plays continuously (looping) and overlay audio is mixed
    on top at scheduled sample positions.
    """

    def __init__(self, base_track_path: str, bpm: int):
        """
        Initialize audio mixer.

        Args:
            base_track_path: Path to the base track WAV file
            bpm: Beats per minute for beat tracking
        """
        self.base_track_path = base_track_path
        self.bpm = bpm
        self.beat_tracker = BeatTracker(bpm)

        # Audio data
        self.base_track: Optional[np.ndarray] = None
        self.base_track_length: int = 0

        # Playback state
        self.current_sample: int = 0
        self.stream: Optional[sd.OutputStream] = None
        self.is_playing: bool = False
        self.lock = threading.Lock()

        # Overlay scheduling
        self.overlay_audio: Optional[np.ndarray] = None
        self.overlay_start_sample: int = 0
        self.overlay_current_pos: int = 0
        self.overlay_active: bool = False

    def load_base_track(self, path: Optional[str] = None) -> None:
        """
        Load base WAV into memory.

        Args:
            path: Optional override path. Uses self.base_track_path if None.
        """
        load_path = path or self.base_track_path

        if not Path(load_path).exists():
            raise FileNotFoundError(f"Base track not found: {load_path}")

        print(f"Loading base track: {load_path}")
        audio_data, sample_rate = sf.read(load_path, dtype='float32')

        # Ensure stereo
        if len(audio_data.shape) == 1:
            audio_data = np.column_stack([audio_data, audio_data])

        # Resample if necessary
        if sample_rate != SAMPLE_RATE:
            print(f"Warning: Base track sample rate ({sample_rate}) differs from target ({SAMPLE_RATE})")
            # Simple resampling - for production, use a proper resampling library
            ratio = SAMPLE_RATE / sample_rate
            new_length = int(len(audio_data) * ratio)
            indices = np.linspace(0, len(audio_data) - 1, new_length).astype(int)
            audio_data = audio_data[indices]

        self.base_track = audio_data
        self.base_track_length = len(audio_data)
        print(f"Base track loaded: {self.base_track_length} samples ({self.base_track_length / SAMPLE_RATE:.2f}s)")

    def _audio_callback(self, outdata: np.ndarray, frames: int,
                        time_info, status: sd.CallbackFlags) -> None:
        """
        Callback function for sounddevice OutputStream.

        Fills output buffer with base track samples (looping) and
        mixes overlay audio on top when scheduled.
        """
        if status:
            print(f"Audio callback status: {status}")

        with self.lock:
            if self.base_track is None:
                outdata.fill(0)
                return

            # Prepare output buffer
            output = np.zeros((frames, CHANNELS), dtype='float32')

            # Fill with base track samples (looping)
            for i in range(frames):
                sample_idx = (self.current_sample + i) % self.base_track_length
                output[i] = self.base_track[sample_idx]

            # Check if overlay should be active
            current_end = self.current_sample + frames

            if self.overlay_audio is not None:
                overlay_len = len(self.overlay_audio)
                overlay_end = self.overlay_start_sample + overlay_len

                # Check if overlay intersects with current frame window
                if self.current_sample < overlay_end and current_end > self.overlay_start_sample:
                    self.overlay_active = True

                    # Calculate mixing range within this frame
                    for i in range(frames):
                        abs_sample = self.current_sample + i
                        overlay_pos = abs_sample - self.overlay_start_sample

                        if 0 <= overlay_pos < overlay_len:
                            # Apply ducking to base track and add overlay
                            output[i] = (output[i] * DUCK_FACTOR +
                                        self.overlay_audio[overlay_pos])

                    # Check if overlay finished
                    if current_end >= overlay_end:
                        self.overlay_active = False
                        self.overlay_audio = None
                else:
                    self.overlay_active = False

            # Clip to prevent distortion
            np.clip(output, -1.0, 1.0, out=output)

            # Copy to output buffer
            outdata[:] = output

            # Update position
            self.current_sample += frames

    def start(self) -> None:
        """Begin streaming base track via callback."""
        if self.base_track is None:
            raise RuntimeError("Base track not loaded. Call load_base_track() first.")

        if self.is_playing:
            print("Playback already started")
            return

        print(f"Starting audio playback at {self.bpm} BPM...")

        self.current_sample = 0
        self.beat_tracker.start()

        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            callback=self._audio_callback,
            blocksize=1024  # ~23ms latency at 44.1kHz
        )
        self.stream.start()
        self.is_playing = True

        print("Audio playback started")

    def get_current_sample(self) -> int:
        """Get current playback sample position."""
        with self.lock:
            return self.current_sample

    def schedule_overlay(self, audio_data: np.ndarray, start_sample: int) -> None:
        """
        Queue audio to mix at specific sample position.

        Args:
            audio_data: Numpy array of audio samples to overlay
            start_sample: Sample position to start mixing overlay
        """
        with self.lock:
            # Ensure stereo
            if len(audio_data.shape) == 1:
                audio_data = np.column_stack([audio_data, audio_data])

            self.overlay_audio = audio_data.astype('float32')
            self.overlay_start_sample = start_sample
            self.overlay_current_pos = 0

            print(f"Overlay scheduled at sample {start_sample} "
                  f"({start_sample / SAMPLE_RATE:.2f}s from start)")

    def stop(self) -> None:
        """Stop playback cleanly."""
        if self.stream is not None:
            print("Stopping audio playback...")
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.is_playing = False
        self.overlay_audio = None
        print("Audio playback stopped")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_audio_file(path: str) -> np.ndarray:
    """
    Load MP3/WAV into numpy array for mixing.

    Args:
        path: Path to audio file (MP3 or WAV)

    Returns:
        Numpy array of audio samples (stereo, float32)
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    print(f"Loading audio file: {path}")
    audio_data, sample_rate = sf.read(path, dtype='float32')

    # Ensure stereo
    if len(audio_data.shape) == 1:
        audio_data = np.column_stack([audio_data, audio_data])

    # Resample if necessary
    if sample_rate != SAMPLE_RATE:
        print(f"Resampling from {sample_rate}Hz to {SAMPLE_RATE}Hz")
        ratio = SAMPLE_RATE / sample_rate
        new_length = int(len(audio_data) * ratio)
        indices = np.linspace(0, len(audio_data) - 1, new_length).astype(int)
        audio_data = audio_data[indices]

    print(f"Audio loaded: {len(audio_data)} samples ({len(audio_data) / SAMPLE_RATE:.2f}s)")
    return audio_data.astype('float32')
