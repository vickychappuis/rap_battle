/**
 * App - Root application component with client-side routing.
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LandingPage } from "./LandingPage";
import { AccessPage } from "./AccessPage";
import { BattleStage } from "./BattleStage";
import { NoCreditsPage } from "./NoCreditsPage";
import { NotFoundPage } from "./NotFoundPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/access" element={<AccessPage />} />
        <Route path="/battle" element={<BattleStage />} />
        <Route path="/no-credits" element={<NoCreditsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
