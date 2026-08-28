import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Remediation } from "../api/types";
import { useCluster } from "../cluster/ClusterContext";
import { cutTag } from "./overviewUtils";

export default function Remediations() {
  const { stats, error: clusterErr } = useCluster();
  const nav = useNavigate();
  const [rems, setRems] = useState<Remediation[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!stats) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await api.remediations(50);
        if (!cancelled) setRems(r);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [stats]);

  if (clusterErr || err) return <div className="page"><div className="err">{clusterErr || err}</div></div>;
  if (!stats || !rems) return <div className="page"><div className="spinner" /></div>;

  const reaching = stats.footholds_reaching_target;
  const hasZeroCut = rems.some((r) => r.footholds_cut === 0);

  return (
    <div className="page">
      <h1 className="h1">Remediations</h1>
      <p className="lede">
        Every fix, ranked by how many attack paths it severs. Apply in order for the fastest exposure drop.
      </p>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Remediation</th><th>Footholds cut</th>
              <th>Paths severed</th><th>Centrality</th><th>Type</th><th></th>
            </tr>
          </thead>
          <tbody>
            {rems.map((r) => (
              <tr key={r.edge_id}>
                <td><span className="rank">{r.rank}</span></td>
                <td className="mono">{r.description}</td>
                <td><span className={`tag ${cutTag(r.footholds_cut, reaching)}`}>{r.footholds_cut} / {reaching}</span></td>
                <td className="mono">{r.paths_cut}</td>
                <td className="mono">{r.centrality}</td>
                <td className="mono">{r.etype}</td>
                <td>
                  <button className="btn btn-ghost" style={{ padding: "6px 12px" }}
                          onClick={() => nav(`/graph?cut=${encodeURIComponent(r.edge_id)}`)}>
                    Preview ↗
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasZeroCut && (
        <div className="callout" style={{ marginTop: 18, maxWidth: 760 }}>
          <div className="bolt">i</div>
          <div>
            <b>Why some fixes cut 0 footholds:</b> "create pods cluster-wide" is a redundant mesh —
            block one route and the attacker hops through another service account. The correct single
            fix is removing the underlying <span className="mono">Role rule</span>, which deletes all
            those edges at once. <i>(Object-level remediation ranking is the next analytical refinement.)</i>
          </div>
        </div>
      )}
    </div>
  );
}
