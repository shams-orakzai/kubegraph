import type { BlastRadius, PathResponse, Remediation } from "../api/client";

export type Selection =
  | { kind: "none" }
  | { kind: "path"; path: PathResponse }
  | { kind: "cut"; rem: Remediation }
  | { kind: "blast"; blast: BlastRadius };

export default function DetailDrawer({ selection }: { selection: Selection }) {
  if (selection.kind === "none") {
    return (
      <div className="drawer drawer-empty">
        <span className="dim">
          Select a path, a remediation, or a node to inspect it here.
        </span>
      </div>
    );
  }

  if (selection.kind === "path") {
    const p = selection.path;
    return (
      <div className="drawer">
        <span className="eyebrow">Attack path · {p.length} hops</span>
        <div className="hopline">
          <span className="chip chip-pod mono">{p.foothold_label}</span>
          {p.hops.map((h, i) => (
            <span key={i} className="hopseg">
              <span className="hop-etype mono">{h.etype}</span>
              <span className="chip mono">{h.to_label}</span>
            </span>
          ))}
        </div>
      </div>
    );
  }

  if (selection.kind === "cut") {
    const r = selection.rem;
    return (
      <div className="drawer">
        <span className="eyebrow accent">Remediation #{r.rank}</span>
        <div className="drawer-title">{r.description}</div>
        <div className="stat-row">
          <Stat label="Footholds cut" value={`${r.footholds_cut}`} big />
          <Stat label="Paths severed" value={`${r.paths_cut}`} />
          <Stat label="Edge type" value={r.etype} mono />
          <Stat label="Centrality" value={`${r.centrality}`} />
        </div>
      </div>
    );
  }

  const b = selection.blast;
  return (
    <div className="drawer">
      <span className="eyebrow">Blast radius</span>
      <div className="drawer-title mono">{b.node}</div>
      <p className="panel-sub">Reaches {b.reachable_count} entities:</p>
      <div className="chips">
        {b.reachable.slice(0, 24).map((n) => (
          <span key={n} className="chip mono">{n}</span>
        ))}
        {b.reachable_count > 24 && <span className="dim">+{b.reachable_count - 24} more</span>}
      </div>
    </div>
  );
}

function Stat({ label, value, big, mono }: { label: string; value: string; big?: boolean; mono?: boolean }) {
  return (
    <div className="stat">
      <div className={`stat-value ${big ? "stat-big" : ""} ${mono ? "mono" : ""}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
