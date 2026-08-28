import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { FleetItem } from "../api/types";
import { useCluster } from "../cluster/ClusterContext";
import { BAND_TAG } from "./overviewUtils";

function bandOf(score: number): string {
  return score < 30 ? "Low" : score < 60 ? "Medium" : "High";
}
function bandColor(band: string): string {
  return band === "High" ? "var(--high)" : band === "Medium" ? "var(--med)" : "var(--low)";
}

export default function Fleet() {
  const { stats, error: clusterErr } = useCluster();
  const [fleet, setFleet] = useState<FleetItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!stats) return;
    let cancelled = false;
    (async () => {
      try {
        const f = await api.fleet();
        if (!cancelled) setFleet(f);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [stats]);

  if (clusterErr || err) return <div className="page"><div className="err">{clusterErr || err}</div></div>;
  if (!stats || !fleet) return <div className="page"><div className="spinner" /></div>;

  const n = fleet.length || 1;
  const avg = Math.round(fleet.reduce((s, f) => s + f.exposure_score, 0) / n);
  const highRisk = fleet.filter((f) => f.exposure_band === "High").length;
  const totalPaths = fleet.reduce((s, f) => s + f.paths, 0);

  return (
    <div className="page">
      <h1 className="h1">Cluster fleet</h1>
      <p className="lede">Exposure across every connected cluster, worst first.</p>

      <div className="tiles">
        <div className="tile"><div className="k">Clusters</div><div className="v">{fleet.length}</div><div className="d dim">connected</div></div>
        <div className="tile"><div className="k">High risk</div><div className="v" style={{ color: "var(--high)" }}>{highRisk}</div><div className="d dim">of {fleet.length}</div></div>
        <div className="tile"><div className="k">Total attack paths</div><div className="v">{totalPaths}</div><div className="d dim">to cluster-admin</div></div>
        <div className="tile"><div className="k">Fleet exposure</div><div className="v" style={{ color: bandColor(bandOf(avg)) }}>{avg}</div><div className="d dim">avg · {bandOf(avg)}</div></div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <table>
          <thead>
            <tr>
              <th>Cluster</th><th>Exposure</th><th>Footholds → admin</th>
              <th>Paths</th><th>Choke points</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {fleet.map((f) => (
              <tr key={f.snapshot_id}>
                <td className="mono">
                  {f.cluster_name}
                  {f.current && <span className="tag tag-ok" style={{ marginLeft: 8 }}>current</span>}
                </td>
                <td>
                  <span className="riskbar"><i style={{ width: `${f.exposure_score}%`, background: bandColor(f.exposure_band) }} /></span>
                  <b>{f.exposure_score}</b>
                </td>
                <td className="mono">{f.footholds_reaching_target} / {f.footholds}</td>
                <td className="mono">{f.paths}</td>
                <td className="mono">{f.choke_points}</td>
                <td><span className={`tag ${BAND_TAG[f.exposure_band]}`}>{f.exposure_band}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {fleet.length === 1 && (
        <p className="dim" style={{ fontSize: 12, marginTop: 14 }}>
          Only one cluster is loaded. Connect more via the collector or the <span className="mono">/inventory</span> API to compare across your fleet.
        </p>
      )}
    </div>
  );
}
