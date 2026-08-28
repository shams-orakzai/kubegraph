import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const ROLE_LABEL: Record<string, string> = {
  engineer: "Security Engineer", platform: "Platform Lead", ciso: "CISO",
};

const items = [
  { to: "/", icon: "◎", label: "Overview", end: true },
  { to: "/graph", icon: "⧉", label: "Attack graph" },
  { to: "/remediations", icon: "✓", label: "Remediations" },
  { to: "/fleet", icon: "☰", label: "Fleet" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const initials = (user?.name || "U").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase();
  return (
    <aside className="side">
      <div className="brand"><div className="mark" /><b>KubeGraph</b></div>
      <nav className="nav">
        {items.map((it) => (
          <NavLink key={it.to} to={it.to} end={it.end}
                   className={({ isActive }) => (isActive ? "on" : "")}>
            <span className="ic">{it.icon}</span> {it.label}
          </NavLink>
        ))}
        <div className="grp">Workspace</div>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "on" : "")}>
          <span className="ic">⚙</span> Settings
        </NavLink>
      </nav>
      <div className="spacer" />
      <div className="usr">
        <div className="av">{initials}</div>
        <div className="meta"><b>{user?.name}</b><small>{ROLE_LABEL[user?.role || "engineer"]}</small></div>
        <button className="out" title="Sign out" onClick={logout}>⇥</button>
      </div>
    </aside>
  );
}
