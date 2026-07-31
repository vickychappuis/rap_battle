/**
 * BattleStage - Main container component for the multi-turn rap battle UI.
 */

import { useSession } from "../hooks/useSession";
import { FlyerHeader } from "./FlyerHeader";
import { RecordingSection } from "./RecordingSection";

export function BattleStage() {
  const {
    state,
    sessionData,
    status,
    error,
    countdown,
    turnHistory,
    retryCount,
    maxTurnRetries,
    winner,
    judgeReason,
    startBattle,
    startRecording,
    retryTurn,
    startOver,
  } = useSession();

  const turnsPerPlayer = sessionData?.turns_per_player ?? 2;

  return (
    <div>
      <FlyerHeader />
      <main className="main-content xerox-grain paper-texture -mt-12">
        <div className="container">
          {error && (
            <div className="card text-spray-paint-red mt-4" role="alert">
              <strong>Error:</strong> {error}
            </div>
          )}

          <RecordingSection
            state={state}
            countdown={countdown}
            sessionData={sessionData}
            turnHistory={turnHistory}
            status={status}
            retryCount={retryCount}
            maxTurnRetries={maxTurnRetries}
            winner={winner}
            judgeReason={judgeReason}
            startBattle={startBattle}
            startRecording={startRecording}
            retryTurn={retryTurn}
            startOver={startOver}
          />

{(state === "complete" || state === "judging") && (
            <div className="mt-12 text-center animate-in">
              <p className="text-lg">Battle Ended!</p>
              <p className="text-sm text-xerox-gray mt-2">
                {turnsPerPlayer} rounds fought.{" "}
                {state === "complete"
                  ? 'Click "New Battle" to go again'
                  : "The judge is deliberating..."}
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
