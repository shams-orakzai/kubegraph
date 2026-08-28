// Dark cinematic Cytoscape theme for the attack-graph canvas.
// Stylesheet is typed loosely on purpose — cytoscape validates it at runtime.
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";

// Register the dagre layout once (hierarchical, low edge-crossing).
cytoscape.use(dagre);

const C = {
  target: "#FF5D73", pod: "#2DD4BF", sa: "#5B9DFF", role: "#F5B23D",
  secret: "#B98CFF", host: "#7C8AA5",
  eStruct: "#33425f", eGrant: "#5B9DFF", eCap: "#F5B23D", eAdmin: "#FF5D73",
  label: "#8095b5", bg: "#070B14",
};

const ADMIN = new Set([
  "IS_CLUSTER_ADMIN", "CAN_ESCALATE", "CAN_BIND", "CAN_UPDATE_RBAC",
  "CAN_APPROVE_CSR", "CAN_IMPERSONATE",
]);
const STRUCT = new Set(["USES_SA", "TOKEN_FOR"]);

export function edgeCategory(etype: string): "struct" | "grant" | "cap" | "admin" {
  if (STRUCT.has(etype)) return "struct";
  if (etype === "GRANTED_ROLE") return "grant";
  if (ADMIN.has(etype)) return "admin";
  return "cap";
}

export const cyStylesheet: any[] = [
  {
    selector: "node",
    style: {
      label: "data(label)", color: C.label, "font-family": "IBM Plex Mono, monospace",
      "font-size": 9, "text-valign": "bottom", "text-margin-y": 5, "text-wrap": "wrap",
      "text-max-width": "120px", width: 22, height: 22,
      "border-width": 1.5, "border-color": C.bg,
      "transition-property": "opacity, width, height, border-width", "transition-duration": "0.18s",
    },
  },
  { selector: 'node[ntype="Pod"]', style: { "background-color": C.pod, shape: "round-rectangle" } },
  { selector: 'node[ntype="ServiceAccount"]', style: { "background-color": C.sa, shape: "ellipse" } },
  { selector: 'node[ntype="Role"]', style: { "background-color": C.role, shape: "diamond" } },
  { selector: 'node[ntype="Secret"]', style: { "background-color": C.secret, shape: "hexagon" } },
  { selector: 'node[ntype="Node"]', style: { "background-color": C.host, shape: "octagon" } },
  {
    selector: 'node[ntype="Target"]',
    style: {
      "background-color": C.target, shape: "star", width: 50, height: 50,
      "font-size": 12, "font-family": "Space Grotesk, sans-serif", color: C.target,
      "text-valign": "top", "text-margin-y": -6,
      "border-width": 4, "border-color": C.target, "border-opacity": 0.3,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.4, "line-color": C.eStruct, "target-arrow-color": C.eStruct,
      "target-arrow-shape": "triangle", "arrow-scale": 0.85, "curve-style": "bezier",
      opacity: 0.7, "transition-property": "opacity, width, line-color", "transition-duration": "0.18s",
    },
  },
  { selector: 'edge[cat="struct"]', style: { "line-style": "dashed", "line-color": C.eStruct, "target-arrow-color": C.eStruct, opacity: 0.45 } },
  { selector: 'edge[cat="grant"]', style: { "line-color": C.eGrant, "target-arrow-color": C.eGrant, opacity: 0.9 } },
  { selector: 'edge[cat="cap"]', style: { "line-color": C.eCap, "target-arrow-color": C.eCap } },
  { selector: 'edge[cat="admin"]', style: { "line-color": C.eAdmin, "target-arrow-color": C.eAdmin, opacity: 0.9 } },

  { selector: ".faded", style: { opacity: 0.06, "text-opacity": 0.04 } },
  { selector: "node.hl", style: { "border-color": "#EAF0FA", "border-width": 2.5, width: 30, height: 30, "text-opacity": 1 } },
  { selector: "edge.hl", style: { width: 3.6, opacity: 1 } },
  {
    selector: "edge.cut",
    style: {
      width: 4, "line-color": C.target, "target-arrow-color": C.target,
      "line-style": "dashed", opacity: 1, "line-dash-pattern": [6, 3],
    },
  },
];

// Dagre gives a clean layered hierarchy; footholds at the bottom (rankDir BT)
// flowing up to the crown jewel — matching the design prototype.
export const LAYOUTS: Record<string, any> = {
  dagre: { name: "dagre", rankDir: "BT", nodeSep: 55, rankSep: 75, edgeSep: 20, padding: 40, animate: false },
  breadthfirst: { name: "breadthfirst", directed: true, spacingFactor: 1.1, padding: 36 },
  cose: { name: "cose", padding: 36, animate: false },
  concentric: { name: "concentric", padding: 36, minNodeSpacing: 34 },
};
