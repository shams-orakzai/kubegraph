"""In-memory snapshot store.

Holds inventory + built graph per snapshot, with a notion of the "current"
snapshot the frontend operates on by default. This is intentionally a thin
in-memory layer for the API increment; the SQLAlchemy/PostgreSQL persistence
layer (proposal's graph store) is the next backend step and will implement the
same interface.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import networkx as nx

from kubegraph.graph.builder import build_graph
from kubegraph.models.inventory import Inventory


@dataclass
class Snapshot:
    snapshot_id: str
    inventory: Inventory
    graph: nx.DiGraph


class SnapshotStore:
    def __init__(self) -> None:
        self._snaps: dict[str, Snapshot] = {}
        self._current: str | None = None

    def add(self, inv: Inventory) -> Snapshot:
        sid = uuid.uuid4().hex[:12]
        snap = Snapshot(snapshot_id=sid, inventory=inv, graph=build_graph(inv))
        self._snaps[sid] = snap
        self._current = sid
        return snap

    def get(self, snapshot_id: str | None = None) -> Snapshot | None:
        sid = snapshot_id or self._current
        return self._snaps.get(sid) if sid else None

    def list(self) -> list[Snapshot]:
        return list(self._snaps.values())

    @property
    def current_id(self) -> str | None:
        return self._current


store = SnapshotStore()
