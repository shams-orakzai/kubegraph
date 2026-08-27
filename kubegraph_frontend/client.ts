// Typed client for the KubeGraph backend. Types mirror api/schemas.py.

const BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

export interface Stats {
  cluster_name: string;
  nodes: number;
  edges: number;
  removable_edges: number;
  footholds: number;
  footholds_reaching_target: number;
}

export interface CyElement<T> {
  data: T;
}
export interface CyNodeData {
  id: string;
  label: string;
  ntype: string;
  namespace: string | null;
}
export interface CyEdgeData {
  id: string;
  source: string;
  target: string;
  etype: string;
  removable: boolean;
}
export interface GraphResponse {
  nodes: CyElement<CyNodeData>[];
  edges: CyElement<CyEdgeData>[];
}

export interface Hop {
  from_label: string;
  etype: string;
  to_label: string;
}
export interface PathResponse {
  foothold: string;
  foothold_label: string;
  length: number;
  hops: Hop[];
  nodes: string[];
}

export interface Remediation {
  rank: number;
  edge_id: string;
  etype: string;
  footholds_cut: number;
  paths_cut: number;
  centrality: number;
  description: string;
}

export interface BlastRadius {
  node: string;
  reachable_count: number;
  reachable: string[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json() as Promise<T>;
}
async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  loadDemo: () => post<{ snapshot_id: string; stats: Stats }>("/demo"),
  stats: () => get<Stats>("/stats"),
  graph: () => get<GraphResponse>("/graph"),
  paths: () => get<PathResponse[]>("/paths"),
  remediations: (top = 10) => get<Remediation[]>(`/remediations?top=${top}`),
  blastRadius: (node: string) =>
    get<BlastRadius>(`/blast-radius?node=${encodeURIComponent(node)}`),
};
