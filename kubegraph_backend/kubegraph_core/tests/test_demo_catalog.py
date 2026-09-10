"""Tests for the selectable synthetic-cluster catalog and cluster switching.

Kept in a separate module so it is collected after test_api.py (alphabetical
order): the API snapshot store is a process-global singleton, and these tests
load higher-exposure clusters that would otherwise perturb test_api's fleet
ordering assertion.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Configure a throwaway DB before importing the app (no-op if already imported).
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(tempfile.mkdtemp(), 'catalog.db')}")
os.environ.setdefault("KUBEGRAPH_SECRET_KEY", "catalog-test-secret")

from fastapi.testclient import TestClient  # noqa: E402
from kubegraph.api.app import app  # noqa: E402
from kubegraph.db import init_db  # noqa: E402
from kubegraph.demo import catalog as democatalog  # noqa: E402

init_db()


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/auth/register", json={
        "name": "Cat Tester", "email": "catalog@example.com",
        "password": "supersecret", "org": "Lab", "role": "engineer",
    })
    tok = c.post("/auth/login", json={
        "email": "catalog@example.com", "password": "supersecret",
    }).json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {tok}"})
    return c


def test_catalog_lists_grouped_clusters(client):
    cat = client.get("/demo/catalog").json()
    assert len(cat) == len(democatalog.CATALOG) >= 10
    groups = {c["group"] for c in cat}
    assert {"Featured", "Evaluation corpus"} <= groups
    ids = {c["id"] for c in cat}
    assert {"synthetic-vulnerable", "hardened-baseline", "impersonation-abuse",
            "c1-single-admin", "c5-deep-chain"} <= ids
    # every catalog entry exposes a distinct cluster_name
    names = [c["cluster_name"] for c in cat]
    assert len(names) == len(set(names))


def test_specific_clusters_give_different_results(client):
    imp = client.post("/demo/impersonation-abuse").json()["stats"]
    hard = client.post("/demo/hardened-baseline").json()["stats"]
    assert imp["cluster_name"] == "impersonation-abuse"
    assert hard["cluster_name"] == "hardened-baseline"
    # the hardened cluster has no viable path; the impersonation one is exposed
    assert hard["footholds_reaching_target"] == 0 and hard["exposure_score"] == 0
    assert imp["footholds_reaching_target"] > 0 and imp["exposure_score"] > 0
    # naturally different graphs
    assert imp["nodes"] != hard["nodes"] or imp["edges"] != hard["edges"]


def test_load_is_idempotent(client):
    client.post("/demo/c4-redundant-mesh")
    client.post("/demo/c4-redundant-mesh")
    names = [s["cluster_name"] for s in client.get("/snapshots").json()]
    assert names.count("C4-redundant-mesh") == 1


def test_select_snapshot_switches_current(client):
    client.post("/demo/secret-sprawl")
    client.post("/demo/c1-single-admin")
    snaps = client.get("/snapshots").json()
    target = next(s for s in snaps if not s["current"])
    r = client.post(f"/snapshots/{target['snapshot_id']}/select")
    assert r.status_code == 200
    assert r.json()["stats"]["cluster_name"] == target["cluster_name"]
    assert client.get("/stats").json()["cluster_name"] == target["cluster_name"]
    # catalog reflects the current flag
    cat = client.get("/demo/catalog").json()
    current = [c for c in cat if c["current"]]
    assert len(current) <= 1


def test_unknown_ids_return_404(client):
    assert client.post("/demo/nope").status_code == 404
    assert client.post("/snapshots/deadbeef/select").status_code == 404
