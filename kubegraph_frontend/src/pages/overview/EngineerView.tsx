import { useNavigate } from "react-router-dom";
import type { PathResponse, Remediation, Stats } from "../../api/types";
import ExposureDonut from "../../components/ExposureDonut";
import { BAND_TAG, cutTag, impactPct } from "../overviewUtils";

export default function EngineerView({ stats, paths, rems }: {
  stats: Stats; paths: PathResponse[]; rems: Remediation[];
}) {
  const nav = useNavigate();
  const maxPaths = rems.length ? Math.max(...rems.map((r) => r.paths_cut)) : 1;

  return (
    <>
      <h1 className="h1">Cluster posture</h1>
      <p className="lede">
        {stats.footholds_reaching_target} of {stats.footholds} workloads can reach cluster-admin.
        {stats.choke_points > 0 && ` ${stats.choke_points} choke point${stats.choke_points > 1 ? "s" : ""}; one fix removes every path.`}
      </p>

      <div className="grid3">
        {/* left: exposure + footholds */}
        <div className="stack">
          <div className="card">
            <span className="eyebrow">Exposure score</span>
            <div className="donut" style={{ marginTop: 12 }}>
              <ExposureDonut score={stats.exposure_score} band={stats.exposure_band} />
              <div style={{ flex: 1 }}>
                <span className={`tag ${BAND_TAG[stats.exposure_band]}`}>
                  {stats.exposure_band === "High" ? "Needs attention" : stats.exposure_band}
                </span>
                <div style={{ marginTop: 10 }}>
                  <div className="mini"><span className="dim">Footholds → admin</span><b style={{ color: "var(--high)" }}>{stats.footholds_reaching_target} / {stats.footholds}</b></div>
                  <div className="mini"><span className="dim">Attack paths</span><b>{stats.paths}</b></div>
                  <div className="mini"><span className="dim">Choke points</span><b>{stats.choke_points}</b></div>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Footholds → admin</h3>
            <p className="sub">Every pod that can reach cluster-admin</p>
            {paths.map((p) => (
              <div className="mini" key={p.foothold}>
                <span className="mono" style={{ color: "#0F766E" }}>{p.foothold_label}</span>
                <span className="mono dim">{p.length} hops</span>
              </div>
            ))}
            {paths.length === 0 && <div className="dim" style={{ fontSize: 12 }}>No paths to cluster-admin.</div>}
          </div>
        </div>

        {/* center: attack path traces */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div><h3>Critical attack paths</h3><p className="sub" style={{ margin: 0 }}>Escalation routes to cluster-admin</p></div>
            <button className="btn btn-ghost" onClick={() => nav("/graph")}>Open graph ↗</button>
          </div>
          {paths.map((p) => (
            <div key={p.foothold} style={{ padding: "10px 0", borderTop: "1px solid var(--line2)" }}>
              <div className="hopline">
                <span className="chip chip-pod">{p.foothold_label}</span>
                {p.hops.map((h, i) => (
                  <span key={i} className="hopline" style={{ display: "contents" }}>
                    <span className="hop-etype">{h.etype}</span>
                    <span className="chip">{h.to_label}</span>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* right: top remediations */}
        <div className="card">
          <h3>Top remediations</h3>
          <p className="sub">By attack paths removed</p>
          {rems.slice(0, 4).map((r) => (
            <div className="fix" key={r.edge_id}>
              <div className="fix-top">
                <span className="rank">{r.rank}</span>
                <span className={`tag ${cutTag(r.footholds_cut, stats.footholds_reaching_target)}`}>
                  {r.footholds_cut}/{stats.footholds_reaching_target}
                </span>
              </div>
              <div className="fix-desc">{r.description}</div>
              <div className="meter"><i style={{ width: `${impactPct(r, maxPaths)}%` }} /></div>
              <div className="fix-meta">{r.paths_cut} paths · centrality {r.centrality}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
