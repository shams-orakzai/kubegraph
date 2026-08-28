import { useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useCluster } from "../cluster/ClusterContext";

const TITLES: Record<string, string> = {
  "/": "Overview", "/graph": "Attack graph", "/remediations": "Remediations",
  "/fleet": "Fleet", "/settings": "Settings",
};

const ROLES: { id: "engineer" | "platform" | "ciso"; label: string }[] = [
  { id: "engineer", label: "Engineer" },
  { id: "platform", label: "Platform" },
  { id: "ciso", label: "CISO" },
];

export default function TopBar({ role, onRole }: {
  role: string;
  onRole: (r: "engineer" | "platform" | "ciso") => void;
}) {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const { stats } = useCluster();
  const title = TITLES[pathname] || "Overview";

  return (
    <header className="top">
      <div className="crumb">{title} / <b>{stats?.cluster_name || "…"}</b></div>
      <div className="grow" />
      <div className="select"><span className="dot" /> {stats?.cluster_name || "no cluster"} <span className="dim">▾</span></div>
      {/* Role switcher only meaningful on the Overview */}
      <div className="seg">
        {ROLES.map((r) => (
          <button key={r.id} className={role === r.id ? "on" : ""} onClick={() => onRole(r.id)}>{r.label}</button>
        ))}
      </div>
      <button className="btn" title={`Signed in as ${user?.email}`}>Export report</button>
    </header>
  );
}
