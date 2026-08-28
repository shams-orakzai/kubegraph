import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { api } from "../api/client";
import type { GraphResponse, PathResponse, Remediation } from "../api/types";
import { useCluster } from "../cluster/ClusterContext";
import { cyStylesheet, edgeCategory, LAYOUTS } from "../graph/cyStyle";

type Highlight =
  | { kind: "none" }
  | { kind: "path"; nodes: string[]; label: string }
  | { kind: "blast"; node: string; reachable: string[]; label: string }
  | { kind: "cut"; edgeId: string; label: string };

const LEGEND = [
  ["#FF5D73", "target"], ["#2DD4BF", "pod"], ["#5B9DFF", "service account"],
  ["#F5B23D", "role"], ["#B98CFF", "secret"],
] as const;

function toElements(graph: GraphResponse, showStructural: boolean): ElementDefinition[] {
  const nodes = graph.nodes.map((n) => ({ data: { ...n.data } }));
  const edges = graph.edges
    .map((e) => ({ data: { ...e.data, cat: edgeCategory(e.data.etype) } }))
    .filter((e) => showStructural || e.data.cat !== "struct");
  return [...nodes, ...edges];
}

export default function Graph() {
  const { stats, error: clusterErr } = useCluster();
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [paths, setPaths] = useState<PathResponse[]>([]);
  const [rems, setRems] = useState<Remediation[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const [layout, setLayout] = useState("breadthfirst");
  const [showStructural, setShowStructural] = useState(true);
  const [highlight, setHighlight] = useState<Highlight>({ kind: "none" });

  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

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
    cy.elements().remove();
    cy.add(toElements(graph, showStructural));
    cy.layout(LAYOUTS[layout] ?? LAYOUTS.breadthfirst).run();
    cy.fit(undefined, 40);
    setHighlight({ kind: "none" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, layout, showStructural]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded hl cut");
    if (highlight.kind === "none") return;

    if (highlight.kind === "path") {
      cy.elements().addClass("faded");
      highlight.nodes.forEach((n) => cy.getElementById(n).removeClass("faded").addClass("hl"));
      for (let i = 0; i < highlight.nodes.length - 1; i++) {
        cy.getElementById(`${highlight.nodes[i]}->${highlight.nodes[i + 1]}`).removeClass("faded").addClass("hl");
      }
    } else if (highlight.kind === "blast") {
      const keep = new Set([highlight.node, ...highlight.reachable]);
      cy.elements().addClass("faded");
      keep.forEach((n) => cy.getElementById(n).removeClass("faded"));
      cy.getElementById(highlight.node).addClass("hl");
      cy.edges().forEach((e) => {
        if (keep.has(e.source().id()) && keep.has(e.target().id())) e.removeClass("faded");
      });
    } else if (highlight.kind === "cut") {
      cy.elements().addClass("faded");
      const e = cy.getElementById(highlight.edgeId);
      e.removeClass("faded").addClass("cut");
      e.source().removeClass("faded").addClass("hl");
      e.target().removeClass("faded").addClass("hl");
    }
  }, [highlight]);

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
          <select className="gv-ctl" value={layout} onChange={(e) => setLayout(e.target.value)} aria-label="Layout">
            {Object.keys(LAYOUTS).map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <button className={`gv-ctl ${showStructural ? "on" : ""}`} onClick={() => setShowStructural((v) => !v)}>structural</button>
          <button className="gv-ctl" onClick={() => { setHighlight({ kind: "none" }); cyRef.current?.fit(undefined, 40); }}>reset view</button>
        </div>
        {!graph && <div className="banner">Loading graph&hellip;</div>}
        <div ref={container} className="cy-canvas" />
        <div className="gv-legend">
          {LEGEND.map(([c, l]) => (
            <span className="lg" key={l}><span className="sw" style={{ background: c }} />{l}</span>
          ))}
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
        {highlight.kind === "cut" && (
          <div className="s2note">Previewing fix: <b>{highlight.label}</b></div>
        )}
        <div className="s2foot">
          <button className="reset" onClick={() => setHighlight({ kind: "none" })}>Reset</button>
          <button className="cut" onClick={previewCut} disabled={!rems.length}>Preview #1 fix</button>
        </div>
      </aside>
    </div>
  );
}
