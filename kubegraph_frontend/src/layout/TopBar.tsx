import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useCluster } from "../cluster/ClusterContext";
import type { DemoCatalogItem } from "../api/types";

const TITLES: Record<string, string> = {
  "/": "Overview", "/graph": "Attack graph", "/remediations": "Remediations",
  "/fleet": "Fleet", "/settings": "Settings",
};

const ROLES: { id: "engineer" | "platform" | "ciso"; label: string }[] = [
  { id: "engineer", label: "Engineer" },
  { id: "platform", label: "Platform" },
  { id: "ciso", label: "CISO" },
];

const BAND_COLOR: Record<string, string> = {
  High: "var(--high)", Medium: "var(--med)", Low: "var(--low)",
};

function ClusterPicker() {
  const {
    stats, catalog, snapshots, switching, switchToCatalog, selectSnapshot,
  } = useCluster();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Group the catalog, and surface any imported (non-catalog) snapshots too.
  const groups = useMemo(() => {
    const order = ["Featured", "Evaluation corpus"];
    const byGroup = new Map<string, DemoCatalogItem[]>();
    for (const c of catalog) {
      if (!byGroup.has(c.group)) byGroup.set(c.group, []);
      byGroup.get(c.group)!.push(c);
    }
    const known = new Set(catalog.map((c) => c.cluster_name));
    const imported = snapshots.filter((s) => !known.has(s.cluster_name));
    const ordered = [...order.filter((g) => byGroup.has(g)),
                     ...[...byGroup.keys()].filter((g) => !order.includes(g))];
    return { byGroup, ordered, imported };
  }, [catalog, snapshots]);

  const activeName = stats?.cluster_name ?? "no cluster";
  const dotColor = stats ? BAND_COLOR[stats.exposure_band] ?? "var(--faint)" : "var(--faint)";

  const pickCatalog = async (id: string) => { setOpen(false); await switchToCatalog(id); };
  const pickSnapshot = async (sid: string) => { setOpen(false); await selectSnapshot(sid); };

  return (
    <div className="cluster-select" ref={ref}>
      <button className="select" onClick={() => setOpen((o) => !o)}
              disabled={switching} title="Switch synthetic cluster">
        <span className="dot" style={{ background: dotColor }} />
        {switching ? "Loading…" : activeName}
        <span className="dim">▾</span>
      </button>

      {open && (
        <div className="cluster-menu" role="menu">
          {groups.ordered.map((g) => (
            <div key={g}>
              <div className="grp">{g}</div>
              {groups.byGroup.get(g)!.map((c) => (
                <button key={c.id} className={`item${c.current ? " on" : ""}`}
                        role="menuitem" onClick={() => void pickCatalog(c.id)}>
                  <div className="it-name">
                    {c.name}
                    {c.current && <span className="chk">✓</span>}
                  </div>
                  <div className="it-desc">{c.description}</div>
                </button>
              ))}
            </div>
          ))}

          {groups.imported.length > 0 && (
            <div>
              <div className="grp">Imported</div>
              {groups.imported.map((s) => (
                <button key={s.snapshot_id} className={`item${s.current ? " on" : ""}`}
                        role="menuitem" onClick={() => void pickSnapshot(s.snapshot_id)}>
                  <div className="it-name">
                    <span className="mono">{s.cluster_name}</span>
                    {s.current && <span className="chk">✓</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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
      <ClusterPicker />
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
