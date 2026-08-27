import type { PathResponse } from "../api/client";

interface Props {
  paths: PathResponse[];
  selected: string | null;
  onSelect: (p: PathResponse) => void;
}

export default function PathsPanel({ paths, selected, onSelect }: Props) {
  return (
    <aside className="panel panel-left">
      <div className="panel-head">
        <span className="eyebrow">Attack paths</span>
        <h2>Footholds → admin</h2>
        <p className="panel-sub">
          {paths.length} pod{paths.length === 1 ? "" : "s"} can reach cluster-admin.
          Select one to trace its route.
        </p>
      </div>
      <ul className="list">
        {paths.map((p) => (
          <li key={p.foothold}>
            <button
              className={`row ${selected === p.foothold ? "row-active" : ""}`}
              onClick={() => onSelect(p)}
            >
              <span className="mono row-title">{p.foothold_label}</span>
              <span className="tag tag-len">{p.length} hops</span>
              <span className="row-chain mono">
                {p.hops.map((h, i) => (
                  <span key={i}>
                    {i > 0 && <span className="dim"> · </span>}
                    {h.etype}
                  </span>
                ))}
              </span>
            </button>
          </li>
        ))}
        {paths.length === 0 && <li className="empty">No paths to cluster-admin.</li>}
      </ul>
    </aside>
  );
}
