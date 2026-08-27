import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import type { GraphResponse } from "../api/client";
import { edgeCategory } from "../theme";
import { cyStylesheet } from "../cy/style";

export type Highlight =
  | { kind: "none" }
  | { kind: "path"; nodes: string[] }
  | { kind: "cut"; edgeId: string }
  | { kind: "blast"; node: string; reachable: string[] };

interface Props {
  graph: GraphResponse | null;
  layout: string;
  showStructural: boolean;
  highlight: Highlight;
  onNodeClick: (id: string) => void;
}

function toElements(graph: GraphResponse, showStructural: boolean): ElementDefinition[] {
  const nodes: ElementDefinition[] = graph.nodes.map((n) => ({ data: { ...n.data } }));
  const edges: ElementDefinition[] = graph.edges
    .map((e) => ({ data: { ...e.data, cat: edgeCategory(e.data.etype) } }))
    .filter((e) => showStructural || e.data.cat !== "struct");
  return [...nodes, ...edges];
}

const LAYOUTS: Record<string, cytoscape.LayoutOptions> = {
  breadthfirst: { name: "breadthfirst", directed: true, spacingFactor: 1.15, padding: 30 } as cytoscape.LayoutOptions,
  cose: { name: "cose", padding: 30, animate: false, } as cytoscape.LayoutOptions,
  concentric: { name: "concentric", padding: 30, minNodeSpacing: 30 } as cytoscape.LayoutOptions,
  circle: { name: "circle", padding: 30 } as cytoscape.LayoutOptions,
};

export default function GraphView({ graph, layout, showStructural, highlight, onNodeClick }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // init once
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      style: cyStylesheet,
      wheelSensitivity: 0.25,
      minZoom: 0.2,
      maxZoom: 3,
    });
    cy.on("tap", "node", (evt) => onNodeClick(evt.target.id()));
    cyRef.current = cy;
    return () => cy.destroy();
  }, [onNodeClick]);

  // load elements + run layout when data or toggles change
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !graph) return;
    cy.elements().remove();
    cy.add(toElements(graph, showStructural));
    cy.layout(LAYOUTS[layout] ?? LAYOUTS.breadthfirst).run();
    cy.fit(undefined, 40);
  }, [graph, layout, showStructural]);

  // apply highlight state
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded hl cut pick");
    if (highlight.kind === "none") return;

    if (highlight.kind === "path") {
      const ids = new Set(highlight.nodes);
      cy.elements().addClass("faded");
      highlight.nodes.forEach((n) => cy.getElementById(n).removeClass("faded").addClass("hl"));
      for (let i = 0; i < highlight.nodes.length - 1; i++) {
        const e = cy.getElementById(`${highlight.nodes[i]}->${highlight.nodes[i + 1]}`);
        e.removeClass("faded").addClass("hl");
      }
      // keep target visible even if not last (it is)
      void ids;
    } else if (highlight.kind === "cut") {
      cy.elements().addClass("faded");
      const e = cy.getElementById(highlight.edgeId);
      e.removeClass("faded").addClass("cut");
      e.source().removeClass("faded").addClass("hl");
      e.target().removeClass("faded").addClass("hl");
    } else if (highlight.kind === "blast") {
      const keep = new Set([highlight.node, ...highlight.reachable]);
      cy.elements().addClass("faded");
      keep.forEach((n) => cy.getElementById(n).removeClass("faded"));
      cy.getElementById(highlight.node).addClass("pick");
      cy.edges().forEach((e) => {
        if (keep.has(e.source().id()) && keep.has(e.target().id())) e.removeClass("faded");
      });
    }
  }, [highlight]);

  return <div ref={container} className="graph-canvas" />;
}
