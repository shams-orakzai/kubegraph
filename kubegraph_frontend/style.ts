// stylesheet is validated by cytoscape at runtime; typed loosely on purpose
import { COLORS } from "../theme";

// The visual grammar: node fill = entity type, edge colour = escalation
// category, dashed = structural. `.faded` recedes, `.hl` illuminates, `.cut`
// marks a remediation about to sever a route.
export const cyStylesheet: any[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      color: COLORS.text,
      "font-family": "IBM Plex Mono, monospace",
      "font-size": 9,
      "text-valign": "bottom",
      "text-margin-y": 4,
      "text-wrap": "wrap",
      "text-max-width": "120px",
      width: 22,
      height: 22,
      "border-width": 1.5,
      "border-color": COLORS.bg,
      "transition-property": "opacity, width, height, border-color",
      "transition-duration": "0.18s",
    },
  },
  { selector: 'node[ntype="Pod"]', style: { "background-color": COLORS.pod, shape: "round-rectangle" } },
  { selector: 'node[ntype="ServiceAccount"]', style: { "background-color": COLORS.sa, shape: "ellipse" } },
  { selector: 'node[ntype="Role"]', style: { "background-color": COLORS.role, shape: "diamond" } },
  { selector: 'node[ntype="Secret"]', style: { "background-color": COLORS.secret, shape: "hexagon" } },
  { selector: 'node[ntype="Node"]', style: { "background-color": COLORS.host, shape: "octagon" } },
  {
    selector: 'node[ntype="Target"]',
    style: {
      "background-color": COLORS.target,
      shape: "star",
      width: 46,
      height: 46,
      "font-size": 12,
      "font-family": "Space Grotesk, sans-serif",
      color: COLORS.target,
      "text-valign": "top",
      "text-margin-y": -6,
      "border-width": 3,
      "border-color": COLORS.target,
      "border-opacity": 0.35,
    },
  },

  {
    selector: "edge",
    style: {
      width: 1.4,
      "line-color": COLORS.edgeStruct,
      "target-arrow-color": COLORS.edgeStruct,
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
      "curve-style": "bezier",
      opacity: 0.75,
      "transition-property": "opacity, width, line-color",
      "transition-duration": "0.18s",
    },
  },
  { selector: 'edge[cat="struct"]', style: { "line-style": "dashed", "line-color": COLORS.edgeStruct, "target-arrow-color": COLORS.edgeStruct } },
  { selector: 'edge[cat="grant"]', style: { "line-color": COLORS.edgeGrant, "target-arrow-color": COLORS.edgeGrant } },
  { selector: 'edge[cat="cap"]', style: { "line-color": COLORS.edgeCap, "target-arrow-color": COLORS.edgeCap } },
  { selector: 'edge[cat="admin"]', style: { "line-color": COLORS.edgeAdmin, "target-arrow-color": COLORS.edgeAdmin } },

  // interaction states
  { selector: ".faded", style: { opacity: 0.08, "text-opacity": 0.05 } },
  {
    selector: "node.hl",
    style: { "border-color": COLORS.text, "border-width": 2.5, width: 30, height: 30, "text-opacity": 1 },
  },
  { selector: "edge.hl", style: { width: 3.5, opacity: 1 } },
  {
    selector: "edge.cut",
    style: {
      width: 4,
      "line-color": COLORS.target,
      "target-arrow-color": COLORS.target,
      "line-style": "dashed",
      opacity: 1,
      "line-dash-pattern": [6, 3],
    },
  },
  { selector: "node.pick", style: { "border-color": COLORS.text, "border-width": 3 } },
];
