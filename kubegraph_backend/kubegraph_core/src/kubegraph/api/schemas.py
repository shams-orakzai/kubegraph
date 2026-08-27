"""API response schemas — the stable contract the React frontend consumes."""

from __future__ import annotations

from pydantic import BaseModel


class Stats(BaseModel):
    cluster_name: str
    nodes: int
    edges: int
    removable_edges: int
    footholds: int
    footholds_reaching_target: int


class CyNodeData(BaseModel):
    id: str
    label: str
    ntype: str
    namespace: str | None = None


class CyEdgeData(BaseModel):
    id: str
    source: str
    target: str
    etype: str
    removable: bool


class CyNode(BaseModel):
    data: CyNodeData


class CyEdge(BaseModel):
    data: CyEdgeData


class GraphResponse(BaseModel):
    """Cytoscape.js-ready elements."""
    nodes: list[CyNode]
    edges: list[CyEdge]


class Hop(BaseModel):
    from_label: str
    etype: str
    to_label: str


class PathResponse(BaseModel):
    foothold: str
    foothold_label: str
    length: int
    hops: list[Hop]
    nodes: list[str]  # node ids, for frontend highlighting


class RemediationResponse(BaseModel):
    rank: int
    edge_id: str
    etype: str
    footholds_cut: int
    paths_cut: int
    centrality: float
    description: str


class BlastRadiusResponse(BaseModel):
    node: str
    reachable_count: int
    reachable: list[str]


class SnapshotSummary(BaseModel):
    snapshot_id: str
    cluster_name: str
    current: bool


class LoadResponse(BaseModel):
    snapshot_id: str
    stats: Stats
