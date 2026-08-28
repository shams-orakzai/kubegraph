import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { api } from "../api/client";
import type { Stats } from "../api/types";

interface ClusterCtx {
  stats: Stats | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const Ctx = createContext<ClusterCtx | null>(null);

export function ClusterProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Ensure a cluster is loaded; seed the demo if the workspace is empty.
      const snaps = await api.snapshots();
      if (snaps.length === 0) await api.loadDemo();
      setStats(await api.stats());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <Ctx.Provider value={{ stats, loading, error, reload: load }}>
      {children}
    </Ctx.Provider>
  );
}

export function useCluster(): ClusterCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useCluster must be used within ClusterProvider");
  return c;
}
