"""KubeGraph backend API.

Endpoints (all operate on the current snapshot unless ?snapshot=<id> given):

    POST /inventory        load an Inventory JSON body -> becomes current
    POST /demo             load the bundled synthetic vulnerable cluster
    GET  /snapshots        list loaded snapshots
    GET  /stats            summary counts
    GET  /graph            Cytoscape.js elements (nodes + edges)
    GET  /paths            shortest attack path per reachable foothold
    GET  /paths/detail     all bounded simple paths from one foothold
    GET  /remediations     ranked choke-point fixes (the headline feature)
    GET  /blast-radius     everything reachable from a node

Run:  uvicorn kubegraph.api.app:app --reload
"""

from __future__ import annotations

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from kubegraph import __version__
from kubegraph.analysis import chokepoint
from kubegraph.api import serialize
from kubegraph.api.schemas import (
    BlastRadiusResponse, GraphResponse, LoadResponse, PathResponse,
    RemediationResponse, SnapshotSummary, Stats,
)
from kubegraph.api.store import store
from kubegraph.graph import paths as pathmod
from kubegraph.models.graph import TARGET_CLUSTER_ADMIN
from kubegraph.models.inventory import Inventory

app = FastAPI(title="KubeGraph API", version=__version__)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _snap(snapshot: str | None):
    snap = store.get(snapshot)
    if snap is None:
        raise HTTPException(404, "No snapshot loaded. POST /inventory or /demo first.")
    return snap


def _stats(snap) -> Stats:
    g = snap.graph
    removable = sum(1 for *_, d in g.edges(data=True) if d.get("removable"))
    fh = pathmod.footholds(g)
    reaching = len(pathmod.reachable_footholds(g))
    return Stats(
        cluster_name=snap.inventory.cluster_name,
        nodes=g.number_of_nodes(), edges=g.number_of_edges(),
        removable_edges=removable, footholds=len(fh),
        footholds_reaching_target=reaching,
    )


@app.get("/")
def root() -> dict:
    return {"name": "KubeGraph API", "version": __version__,
            "current_snapshot": store.current_id,
            "snapshots": len(store.list())}


@app.post("/inventory", response_model=LoadResponse)
def load_inventory(inv: Inventory = Body(...)) -> LoadResponse:
    snap = store.add(inv)
    return LoadResponse(snapshot_id=snap.snapshot_id, stats=_stats(snap))


@app.post("/demo", response_model=LoadResponse)
def load_demo() -> LoadResponse:
    import importlib.util
    from pathlib import Path
    fx = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "build_fixture.py"
    if not fx.exists():
        raise HTTPException(404, "Demo fixture not found.")
    spec = importlib.util.spec_from_file_location("build_fixture", fx)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    snap = store.add(mod.build())
    return LoadResponse(snapshot_id=snap.snapshot_id, stats=_stats(snap))


@app.get("/snapshots", response_model=list[SnapshotSummary])
def list_snapshots() -> list[SnapshotSummary]:
    return [SnapshotSummary(snapshot_id=s.snapshot_id,
                            cluster_name=s.inventory.cluster_name,
                            current=s.snapshot_id == store.current_id)
            for s in store.list()]


@app.get("/stats", response_model=Stats)
def stats(snapshot: str | None = Query(None)) -> Stats:
    return _stats(_snap(snapshot))


@app.get("/graph", response_model=GraphResponse)
def graph(snapshot: str | None = Query(None)) -> GraphResponse:
    return serialize.to_cytoscape(_snap(snapshot).graph)


@app.get("/paths", response_model=list[PathResponse])
def paths(snapshot: str | None = Query(None)) -> list[PathResponse]:
    return serialize.shortest_paths_response(_snap(snapshot).graph)


@app.get("/paths/detail", response_model=list[PathResponse])
def paths_detail(
    foothold: str = Query(..., description="node id, e.g. pod:default/web-frontend"),
    cutoff: int = Query(8, ge=1, le=12),
    snapshot: str | None = Query(None),
) -> list[PathResponse]:
    g = _snap(snapshot).graph
    if not g.has_node(foothold):
        raise HTTPException(404, f"Unknown foothold: {foothold}")
    ap = pathmod.all_attack_paths(g, foothold, TARGET_CLUSTER_ADMIN, cutoff=cutoff)
    return [serialize.path_to_response(g, foothold, p) for p in ap]


@app.get("/remediations", response_model=list[RemediationResponse])
def remediations(
    top: int = Query(10, ge=1, le=100),
    cutoff: int = Query(6, ge=1, le=10),
    snapshot: str | None = Query(None),
) -> list[RemediationResponse]:
    g = _snap(snapshot).graph
    ranked = chokepoint.rank_remediations(g, cutoff=cutoff, top=top)
    return [RemediationResponse(
        rank=i + 1, edge_id=r.edge_id, etype=r.etype,
        footholds_cut=r.footholds_cut, paths_cut=r.paths_cut,
        centrality=r.centrality, description=r.description,
    ) for i, r in enumerate(ranked)]


@app.get("/blast-radius", response_model=BlastRadiusResponse)
def blast_radius(
    node: str = Query(..., description="node id to compute blast radius from"),
    snapshot: str | None = Query(None),
) -> BlastRadiusResponse:
    g = _snap(snapshot).graph
    if not g.has_node(node):
        raise HTTPException(404, f"Unknown node: {node}")
    reach = chokepoint.blast_radius(g, node)
    return BlastRadiusResponse(node=node, reachable_count=len(reach), reachable=reach)
