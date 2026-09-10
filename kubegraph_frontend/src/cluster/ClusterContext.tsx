import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { api } from "../api/client";
import type { DemoCatalogItem, SnapshotSummary, Stats } from "../api/types";

interface ClusterCtx {
  stats: Stats | null;
  loading: boolean;
  switching: boolean;
  error: string | null;
  catalog: DemoCatalogItem[];
  snapshots: SnapshotSummary[];
  reload: () => void;
  refreshMeta: () => Promise<void>;
  switchToCatalog: (id: string) => Promise<void>;
  selectSnapshot: (sid: string) => Promise<void>;
}

const Ctx = createContext<ClusterCtx | null>(null);

export function ClusterProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<DemoCatalogItem[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotSummary[]>([]);

  const refreshMeta = useCallback(async () => {
    try {
      const [cat, snaps] = await Promise.all([api.demoCatalog(), api.snapshots()]);
      setCatalog(cat);
      setSnapshots(snaps);
    } catch { /* non-fatal: the dropdown just won't populate */ }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Ensure a cluster is loaded; seed the default demo if the workspace is empty.
      const snaps = await api.snapshots();
      if (snaps.length === 0) await api.loadDemo();
      setStats(await api.stats());
      await refreshMeta();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [refreshMeta]);

  useEffect(() => { void load(); }, [load]);

  // Switch the active cluster, then refresh stats and dropdown state.
  const applySwitch = useCallback(async (fn: () => Promise<{ stats: Stats }>) => {
    setSwitching(true);
    setError(null);
    try {
      const res = await fn();
      setStats(res.stats);
      await refreshMeta();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSwitching(false);
    }
  }, [refreshMeta]);

  const switchToCatalog = useCallback(
    (id: string) => applySwitch(() => api.loadDemo(id)),
    [applySwitch]);

  const selectSnapshot = useCallback(
    (sid: string) => applySwitch(() => api.selectSnapshot(sid)),
    [applySwitch]);

  return (
    <Ctx.Provider value={{
      stats, loading, switching, error, catalog, snapshots,
      reload: load, refreshMeta, switchToCatalog, selectSnapshot,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export function useCluster(): ClusterCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useCluster must be used within ClusterProvider");
  return c;
}
