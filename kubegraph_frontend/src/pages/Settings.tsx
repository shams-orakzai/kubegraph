import { useEffect, useState } from "react";
import { api, tokenStore } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useCluster } from "../cluster/ClusterContext";
import { useRoleControl, type Role } from "../layout/AppShell";

const ROLE_INFO: { id: Role; label: string; blurb: string }[] = [
  { id: "engineer", label: "Engineer", blurb: "Graph- and path-forward: attack graph, footholds, top fixes." },
  { id: "platform", label: "Platform", blurb: "Remediation backlog: what to fix first, by impact." },
  { id: "ciso", label: "CISO", blurb: "Posture and fleet: exposure across every cluster." },
];
const BAND_TAG: Record<string, string> = { Low: "tag-ok", Medium: "tag-med", High: "tag-crit" };

function tokenExpiry(tok: string | null): string {
  if (!tok) return "no token";
  try {
    const payload = JSON.parse(atob(tok.split(".")[1]));
    if (!payload.exp) return "no expiry";
    const ms = payload.exp * 1000 - Date.now();
    if (ms <= 0) return "expired — sign in again";
    const h = Math.floor(ms / 3_600_000), m = Math.floor((ms % 3_600_000) / 60_000);
    return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`;
  } catch { return "—"; }
}

export default function Settings() {
  const { user, logout } = useAuth();
  const { stats, reload } = useCluster();
  const { role, setRole } = useRoleControl();

  const [snaps, setSnaps] = useState<{ snapshot_id: string; cluster_name: string; current: boolean }[]>([]);
  const [version, setVersion] = useState<string>("…");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadMeta = async () => {
    try { setSnaps(await api.snapshots()); } catch { /* ignore */ }
    try { setVersion((await api.health()).version); } catch { setVersion("unreachable"); }
  };
  useEffect(() => { void loadMeta(); }, []);

  const initials = (user?.name || "U").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase();

  const reloadDemo = async () => {
    setBusy(true);
    try { await api.loadDemo(); reload(); await loadMeta(); } finally { setBusy(false); }
  };
  const copyToken = async () => {
    const t = tokenStore.get(); if (!t) return;
    try { await navigator.clipboard.writeText(t); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* ignore */ }
  };

  return (
    <div className="page">
      <h1 className="h1">Settings</h1>
      <p className="lede">Your account, dashboard persona, workspace, and connection.</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 860 }}>

        {/* ---- Profile ---- */}
        <div className="card">
          <span className="eyebrow">Profile</span>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 12 }}>
            <div className="av" style={{ width: 52, height: 52, borderRadius: "50%", display: "grid", placeItems: "center",
              background: "linear-gradient(135deg,var(--sa),var(--secret))", color: "#fff", fontWeight: 800, fontSize: 18 }}>{initials}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{user?.name}</div>
              <div className="dim mono" style={{ fontSize: 13 }}>{user?.email}</div>
            </div>
            <span className="tag tag-low" style={{ textTransform: "capitalize" }}>{user?.role}</span>
          </div>
          <div style={{ marginTop: 14 }}>
            <div className="mini"><span className="dim">Organisation</span><b>{user?.org || "—"}</b></div>
            <div className="mini"><span className="dim">Account ID</span><b className="mono">#{user?.id}</b></div>
          </div>
          <p className="dim" style={{ fontSize: 12, marginTop: 12 }}>Profile editing and team management are on the roadmap.</p>
        </div>

        {/* ---- Dashboard persona ---- */}
        <div className="card">
          <span className="eyebrow">Dashboard persona</span>
          <h3 style={{ marginTop: 6 }}>Which overview you land on</h3>
          <p className="sub" style={{ margin: "2px 0 12px" }}>Changes the Overview immediately, and is saved in this browser.</p>
          <div className="seg" style={{ width: "fit-content" }}>
            {ROLE_INFO.map((r) => (
              <button key={r.id} className={role === r.id ? "on" : ""} onClick={() => setRole(r.id)}>{r.label}</button>
            ))}
          </div>
          <p style={{ fontSize: 13, marginTop: 12, color: "var(--ink,#E6ECF5)" }}>
            {ROLE_INFO.find((r) => r.id === role)?.blurb}
          </p>
        </div>

        {/* ---- Cluster & workspace ---- */}
        <div className="card">
          <span className="eyebrow">Cluster &amp; workspace</span>
          <div className="mini" style={{ marginTop: 10 }}>
            <span className="dim">Active cluster</span>
            <span className="mono">{stats?.cluster_name || "—"}</span>
          </div>
          <div className="mini">
            <span className="dim">Exposure</span>
            {stats
              ? <span className={`tag ${BAND_TAG[stats.exposure_band]}`}>{stats.exposure_band} · {stats.exposure_score}</span>
              : <b>—</b>}
          </div>
          <div className="mini"><span className="dim">Loaded snapshots</span><b>{snaps.length}</b></div>

          {snaps.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {snaps.map((s) => (
                <div className="mini" key={s.snapshot_id}>
                  <span className="mono">{s.cluster_name}</span>
                  {s.current
                    ? <span className="tag tag-ok">current</span>
                    : <span className="dim mono" style={{ fontSize: 11 }}>{s.snapshot_id.slice(0, 8)}</span>}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => reload()}>Reload cluster</button>
            <button className="btn" onClick={reloadDemo} disabled={busy}>{busy ? "Loading…" : "Load demo cluster"}</button>
          </div>
          <p className="dim" style={{ fontSize: 12, marginTop: 12 }}>
            Connect a real cluster with the CLI: <span className="mono">kubegraph collect -o inventory.json</span>, then POST it to
            <span className="mono"> /inventory</span>.
          </p>
        </div>

        {/* ---- Connection & session ---- */}
        <div className="card">
          <span className="eyebrow">Connection &amp; session</span>
          <div className="mini" style={{ marginTop: 10 }}>
            <span className="dim">API endpoint</span>
            <span className="mono">{api.base}</span>
          </div>
          <div className="mini"><span className="dim">Backend version</span><span className="mono">v{version}</span></div>
          <div className="mini">
            <span className="dim">API docs</span>
            <a className="mono" href={`${api.base}/docs`} target="_blank" rel="noreferrer" style={{ color: "var(--brand,#6366F1)" }}>{api.base}/docs ↗</a>
          </div>
          <div className="mini"><span className="dim">Session token</span><span className="mono">expires {tokenExpiry(tokenStore.get())}</span></div>
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={copyToken}>{copied ? "Copied ✓" : "Copy access token"}</button>
            <button className="btn" style={{ background: "var(--high,#E11D48)" }} onClick={logout}>Sign out</button>
          </div>
          <p className="dim" style={{ fontSize: 12, marginTop: 12 }}>
            The access token authenticates API calls — handy for testing with <span className="mono">curl</span>. Keep it private.
          </p>
        </div>

        <p className="dim" style={{ fontSize: 12, textAlign: "center", paddingBottom: 12 }}>
          KubeGraph — graph-theoretic Kubernetes privilege-escalation analysis · defensive use only, on clusters you own.
        </p>
      </div>
    </div>
  );
}
