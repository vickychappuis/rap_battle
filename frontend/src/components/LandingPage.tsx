/**
 * LandingPage - Home page with boxing gloves and "Enter the Arena" CTA.
 */

import { useNavigate } from "react-router-dom";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      <div className="flyer-header">
        <img
          src="/rap_arena_logo.png"
          alt="Rap Arena"
          className="flyer-logo"
        />
      </div>

      <main className="landing-content">
        <div className="landing-gloves">
          <img
            src="/red_glove.png"
            alt="Red boxing glove"
            className="landing-glove landing-glove--red"
          />
          <img
            src="/blue_glove.png"
            alt="Blue boxing glove"
            className="landing-glove landing-glove--blue"
          />
        </div>

        <button
          className="landing-cta"
          onClick={() => navigate("/access")}
        >
          <img
            src="/torn_yellow_paper.png"
            alt=""
            className="landing-cta__bg"
          />
          <span className="landing-cta__text">Enter the Arena</span>
        </button>
      </main>
    </div>
  );
}
