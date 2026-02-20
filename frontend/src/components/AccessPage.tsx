/**
 * AccessPage - Collects invite code before entering the battle.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlyerHeader } from "./FlyerHeader";
import { validateInviteCode, requestInviteCode } from "../api/session";

export function AccessPage() {
  const navigate = useNavigate();
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [showRequest, setShowRequest] = useState(false);
  const [contact, setContact] = useState("");
  const [requestSent, setRequestSent] = useState(false);
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestError, setRequestError] = useState("");

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

  async function handleRequest(e: React.FormEvent) {
    e.preventDefault();
    setRequestError("");

    if (!contact.trim()) {
      setRequestError("Drop your email or handle.");
      return;
    }

    setRequestLoading(true);
    try {
      await requestInviteCode(contact.trim());
      setRequestSent(true);
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setRequestLoading(false);
    }
  }

  return (
    <div className="access-page">
      <FlyerHeader />

      <main className="access-content">
        <div className="access-form">
          <form onSubmit={handleSubmit} style={{ display: "contents" }}>
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

          <div className="access-request">
            {!showRequest ? (
              <button
                type="button"
                className="access-request-toggle"
                onClick={() => setShowRequest(true)}
              >
                No code? Request access →
              </button>
            ) : requestSent ? (
              <p className="access-request-success">
                Got it — we'll reach out.
              </p>
            ) : (
              <form className="access-request-form" onSubmit={handleRequest}>
                <input
                  className="access-input"
                  type="text"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder="email or @handle"
                  autoComplete="off"
                  disabled={requestLoading}
                  autoFocus
                />
                {requestError && (
                  <p className="access-error">{requestError}</p>
                )}
                <button
                  type="submit"
                  className="btn-secondary"
                  disabled={requestLoading}
                >
                  {requestLoading ? "Sending..." : "Request Access"}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
