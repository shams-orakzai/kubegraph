"""Remediation ranking — the core contribution.

Two rankings over *removable* edges:

1. EXACT impact (the gold reference, ~ KubeHound's approach): for each removable
   edge, remove it and recompute how many footholds / paths to the target are
   eliminated. Correct but O(|E_removable| x reachability) — the cost that
   motivates an approximation.

2. CENTRALITY approximation: source->target edge-betweenness (how many shortest
   attacker->target paths traverse each edge). Cheap; one pass. Phase 3's
   evaluation will measure how faithfully this reproduces the exact ranking and
   whether it beats a severity baseline on paths-eliminated-per-fix.

NOTE (next analytical refinement): the truly correct unit of "a single fix" is
an RBAC *object* (one Role rule / one binding), which can map to many graph
edges at once. Ranking is edge-level here; object-level grouping via edge
provenance is the planned enhancement.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from kubegraph.graph import paths as pathmod
from kubegraph.models.graph import TARGET_CLUSTER_ADMIN, EdgeType


@dataclass
class Remediation:
    edge_id: str
    source: str
    target_node: str
    etype: str
    footholds_cut: int
    paths_cut: int
    centrality: float
    description: str


def _reachable(g: nx.DiGraph, target: str) -> set[str]:
    return set(pathmod.reachable_footholds(g, target).keys())


def _total_paths(g: nx.DiGraph, target: str, cutoff: int) -> int:
    return sum(len(pathmod.all_attack_paths(g, fh, target, cutoff))
               for fh in pathmod.footholds(g))


def _describe(g: nx.DiGraph, u: str, v: str, etype: str) -> str:
    lu = g.nodes[u].get("label", u)
    lv = g.nodes[v].get("label", v)
    match etype:
        case EdgeType.GRANTED_ROLE:
            return f"Unbind {lu} from {lv}"
        case EdgeType.IS_CLUSTER_ADMIN:
            return f"Remove cluster-admin (wildcard */*) from {lu}"
        case EdgeType.CAN_CREATE_POD:
            return f"Revoke pod/workload create from {lu} (blocks mounting {lv})"
        case EdgeType.CAN_EXEC:
            return f"Revoke pods/exec from {lu} (blocks entering {lv})"
        case EdgeType.CAN_GET_SECRET:
            return f"Revoke get/list secrets from {lu} (blocks reading {lv})"
        case EdgeType.CAN_CREATE_TOKEN:
            return f"Revoke serviceaccounts/token from {lu} (blocks minting {lv})"
        case EdgeType.CAN_IMPERSONATE:
            return f"Revoke impersonate from {lu}"
        case EdgeType.CAN_ESCALATE:
            return f"Revoke escalate on roles from {lu}"
        case EdgeType.CAN_BIND:
            return f"Revoke bind on roles from {lu}"
        case EdgeType.CAN_UPDATE_RBAC:
            return f"Revoke write access to RBAC bindings from {lu}"
        case EdgeType.CAN_APPROVE_CSR:
            return f"Revoke CSR approval from {lu}"
        case _:
            return f"Remove {etype}: {lu} -> {lv}"


def subset_edge_betweenness(
    g: nx.DiGraph, target: str = TARGET_CLUSTER_ADMIN
) -> dict[tuple[str, str], float]:
    """Attack-path-aware edge betweenness: fraction of foothold->target shortest
    paths through each edge. The fast choke-point approximation."""
    sources = pathmod.footholds(g)
    if not sources or not g.has_node(target):
        return {}
    return nx.edge_betweenness_centrality_subset(
        g, sources=sources, targets=[target], normalized=False)


def rank_remediations(
    g: nx.DiGraph,
    target: str = TARGET_CLUSTER_ADMIN,
    cutoff: int = 6,
    top: int | None = None,
) -> list[Remediation]:
    """Exact impact ranking (with centrality attached for comparison)."""
    base_reach = _reachable(g, target)
    base_paths = _total_paths(g, target, cutoff)
    cent = subset_edge_betweenness(g, target)

    out: list[Remediation] = []
    for u, v, d in g.edges(data=True):
        if not d.get("removable"):
            continue
        h = g.copy()
        h.remove_edge(u, v)
        fc = len(base_reach) - len(_reachable(h, target))
        pc = base_paths - _total_paths(h, target, cutoff)
        if fc == 0 and pc == 0:
            continue  # a fix that changes nothing is not a remediation
        etype = str(d["etype"])
        out.append(Remediation(
            edge_id=f"{u}->{v}", source=u, target_node=v, etype=etype,
            footholds_cut=fc, paths_cut=pc,
            centrality=round(cent.get((u, v), 0.0), 4),
            description=_describe(g, u, v, etype),
        ))
    out.sort(key=lambda r: (r.footholds_cut, r.paths_cut, r.centrality),
             reverse=True)
    return out[:top] if top else out


def blast_radius(g: nx.DiGraph, node: str) -> list[str]:
    """Everything an attacker at ``node`` can eventually reach."""
    if not g.has_node(node):
        return []
    return sorted(nx.descendants(g, node))
