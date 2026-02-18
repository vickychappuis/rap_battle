/**
 * AccessPage - Collects ElevenLabs API key and invite code before entering the battle.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlyerHeader } from "./FlyerHeader";

export function AccessPage() {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    localStorage.setItem("elevenlabs_api_key", apiKey);
    localStorage.setItem("invite_code", inviteCode);
    navigate("/battle");
  }

  return (
    <div className="access-page">
      <FlyerHeader />

      <main className="access-content">
        <form className="access-form" onSubmit={handleSubmit}>
          <div className="access-field">
            <label className="access-label" htmlFor="api-key">
              Put your ElevenLabs API code
            </label>
            <input
              id="api-key"
              className="access-input"
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              autoComplete="off"
            />
          </div>

          <p className="access-divider" aria-hidden="true">
            or
          </p>

          <div className="access-field">
            <label className="access-label" htmlFor="invite-code">
              Insert your invite code here
            </label>
            <input
              id="invite-code"
              className="access-input"
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              placeholder="XXXX-XXXX"
              autoComplete="off"
            />
          </div>

          <button type="submit" className="btn-primary access-submit">
            Let's Go
          </button>
        </form>
      </main>
    </div>
  );
}
