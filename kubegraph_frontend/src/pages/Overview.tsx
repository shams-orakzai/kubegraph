import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { FleetItem, PathResponse, Remediation } from "../api/types";
import { useCluster } from "../cluster/ClusterContext";
import { useRole } from "../layout/AppShell";
import EngineerView from "./overview/EngineerView";
import PlatformView from "./overview/PlatformView";
import CisoView from "./overview/CisoView";

interface Extra { paths: PathResponse[]; rems: Remediation[]; fleet: FleetItem[]; }

export default function Overview() {
  const { stats, loading, error } = useCluster();
  const role = useRole();
  const [extra, setExtra] = useState<Extra | null>(null);
  const [xerr, setXerr] = useState<string | null>(null);

  // Fetch role data only once the cluster (stats) is loaded, to avoid racing
  // the demo-seed in ClusterContext.
  useEffect(() => {
    if (!stats) return;
    let cancelled = false;
    setExtra(null); setXerr(null);
    (async () => {
      try {
        const [paths, rems, fleet] = await Promise.all([
          api.paths(), api.remediations(12), api.fleet(),
        ]);
        if (!cancelled) setExtra({ paths, rems, fleet });
      } catch (e) {
        if (!cancelled) setXerr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [stats]);

  if (error) return (
    <div className="page"><div className="err" style={{ maxWidth: 560 }}>
      {error}. Start the backend: <span className="mono">uvicorn kubegraph.api.app:app --port 8000</span>
    </div></div>
  );
  if (loading || !stats || (!extra && !xerr)) {
    return <div className="page"><div className="spinner" /></div>;
  }
  if (xerr || !extra) {
    return <div className="page"><div className="err" style={{ maxWidth: 560 }}>{xerr}</div></div>;
  }

  return (
    <div className="page">
      {role === "engineer" && <EngineerView stats={stats} paths={extra.paths} rems={extra.rems} />}
      {role === "platform" && <PlatformView stats={stats} rems={extra.rems} />}
      {role === "ciso" && <CisoView stats={stats} fleet={extra.fleet} />}
    </div>
  );
}
