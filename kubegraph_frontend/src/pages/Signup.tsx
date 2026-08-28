import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

export default function Signup() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: "", email: "", org: "", password: "" });
  const [role, setRole] = useState<"engineer" | "platform" | "ciso">("engineer");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const submit = async () => {
    setError(null); setBusy(true);
    try {
      await register({ ...f, role });
      nav("/", { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create account");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth-art">
        <div className="mk"><div className="mark" /><b>KubeGraph</b></div>
        <div>
          <h1>Map your cluster's attack surface in minutes.</h1>
          <p>Connect a cluster with read-only access and get a ranked list of the fixes that matter most.</p>
        </div>
        <div className="mono" style={{ color: "#8095b5", fontSize: 12 }}>No agents · read-only RBAC · your data stays yours</div>
        <div className="glow" /><div className="star" />
      </div>
      <div className="auth-form">
        <form className="af" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <h2>Create your workspace</h2>
          <p className="s">Start analysing your clusters today</p>
          {error && <div className="err">{error}</div>}
          <div className="field"><label>Full name</label><input value={f.name} onChange={set("name")} autoFocus /></div>
          <div className="field"><label>Work email</label><input type="email" value={f.email} onChange={set("email")} /></div>
          <div className="field"><label>Organisation</label><input value={f.org} onChange={set("org")} /></div>
          <div className="field"><label>Password</label><input type="password" value={f.password} onChange={set("password")} placeholder="at least 8 characters" /></div>
          <div className="field"><label>Primary role</label>
            <div className="seg" style={{ width: "fit-content" }}>
              {(["engineer", "platform", "ciso"] as const).map((r) => (
                <button type="button" key={r} className={role === r ? "on" : ""} onClick={() => setRole(r)}>
                  {r === "engineer" ? "Engineer" : r === "platform" ? "Platform" : "CISO"}
                </button>
              ))}
            </div>
          </div>
          <button className="primary" type="submit" disabled={busy}>{busy ? "Creating…" : "Create workspace"}</button>
          <div className="foot">Already have an account? <Link to="/login">Sign in</Link></div>
        </form>
      </div>
    </div>
  );
}
