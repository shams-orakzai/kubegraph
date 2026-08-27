"""Attack-path queries over the built graph.

Phase 2 scope: reachability and path enumeration (shortest + bounded all-paths)
from attacker footholds (pods) to high-value targets. The choke-point /
centrality remediation ranking arrives in Phase 3 and builds directly on these
primitives.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from kubegraph.models.graph import TARGET_CLUSTER_ADMIN, NodeType


@dataclass
class AttackPath:
    nodes: list[str]
    edges: list[str]  # EdgeType value per hop

    @property
    def length(self) -> int:
        return len(self.edges)


def footholds(g: nx.DiGraph) -> list[str]:
    """Every pod is a plausible initial foothold."""
    return [n for n, d in g.nodes(data=True) if d.get("ntype") == NodeType.POD]


def _path_edges(g: nx.DiGraph, nodes: list[str]) -> list[str]:
    return [str(g.edges[nodes[i], nodes[i + 1]]["etype"])
            for i in range(len(nodes) - 1)]


def shortest_attack_path(
    g: nx.DiGraph, source: str, target: str = TARGET_CLUSTER_ADMIN
) -> AttackPath | None:
    if not (g.has_node(source) and g.has_node(target)):
        return None
    try:
        nodes = nx.shortest_path(g, source, target)
    except nx.NetworkXNoPath:
        return None
    return AttackPath(nodes=nodes, edges=_path_edges(g, nodes))


def all_attack_paths(
    g: nx.DiGraph,
    source: str,
    target: str = TARGET_CLUSTER_ADMIN,
    cutoff: int = 8,
) -> list[AttackPath]:
    """Bounded enumeration of simple paths (the brute-force reference).

    ``cutoff`` bounds path length to keep this tractable; the scalability
    evaluation (Phase 3) contrasts this against centrality-based ranking.
    """
    if not (g.has_node(source) and g.has_node(target)):
        return []
    out = []
    for nodes in nx.all_simple_paths(g, source, target, cutoff=cutoff):
        out.append(AttackPath(nodes=nodes, edges=_path_edges(g, nodes)))
    return out


def reachable_footholds(
    g: nx.DiGraph, target: str = TARGET_CLUSTER_ADMIN
) -> dict[str, AttackPath]:
    """Foothold -> its shortest attack path, for footholds that can reach target."""
    result: dict[str, AttackPath] = {}
    for fh in footholds(g):
        path = shortest_attack_path(g, fh, target)
        if path is not None:
            result[fh] = path
    return result


def render_path(g: nx.DiGraph, path: AttackPath) -> str:
    """Human-readable 'node -[EDGE]-> node' rendering using node labels."""
    parts: list[str] = []
    for i, node in enumerate(path.nodes):
        label = g.nodes[node].get("label", node)
        parts.append(label)
        if i < len(path.edges):
            parts.append(f" ─[{path.edges[i]}]→ ")
    return "".join(parts)
