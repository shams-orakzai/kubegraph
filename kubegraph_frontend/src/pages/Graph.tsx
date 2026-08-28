import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { api } from "../api/client";
import type { GraphResponse, PathResponse, Remediation } from "../api/types";
import { useCluster } from "../cluster/ClusterContext";
import { cyStylesheet, edgeCategory } from "../graph/cyStyle";

type Mode = "paths" | "full";
type Highlight =
  | { kind: "none" }
  | { kind: "path"; nodes: string[]; label: string }
  | { kind: "blast"; node: string; reachable: string[]; label: string }
  | { kind: "cut"; edgeId: string; label: string };

const LEGEND = [
  ["#FF5D73", "target"], ["#2DD4BF", "pod"], ["#5B9DFF", "service account"],
  ["#F5B23D", "role"], ["#B98CFF", "secret"],
] as const;

/** Only the nodes/edges that lie on a shortest attack path to the target. */
function pathElements(graph: GraphResponse, paths: PathResponse[]): ElementDefinition[] {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  for (const p of paths) {
    p.nodes.forEach((n) => nodeIds.add(n));
    for (let i = 0; i < p.nodes.length - 1; i++) edgeIds.add(`${p.nodes[i]}->${p.nodes[i + 1]}`);
  }
  const nodes = graph.nodes.filter((n) => nodeIds.has(n.data.id)).map((n) => ({ data: { ...n.data } }));
  const edges = graph.edges.filter((e) => edgeIds.has(e.data.id))
    .map((e) => ({ data: { ...e.data, cat: edgeCategory(e.data.etype) } }));
  return [...nodes, ...edges];
}

function fullElements(graph: GraphResponse, showStructural: boolean): ElementDefinition[] {
  const nodes = graph.nodes.map((n) => ({ data: { ...n.data } }));
  const edges = graph.edges
    .map((e) => ({ data: { ...e.data, cat: edgeCategory(e.data.etype) } }))
    .filter((e) => showStructural || e.data.cat !== "struct");
  return [...nodes, ...edges];
}

/** Tiered top-down layout: target at the top, footholds at the bottom,
 *  tiers by undirected distance from the target. Mirrors the prototype. */
function layered(cy: Core) {
  const target = cy.nodes('[ntype="Target"]');
  const dist = new Map<string, number>();
  if (target.nonempty()) {
    const root = target.first().id();
    dist.set(root, 0);
    let frontier = [root];
    while (frontier.length) {
      const next: string[] = [];
      for (const id of frontier) {
        cy.getElementById(id).neighborhood("node").forEach((nb) => {
          if (!dist.has(nb.id())) { dist.set(nb.id(), (dist.get(id) || 0) + 1); next.push(nb.id()); }
        });
      }
      frontier = next;
    }
  }
  const maxD = dist.size ? Math.max(...dist.values()) : 0;
  cy.nodes().forEach((n) => { if (!dist.has(n.id())) dist.set(n.id(), maxD + 1); });

  const tiers = new Map<number, string[]>();
  cy.nodes().forEach((n) => {
    const d = dist.get(n.id()) ?? 0;
    if (!tiers.has(d)) tiers.set(d, []);
    tiers.get(d)!.push(n.id());
  });

  const X = 220, Y = 145;
  tiers.forEach((ids, d) => {
    ids.sort();
    const k = ids.length;
    ids.forEach((id, i) => cy.getElementById(id).position({ x: (i - (k - 1) / 2) * X, y: d * Y }));
  });
  cy.fit(undefined, 55);
}

export default function Graph() {
  const { stats, error: clusterErr } = useCluster();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [paths, setPaths] = useState<PathResponse[]>([]);
  const [rems, setRems] = useState<Remediation[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const [mode, setMode] = useState<Mode>("paths");
  const [showStructural, setShowStructural] = useState(true);
  const [highlight, setHighlight] = useState<Highlight>({ kind: "none" });

  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [searchParams] = useSearchParams();
  const appliedCut = useRef(false);

  useEffect(() => {
    if (!stats) return;
    let cancelled = false;
    (async () => {
      try {
        const [g, p, r] = await Promise.all([api.graph(), api.paths(), api.remediations(12)]);
        if (!cancelled) { setGraph(g); setPaths(p); setRems(r); }
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [stats]);

  useEffect(() => {
    if (!container.current || !graph) return;
    const cy = cytoscape({
      container: container.current, style: cyStylesheet,
      wheelSensitivity: 0.25, minZoom: 0.2, maxZoom: 3,
    });
    cy.on("tap", "node", (evt) => void onNodeTap(evt.target.id(), evt.target.data("label")));
    cy.on("tap", (evt) => { if (evt.target === cy) setHighlight({ kind: "none" }); });
    cyRef.current = cy;
    return () => { cy.destroy(); cyRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graph) return;
    const els = mode === "paths" ? pathElements(graph, paths) : fullElements(graph, showStructural);
    cy.elements().remove();
    cy.add(els);
    layered(cy);
    setHighlight({ kind: "none" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, mode, showStructural, paths]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded hl cut");
    if (highlight.kind === "none") return;
    if (highlight.kind === "path") {
      cy.elements().addClass("faded");
      highlight.nodes.forEach((n) => cy.getElementById(n).removeClass("faded").addClass("hl"));
      for (let i = 0; i < highlight.nodes.length - 1; i++)
        cy.getElementById(`${highlight.nodes[i]}->${highlight.nodes[i + 1]}`).removeClass("faded").addClass("hl");
    } else if (highlight.kind === "blast") {
      const keep = new Set([highlight.node, ...highlight.reachable]);
      cy.elements().addClass("faded");
      keep.forEach((n) => cy.getElementById(n).removeClass("faded"));
      cy.getElementById(highlight.node).addClass("hl");
      cy.edges().forEach((e) => { if (keep.has(e.source().id()) && keep.has(e.target().id())) e.removeClass("faded"); });
    } else if (highlight.kind === "cut") {
      cy.elements().addClass("faded");
      const e = cy.getElementById(highlight.edgeId);
      e.removeClass("faded").addClass("cut");
      e.source().removeClass("faded").addClass("hl");
      e.target().removeClass("faded").addClass("hl");
    }
  }, [highlight]);

  // If arrived from Remediations "Preview" (?cut=<edge_id>), highlight that fix once.
  useEffect(() => {
    if (!graph || appliedCut.current) return;
    const cut = searchParams.get("cut");
    if (cut && graph.edges.some((e) => e.data.id === cut)) {
      appliedCut.current = true;
      const label = rems.find((r) => r.edge_id === cut)?.description || cut;
      setHighlight({ kind: "cut", edgeId: cut, label });
    }
  }, [graph, rems, searchParams]);

  async function onNodeTap(id: string, label: string) {
    try {
      const b = await api.blastRadius(id);
      setHighlight({ kind: "blast", node: id, reachable: b.reachable, label });
    } catch { /* ignore */ }
  }
  function previewCut() {
    if (rems.length) setHighlight({ kind: "cut", edgeId: rems[0].edge_id, label: rems[0].description });
  }

  if (clusterErr) return <div className="page"><div className="err">{clusterErr}</div></div>;
  if (err) return <div className="page"><div className="err">{err}</div></div>;

  return (
    <div className="gv">
      <div className="canvas">
        <div className="gv-head">
          <span className="eyebrow">Live attack graph</span>
          <h2>Escalation map &rarr; cluster-admin</h2>
        </div>
        <div className="gv-controls">
          <div className="gv-seg">
            <button className={mode === "paths" ? "on" : ""} onClick={() => setMode("paths")}>Attack paths</button>
            <button className={mode === "full" ? "on" : ""} onClick={() => setMode("full")}>Full graph</button>
          </div>
          {mode === "full" && (
            <button className={`gv-ctl ${showStructural ? "on" : ""}`} onClick={() => setShowStructural((v) => !v)}>structural</button>
          )}
          <button className="gv-ctl" onClick={() => { setHighlight({ kind: "none" }); cyRef.current && layered(cyRef.current); }}>reset view</button>
        </div>
        {!graph && <div className="banner">Loading graph&hellip;</div>}
        <div ref={container} className="cy-canvas" />
        <div className="gv-legend">
          {LEGEND.map(([c, l]) => (<span className="lg" key={l}><span className="sw" style={{ background: c }} />{l}</span>))}
          <span className="lg"><span className="sw" style={{ background: "#33425f" }} />structural (dashed)</span>
        </div>
      </div>

      <aside className="side2">
        <div className="s2head">
          <span className="eyebrow">Trace attack paths</span>
          <h3>Footholds &rarr; cluster-admin</h3>
        </div>
        <div className="s2list">
          {paths.map((p) => (
            <button key={p.foothold}
                    className={`trace ${highlight.kind === "path" && highlight.label === p.foothold_label ? "on" : ""}`}
                    onClick={() => setHighlight({ kind: "path", nodes: p.nodes, label: p.foothold_label })}>
              <div className="t1">{p.foothold_label}</div>
              <div className="t2">{p.hops.map((h) => h.etype).join(" · ")}</div>
            </button>
          ))}
          {paths.length === 0 && <div className="s2note">No paths to cluster-admin.</div>}
        </div>
        {highlight.kind === "blast" && (
          <div className="s2note">Blast radius of <b>{highlight.label}</b>: reaches {highlight.reachable.length} entities.</div>
        )}
        {highlight.kind === "cut" && (<div className="s2note">Previewing fix: <b>{highlight.label}</b></div>)}
        <div className="s2foot">
          <button className="reset" onClick={() => setHighlight({ kind: "none" })}>Reset</button>
          <button className="cut" onClick={previewCut} disabled={!rems.length}>Preview #1 fix</button>
        </div>
      </aside>
    </div>
  );
}
