// Types mirroring the backend response schemas.

export interface User {
  id: number;
  name: string;
  email: string;
  org: string;
  role: "engineer" | "platform" | "ciso";
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Stats {
  cluster_name: string;
  nodes: number;
  edges: number;
  removable_edges: number;
  footholds: number;
  footholds_reaching_target: number;
  exposure_score: number;
  exposure_band: "Low" | "Medium" | "High";
  paths: number;
  choke_points: number;
}

export interface FleetItem {
  snapshot_id: string;
  cluster_name: string;
  exposure_score: number;
  exposure_band: "Low" | "Medium" | "High";
  footholds: number;
  footholds_reaching_target: number;
  paths: number;
  choke_points: number;
  current: boolean;
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

export interface Hop { from_label: string; etype: string; to_label: string; }
export interface PathResponse {
  foothold: string;
  foothold_label: string;
  length: number;
  hops: Hop[];
  nodes: string[];
}

export interface GraphResponse {
  nodes: { data: { id: string; label: string; ntype: string; namespace: string | null } }[];
  edges: { data: { id: string; source: string; target: string; etype: string; removable: boolean } }[];
}

export interface BlastRadius {
  node: string;
  reachable_count: number;
  reachable: string[];
}

export interface BlastRadius {
  node: string;
  reachable_count: number;
  reachable: string[];
}
