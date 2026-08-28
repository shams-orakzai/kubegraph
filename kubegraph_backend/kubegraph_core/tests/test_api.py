"""API tests using FastAPI's TestClient against the demo cluster.

Routes are now auth-protected, so the client fixture registers a user, logs in,
and attaches the Bearer token. An isolated on-disk SQLite file (per test session)
keeps this from touching any real database.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Point the app at a throwaway database BEFORE importing it.
_TMPDB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDB}"
os.environ["KUBEGRAPH_SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from kubegraph.api.app import app  # noqa: E402
from kubegraph.db import init_db  # noqa: E402

init_db()


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/auth/register", json={
        "name": "Test User", "email": "test@example.com",
        "password": "supersecret", "org": "Lab", "role": "engineer",
    })
    tok = c.post("/auth/login", json={
        "email": "test@example.com", "password": "supersecret",
    }).json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {tok}"})
    c.post("/demo")
    return c


def test_protected_without_token():
    c = TestClient(app)
    assert c.get("/stats").status_code == 401


def test_register_and_login_roundtrip():
    c = TestClient(app)
    r = c.post("/auth/register", json={
        "name": "Ada", "email": "ada@example.com", "password": "password123", "role": "ciso",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "ciso"
    assert body["access_token"]
    # duplicate email rejected
    assert c.post("/auth/register", json={
        "name": "Ada2", "email": "ada@example.com", "password": "password123",
    }).status_code == 409
    # wrong password rejected
    assert c.post("/auth/login", json={
        "email": "ada@example.com", "password": "wrong",
    }).status_code == 401


def test_me(client):
    me = client.get("/auth/me").json()
    assert me["email"] == "test@example.com"


def test_stats_has_exposure(client):
    s = client.get("/stats").json()
    assert s["footholds"] == 4
    assert s["footholds_reaching_target"] == 4
    assert 0 <= s["exposure_score"] <= 100
    assert s["exposure_band"] in {"Low", "Medium", "High"}
    assert s["choke_points"] == 2


def test_fleet(client):
    f = client.get("/fleet").json()
    assert len(f) >= 1
    assert f[0]["cluster_name"] == "synthetic-vulnerable-01"
    assert f[0]["choke_points"] == 2


def test_graph_shape(client):
    g = client.get("/graph").json()
    assert any(e["data"]["etype"] == "CAN_CREATE_POD" for e in g["edges"])


def test_paths(client):
    assert len(client.get("/paths").json()) == 4


def test_top_remediation_cuts_all(client):
    rem = client.get("/remediations?top=5").json()
    assert rem[0]["footholds_cut"] == 4
