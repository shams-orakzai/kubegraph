import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null); setBusy(true);
    try {
      await login(email, password);
      nav("/", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth-art">
        <div className="mk"><div className="mark" /><b>KubeGraph</b></div>
        <div>
          <h1>See every path an attacker could take to cluster-admin — and the one fix that closes them.</h1>
          <p>Graph-based Kubernetes privilege-escalation analysis for your whole fleet.</p>
        </div>
        <div className="mono" style={{ color: "#8095b5", fontSize: 12 }}>SSO / SAML · read-only cluster access</div>
        <div className="glow" /><div className="star" />
      </div>
      <div className="auth-form">
        <form className="af" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <h2>Welcome back</h2>
          <p className="s">Sign in to your KubeGraph workspace</p>
          {error && <div className="err">{error}</div>}
          <div className="field"><label>Work email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoFocus />
          </div>
          <div className="field"><label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>
          <button className="primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <div className="divider">or</div>
          <button className="sso" type="button" disabled>Continue with SSO / SAML</button>
          <div className="foot">New to KubeGraph? <Link to="/signup">Create a workspace</Link></div>
        </form>
      </div>
    </div>
  );
}
