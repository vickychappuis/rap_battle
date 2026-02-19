/**
 * NotFoundPage - 404 page with big brutalist typography.
 */

import { useNavigate } from "react-router-dom";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="not-found-page">
      <div className="not-found-content">
        <span className="not-found-404">404</span>
        <p className="not-found-subtitle">Wrong stage, homie</p>
        <button className="btn-primary" onClick={() => navigate("/")}>
          Back to the Arena
        </button>
      </div>
    </div>
  );
}
