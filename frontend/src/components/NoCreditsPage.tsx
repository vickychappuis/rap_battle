import { useNavigate } from "react-router-dom";
import { FlyerHeader } from "./FlyerHeader";

export function NoCreditsPage() {
  const navigate = useNavigate();

  return (
    <div className="access-page">
      <FlyerHeader />

      <main className="no-credits-content">
        <div className="no-credits-box animate-in">
          <div className="no-credits-gloves">
            <img src="/red_glove.png" alt="" className="no-credits-glove no-credits-glove--left" />
            <img src="/blue_glove.png" alt="" className="no-credits-glove no-credits-glove--right" />
          </div>
          <div className="no-credits-banner">
            <h2 className="no-credits-title">You're out of battle credits</h2>
          </div>
          <p className="no-credits-subtitle">
            Paid subscriptions coming soon.
          </p>
          <button
            className="btn-primary"
            onClick={() => navigate("/access")}
          >
            Try another code
          </button>
        </div>
      </main>
    </div>
  );
}
