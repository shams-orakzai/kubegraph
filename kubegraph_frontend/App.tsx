import { useCallback, useEffect, useState } from "react";
import {
  api, type GraphResponse, type PathResponse, type Remediation, type Stats,
} from "./api/client";
import TopBar from "./components/TopBar";
import PathsPanel from "./components/PathsPanel";
import RemediationsPanel from "./components/RemediationsPanel";
import GraphView, { type Highlight } from "./components/GraphView";
import DetailDrawer, { type Selection } from "./components/DetailDrawer";

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [paths, setPaths] = useState<PathResponse[]>([]);
  const [rems, setRems] = useState<Remediation[]>([]);

  const [layout, setLayout] = useState("breadthfirst");
  const [showStructural, setShowStructural] = useState(true);
  const [highlight, setHighlight] = useState<Highlight>({ kind: "none" });
  const [selection, setSelection] = useState<Selection>({ kind: "none" });
  const [selKey, setSelKey] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await api.loadDemo();
      const [s, g, p, r] = await Promise.all([
        api.stats(), api.graph(), api.paths(), api.remediations(12),
      ]);
      setStats(s); setGraph(g); setPaths(p); setRems(r);
      clearSelection();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  function clearSelection() {
    setHighlight({ kind: "none" });
    setSelection({ kind: "none" });
    setSelKey(null);
  }

  function onSelectPath(p: PathResponse) {
    setSelKey(p.foothold);
    setHighlight({ kind: "path", nodes: p.nodes });
    setSelection({ kind: "path", path: p });
  }

  function onSelectRem(r: Remediation) {
    setSelKey(r.edge_id);
    setHighlight({ kind: "cut", edgeId: r.edge_id });
    setSelection({ kind: "cut", rem: r });
  }

  async function onNodeClick(id: string) {
    try {
      const b = await api.blastRadius(id);
      setSelKey(id);
      setHighlight({ kind: "blast", node: id, reachable: b.reachable });
      setSelection({ kind: "blast", blast: b });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="app">
      <TopBar
        stats={stats}
        layout={layout}
        showStructural={showStructural}
        onLayout={setLayout}
        onToggleStructural={() => setShowStructural((v) => !v)}
        onReload={() => void load()}
        onReset={clearSelection}
      />

      <main className="stage">
        <PathsPanel
          paths={paths}
          selected={selection.kind === "path" ? selKey : null}
          onSelect={onSelectPath}
        />

        <section className="center">
          {error && (
            <div className="banner banner-error">
              Can't reach the backend at <span className="mono">{api.base}</span> — {error}.
              Start it with <span className="mono">uvicorn kubegraph.api.app:app</span>, then reload.
            </div>
          )}
          {loading && !graph && <div className="banner">Loading cluster…</div>}
          <GraphView
            graph={graph}
            layout={layout}
            showStructural={showStructural}
            highlight={highlight}
            onNodeClick={onNodeClick}
          />
        </section>

        <RemediationsPanel
          remediations={rems}
          stats={stats}
          selected={selection.kind === "cut" ? selKey : null}
          onSelect={onSelectRem}
        />
      </main>

      <DetailDrawer selection={selection} />
    </div>
  );
}
