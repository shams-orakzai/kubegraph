import type { Remediation, Stats } from "../api/client";

interface Props {
  remediations: Remediation[];
  stats: Stats | null;
  selected: string | null;
  onSelect: (r: Remediation) => void;
}

export default function RemediationsPanel({ remediations, stats, selected, onSelect }: Props) {
  const total = stats?.footholds_reaching_target ?? 0;
  return (
    <aside className="panel panel-right">
      <div className="panel-head">
        <span className="eyebrow accent">Remediations</span>
        <h2>Highest-impact fixes</h2>
        <p className="panel-sub">
          Ranked by attack paths severed. Select one to preview the cut.
        </p>
      </div>
      <ul className="list">
        {remediations.map((r) => {
          const share = total ? Math.round((r.footholds_cut / total) * 100) : 0;
          return (
            <li key={r.edge_id}>
              <button
                className={`rem ${selected === r.edge_id ? "row-active" : ""}`}
                onClick={() => onSelect(r)}
              >
                <div className="rem-top">
                  <span className="rank">#{r.rank}</span>
                  <span className="rem-cut mono">
                    {r.footholds_cut}/{total} footholds
                  </span>
                </div>
                <div className="rem-desc">{r.description}</div>
                <div className="meter" aria-hidden>
                  <span className="meter-fill" style={{ width: `${share}%` }} />
                </div>
                <div className="rem-meta mono dim">
                  {r.paths_cut} paths · centrality {r.centrality}
                </div>
              </button>
            </li>
          );
        })}
        {remediations.length === 0 && <li className="empty">No remediations computed.</li>}
      </ul>
    </aside>
  );
}
