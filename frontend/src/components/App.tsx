/**
 * App - Root application component with client-side routing.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ARENA_ON_HIATUS, LandingPage } from "./LandingPage";
import { BattleStage } from "./BattleStage";
import { NotFoundPage } from "./NotFoundPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/battle"
          element={ARENA_ON_HIATUS ? <Navigate to="/" replace /> : <BattleStage />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
