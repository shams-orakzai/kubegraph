"""Serialize the in-memory graph into API response shapes."""

from __future__ import annotations

import networkx as nx

from kubegraph.api.schemas import (
    CyEdge, CyEdgeData, CyNode, CyNodeData, GraphResponse, Hop, PathResponse,
)
from kubegraph.graph import paths as pathmod


def to_cytoscape(g: nx.DiGraph) -> GraphResponse:
    nodes = [
        CyNode(data=CyNodeData(
            id=n,
            label=d.get("label", n),
            ntype=str(d.get("ntype", "")),
            namespace=d.get("namespace"),
        ))
        for n, d in g.nodes(data=True)
    ]
    edges = [
        CyEdge(data=CyEdgeData(
            id=f"{u}->{v}", source=u, target=v,
            etype=str(d.get("etype", "")), removable=bool(d.get("removable")),
        ))
        for u, v, d in g.edges(data=True)
    ]
    return GraphResponse(nodes=nodes, edges=edges)


def path_to_response(g: nx.DiGraph, foothold: str, path) -> PathResponse:
    hops = [
        Hop(
            from_label=g.nodes[path.nodes[i]].get("label", path.nodes[i]),
            etype=path.edges[i],
            to_label=g.nodes[path.nodes[i + 1]].get("label", path.nodes[i + 1]),
        )
        for i in range(len(path.edges))
    ]
    return PathResponse(
        foothold=foothold,
        foothold_label=g.nodes[foothold].get("label", foothold),
        length=path.length, hops=hops, nodes=path.nodes,
    )


def shortest_paths_response(g: nx.DiGraph) -> list[PathResponse]:
    reach = pathmod.reachable_footholds(g)
    ordered = sorted(reach.items(), key=lambda kv: kv[1].length)
    return [path_to_response(g, fh, p) for fh, p in ordered]
