/**
 * LandingPage - Home page with boxing gloves and "Enter the Arena" CTA.
 */

import { useNavigate } from "react-router-dom";
import { FlyerHeader } from "./FlyerHeader";

/**
 * When true the arena is paused: the CTA is replaced by a notice pointing at
 * the repo, and /battle redirects home. Flip back to false to reopen — the
 * backend also needs its API keys set again, or every battle will fail.
 */
export const ARENA_ON_HIATUS = true;

const REPO_URL = "https://github.com/vickychappuis/rap_battle";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      <FlyerHeader />

      <main className="landing-content">
        <div className="landing-gloves">
          <img
            src="/red_glove.webp"
            alt="Red boxing glove"
            className="landing-glove landing-glove--red"
          />
          <img
            src="/blue_glove.webp"
            alt="Blue boxing glove"
            className="landing-glove landing-glove--blue"
          />
        </div>

        {ARENA_ON_HIATUS ? (
          <div className="landing-hiatus card">
            <span className="stamp landing-hiatus__stamp">On Hiatus</span>
            <p className="landing-hiatus__text">
              The arena isn't live on the web these days. Wanna battle anyway?
              Grab the code and run it yourself.
            </p>
            <a
              className="landing-hiatus__link"
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
            >
              Get the Code
            </a>
          </div>
        ) : (
          <button
            className="landing-cta"
            onClick={() => navigate("/battle")}
          >
            <img
              src="/torn_yellow_paper.webp"
              alt=""
              className="landing-cta__bg"
            />
            <span className="landing-cta__text">Enter the Arena</span>
          </button>
        )}
      </main>
    </div>
  );
}
