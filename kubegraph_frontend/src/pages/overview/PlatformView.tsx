import { useNavigate } from "react-router-dom";
import type { Remediation, Stats } from "../../api/types";
import { cutTag } from "../overviewUtils";

export default function PlatformView({ stats, rems }: { stats: Stats; rems: Remediation[] }) {
  const nav = useNavigate();
  const critical = rems.filter((r) => r.footholds_cut >= stats.footholds_reaching_target && stats.footholds_reaching_target > 0).length;

  return (
    <>
      <h1 className="h1">What to fix first</h1>
      <p className="lede">Prioritised by how many attack paths each change removes. Work top-down for the fastest exposure drop.</p>

      <div className="tiles">
        <div className="tile"><div className="k">Open findings</div><div className="v">{stats.removable_edges}</div><div className="d dim">removable grants</div></div>
        <div className="tile"><div className="k">Critical fixes</div><div className="v" style={{ color: "var(--high)" }}>{critical}</div><div className="d" style={{ color: "var(--high)" }}>cut all footholds</div></div>
        <div className="tile"><div className="k">Attack paths</div><div className="v">{stats.paths}</div><div className="d dim">to cluster-admin</div></div>
        <div className="tile"><div className="k">Workloads at risk</div><div className="v">{stats.footholds_reaching_target}/{stats.footholds}</div><div className="d dim">reach admin</div></div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>Remediation backlog</h3>
          <button className="btn btn-ghost" onClick={() => nav("/remediations")}>Full list ↗</button>
        </div>
        <table style={{ marginTop: 10 }}>
          <thead><tr><th>Priority</th><th>Fix</th><th>Impact</th><th>Type</th><th>Assign</th></tr></thead>
          <tbody>
            {rems.map((r) => (
              <tr className="click" key={r.edge_id}>
                <td><span className="rank">{r.rank}</span></td>
                <td className="mono">{r.description}</td>
                <td><span className={`tag ${cutTag(r.footholds_cut, stats.footholds_reaching_target)}`}>{r.footholds_cut}/{stats.footholds_reaching_target} · {r.paths_cut} paths</span></td>
                <td className="mono">{r.etype}</td>
                <td><button className="btn btn-ghost" title="Ticketing integration coming later" style={{ padding: "5px 10px" }}>— assign</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
