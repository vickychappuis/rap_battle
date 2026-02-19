/**
 * AccessPage - Collects invite code before entering the battle.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlyerHeader } from "./FlyerHeader";
import { validateInviteCode } from "../api/session";

export function AccessPage() {
  const navigate = useNavigate();
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!inviteCode) {
      setError("Please enter an invite code.");
      return;
    }

    setLoading(true);
    try {
      await validateInviteCode(inviteCode);
      localStorage.setItem("invite_code", inviteCode);
      navigate("/battle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="access-page">
      <FlyerHeader />

      <main className="access-content">
        <form className="access-form" onSubmit={handleSubmit}>
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
              disabled={loading}
            />
          </div>

          {error && <p className="access-error">{error}</p>}

          <button
            type="submit"
            className="btn-primary access-submit"
            disabled={loading}
          >
            {loading ? "Validating..." : "Let's Go"}
          </button>
        </form>
      </main>
    </div>
  );
}
