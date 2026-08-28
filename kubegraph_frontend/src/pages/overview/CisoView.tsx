import { useNavigate } from "react-router-dom";
import type { FleetItem, Stats } from "../../api/types";
import { BAND_TAG } from "../overviewUtils";

function band(score: number): string {
  return score < 30 ? "Low" : score < 60 ? "Medium" : "High";
}

export default function CisoView({ stats, fleet }: { stats: Stats; fleet: FleetItem[] }) {
  const nav = useNavigate();
  const n = fleet.length || 1;
  const avg = Math.round(fleet.reduce((s, f) => s + f.exposure_score, 0) / n);
  const highRisk = fleet.filter((f) => f.exposure_band === "High").length;
  const adminReachable = fleet.reduce((s, f) => s + f.footholds_reaching_target, 0);
  const totalPaths = fleet.reduce((s, f) => s + f.paths, 0);

  return (
    <>
      <h1 className="h1">Security posture</h1>
      <p className="lede">Executive view — exposure across the fleet and where the risk is concentrated.</p>

      <div className="tiles">
        <div className="tile"><div className="k">Fleet exposure</div><div className="v" style={{ color: avg >= 60 ? "var(--high)" : avg >= 30 ? "var(--med)" : "var(--low)" }}>{band(avg)}</div><div className="d dim">avg score {avg}</div></div>
        <div className="tile"><div className="k">Clusters at high risk</div><div className="v" style={{ color: "var(--high)" }}>{highRisk}</div><div className="d dim">of {fleet.length}</div></div>
        <div className="tile"><div className="k">Admin-reachable workloads</div><div className="v">{adminReachable}</div><div className="d dim">across fleet</div></div>
        <div className="tile"><div className="k">Total attack paths</div><div className="v">{totalPaths}</div><div className="d dim">to cluster-admin</div></div>
      </div>

      <div className="grid2">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Risk by cluster</h3>
            <button className="btn btn-ghost" onClick={() => nav("/fleet")}>Fleet view ↗</button>
          </div>
          <div style={{ marginTop: 12 }}>
            {fleet.map((f) => (
              <div className="mini" key={f.snapshot_id}>
                <span className="mono">{f.cluster_name}</span>
                <span>
                  <span className="riskbar"><i style={{ width: `${f.exposure_score}%`, background: f.exposure_band === "High" ? "var(--high)" : f.exposure_band === "Medium" ? "var(--med)" : "var(--low)" }} /></span>
                  <b>{f.exposure_score}</b>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Readiness</h3>
          <div style={{ marginTop: 12 }}>
            <div className="mini"><span className="dim">Current cluster</span><span className="mono">{stats.cluster_name}</span></div>
            <div className="mini"><span className="dim">Exposure</span><span className={`tag ${BAND_TAG[stats.exposure_band]}`}>{stats.exposure_band} · {stats.exposure_score}</span></div>
            <div className="mini"><span className="dim">Single-fix cuts available</span><b>{stats.choke_points}</b></div>
          </div>
          {stats.choke_points > 0 && (
            <div className="callout" style={{ marginTop: 16 }}>
              <div className="bolt">✓</div>
              <div><b>Fastest win:</b> resolving {stats.choke_points} critical fix{stats.choke_points > 1 ? "es" : ""} removes every path to admin on {stats.cluster_name} and drops its exposure to Low.</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
