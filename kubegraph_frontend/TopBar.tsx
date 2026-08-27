import type { Stats } from "../api/client";
import { NODE_TYPE_LABELS } from "../theme";

interface Props {
  stats: Stats | null;
  layout: string;
  showStructural: boolean;
  onLayout: (l: string) => void;
  onToggleStructural: () => void;
  onReload: () => void;
  onReset: () => void;
}

const LAYOUTS = ["breadthfirst", "cose", "concentric", "circle"];

export default function TopBar({
  stats, layout, showStructural, onLayout, onToggleStructural, onReload, onReset,
}: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="mark">Kube<span className="mark-accent">Graph</span></span>
        <span className="brand-sub mono">privilege-escalation attack paths</span>
      </div>

      <div className="cluster">
        {stats && (
          <>
            <span className="cluster-name mono">{stats.cluster_name}</span>
            <span className="chips-inline">
              <Chip value={`${stats.footholds_reaching_target}/${stats.footholds}`} label="footholds reach admin" danger />
              <Chip value={`${stats.nodes}`} label="nodes" />
              <Chip value={`${stats.edges}`} label="edges" />
              <Chip value={`${stats.removable_edges}`} label="removable" />
            </span>
          </>
        )}
      </div>

      <div className="controls">
        <select className="ctl" value={layout} onChange={(e) => onLayout(e.target.value)} aria-label="Graph layout">
          {LAYOUTS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <button className={`ctl ${showStructural ? "ctl-on" : ""}`} onClick={onToggleStructural}>
          structural edges
        </button>
        <button className="ctl" onClick={onReset}>reset view</button>
        <button className="ctl ctl-primary" onClick={onReload}>reload cluster</button>
      </div>

      <div className="legend" aria-label="Legend">
        {Object.entries(NODE_TYPE_LABELS).map(([k, v]) => (
          <span key={k} className="legend-item">
            <span className="swatch" style={{ background: v.color }} />
            <span className="dim">{v.label}</span>
          </span>
        ))}
      </div>
    </header>
  );
}

function Chip({ value, label, danger }: { value: string; label: string; danger?: boolean }) {
  return (
    <span className={`stat-chip ${danger ? "stat-chip-danger" : ""}`}>
      <span className="stat-chip-value mono">{value}</span>
      <span className="stat-chip-label">{label}</span>
    </span>
  );
}
