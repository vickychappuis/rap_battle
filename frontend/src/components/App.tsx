/**
 * App - Root application component with client-side routing.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LandingPage } from "./LandingPage";
import { BattleStage } from "./BattleStage";
import { NotFoundPage } from "./NotFoundPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/access" element={<Navigate to="/battle" replace />} />
        <Route path="/battle" element={<BattleStage />} />
        <Route path="/no-credits" element={<Navigate to="/battle" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
