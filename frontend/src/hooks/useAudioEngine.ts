/**
 * useAudioEngine - React hook for managing the AudioEngine lifecycle.
 */

import { useRef, useCallback, useEffect } from 'react';
import { AudioEngine } from '../audio/AudioEngine';
import { Recorder } from '../audio/Recorder';

export function useAudioEngine() {
  const engineRef = useRef<AudioEngine | null>(null);
  const recorderRef = useRef<Recorder | null>(null);

  // Get or create the AudioEngine instance
  const getEngine = useCallback(() => {
    if (!engineRef.current) {
      engineRef.current = new AudioEngine();
    }
    return engineRef.current;
  }, []);

  // Get or create the Recorder instance
  const getRecorder = useCallback(() => {
    if (!recorderRef.current) {
      recorderRef.current = new Recorder();
    }
    return recorderRef.current;
  }, []);

  // Start base track
  const startBaseTrack = useCallback(async (url: string, bpm: number) => {
    const engine = getEngine();
    await engine.startBaseTrack(url, bpm);
  }, [getEngine]);

  // Schedule AI response
  const scheduleAiResponse = useCallback(async (url: string) => {
    const engine = getEngine();
    return engine.scheduleAiResponse(url);
  }, [getEngine]);

  // Record audio
  const recordAudio = useCallback(async (durationMs: number): Promise<Blob> => {
    const recorder = getRecorder();
    return recorder.record(durationMs);
  }, [getRecorder]);

  // Check if playing
  const isPlaying = useCallback(() => {
    return engineRef.current?.getIsPlaying() ?? false;
  }, []);

  // Stop everything
  const stop = useCallback(() => {
    if (engineRef.current) {
      engineRef.current.stop();
    }
    if (recorderRef.current) {
      recorderRef.current.dispose();
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (engineRef.current) {
        engineRef.current.close();
        engineRef.current = null;
      }
      if (recorderRef.current) {
        recorderRef.current.dispose();
        recorderRef.current = null;
      }
    };
  }, []);

  return {
    startBaseTrack,
    scheduleAiResponse,
    recordAudio,
    isPlaying,
    stop,
  };
}
