// Single source of truth for the palette. Colour carries meaning here:
// node hue == entity type, edge hue == escalation category.

export const COLORS = {
  bg: "#0C111B",
  panel: "#141C2B",
  panelAlt: "#1B2536",
  line: "#25304A",
  text: "#E6ECF5",
  textDim: "#8A99B5",

  // entity types
  target: "#FF5D73", // cluster-admin — the crown jewel
  pod: "#2DD4BF", // foothold
  sa: "#5B9DFF", // service account / identity
  role: "#F5B23D", // role / clusterrole
  secret: "#B98CFF", // secret
  host: "#7C8AA5", // node / host

  // edge categories
  edgeStruct: "#3A4763", // structural (dashed, not remediable)
  edgeGrant: "#5B9DFF", // GRANTED_ROLE
  edgeCap: "#F5B23D", // capability hop (create-pod, exec, get-secret, ...)
  edgeAdmin: "#FF5D73", // direct-to-admin power (escalate, bind, impersonate, ...)
} as const;

export const NODE_TYPE_LABELS: Record<string, { color: string; label: string }> = {
  Target: { color: COLORS.target, label: "cluster-admin target" },
  Pod: { color: COLORS.pod, label: "Pod (foothold)" },
  ServiceAccount: { color: COLORS.sa, label: "ServiceAccount" },
  Role: { color: COLORS.role, label: "Role / ClusterRole" },
  Secret: { color: COLORS.secret, label: "Secret" },
  Node: { color: COLORS.host, label: "Node (host)" },
};

// Map an edge type to its category colour.
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
