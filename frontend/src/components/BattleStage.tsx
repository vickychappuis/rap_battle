/**
 * BattleStage - Main container component for the multi-turn rap battle UI.
 */

import { useSession } from "../hooks/useSession";
import { FlyerHeader } from "./FlyerHeader";
import { StatusBanner } from "./StatusBanner";
import { PipelineProgress } from "./PipelineProgress";
import { BattleTimeline } from "./BattleTimeline";
import { PlayerCard } from "./PlayerCard";
import { RecordingSection } from "./RecordingSection";

export function BattleStage() {
  const {
    state,
    sessionData,
    status,
    error,
    countdown,
    currentRound,
    turnHistory,
    startBattle,
    startRecording,
  } = useSession();

  const turnsPerPlayer = sessionData?.turns_per_player ?? 2;

  return (
    <div>
      <FlyerHeader />
      <main className="main-content xerox-grain paper-texture -mt-12">
        <div className="container">
          <PlayerCard />

          <StatusBanner
            state={state}
            countdown={countdown}
            currentRound={currentRound}
            turnsPerPlayer={turnsPerPlayer}
          />

          {error && (
            <div className="card text-spray-paint-red mt-4">
              <strong>Error:</strong> {error}
            </div>
          )}

          <RecordingSection
            state={state}
            countdown={countdown}
            sessionData={sessionData}
            turnHistory={turnHistory}
            error={error}
            startBattle={startBattle}
            startRecording={startRecording}
          />

          {sessionData && (
            <div className="mt-2 text-center text-sm text-xerox-gray mono">
              {sessionData.bpm} BPM | {sessionData.bars_per_turn} bars |{" "}
              {sessionData.record_duration}s per turn
            </div>
          )}

          <div className="mt-3">
            <PipelineProgress status={status} />
          </div>

          {turnHistory.length > 0 && (
            <div className="mt-12">
              <h2 className="mb-4">Battle History</h2>
              <BattleTimeline turnHistory={turnHistory} />
            </div>
          )}

          {state === "complete" && (
            <div className="mt-12 text-center animate-in">
              <p className="text-lg">Battle Complete!</p>
              <p className="text-sm text-xerox-gray mt-2">
                {turnsPerPlayer} rounds fought. Click "New Battle" to go again
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
