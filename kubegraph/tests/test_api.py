"""API tests using FastAPI's TestClient against the demo cluster."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from kubegraph.api.app import app


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/demo")  # load synthetic vulnerable cluster as current snapshot
    return c


def test_stats(client):
    s = client.get("/stats").json()
    assert s["footholds"] == 4
    assert s["footholds_reaching_target"] == 4


def test_graph_shape(client):
    g = client.get("/graph").json()
    assert g["nodes"] and g["edges"]
    assert all("data" in n for n in g["nodes"])
    assert any(e["data"]["etype"] == "CAN_CREATE_POD" for e in g["edges"])


def test_paths(client):
    paths = client.get("/paths").json()
    assert len(paths) == 4
    assert all(p["hops"] for p in paths)


def test_top_remediation_cuts_all_footholds(client):
    rem = client.get("/remediations?top=5").json()
    assert rem, "expected at least one remediation"
    # The #1 fix must eliminate every foothold's path (the choke point).
    assert rem[0]["footholds_cut"] == 4


def test_blast_radius(client):
    r = client.get("/blast-radius?node=sa:kube-system/deployer").json()
    assert r["reachable_count"] >= 1


def test_no_snapshot_404():
    # Fresh client with an empty store path -> 404 guidance.
    from kubegraph.api.store import SnapshotStore
    import kubegraph.api.app as appmod
    original = appmod.store
    appmod.store = SnapshotStore()
    try:
        c = TestClient(app)
        assert c.get("/stats").status_code == 404
    finally:
        appmod.store = original
