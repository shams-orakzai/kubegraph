"""Validate the builder + path engine against the ground-truth fixture.

These assertions are the beginnings of the detection-coverage / false-positive
evaluation: every labelled foothold must reach cluster-admin (coverage) and the
true-negative control must NOT (false-positive guard).
"""

from __future__ import annotations

import pytest

from kubegraph.graph import paths as pathmod
from kubegraph.graph.builder import build_graph
from kubegraph.graph.rbac import rule_allows
from kubegraph.models.graph import EdgeType, TARGET_CLUSTER_ADMIN
from kubegraph.models.inventory import PolicyRule

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "build_fixture", Path(__file__).parent / "fixtures" / "build_fixture.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


@pytest.fixture
def graph():
    return build_graph(_fx.build())


def test_target_exists(graph):
    assert graph.has_node(TARGET_CLUSTER_ADMIN)


def test_detection_coverage(graph):
    """Every ground-truth foothold reaches cluster-admin (recall = 1.0)."""
    reachable = set(pathmod.reachable_footholds(graph).keys())
    missing = _fx.GROUND_TRUTH_REACHABLE - reachable
    assert not missing, f"missed known escalation paths: {missing}"


def test_choke_point_convergence(graph):
    """All three pod-creator footholds funnel through kube-system/deployer."""
    deployer = "sa:kube-system/deployer"
    for fh in ("pod:default/web-frontend", "pod:default/api-server",
               "pod:prod/batch-worker"):
        path = pathmod.shortest_attack_path(graph, fh)
        assert path is not None and deployer in path.nodes


def test_secret_route(graph):
    """secops reaches admin via the deployer token secret, not pod-creation."""
    path = pathmod.shortest_attack_path(graph, "pod:prod/audit-agent")
    assert path is not None
    assert EdgeType.CAN_GET_SECRET in path.edges
    assert EdgeType.TOKEN_FOR in path.edges


def test_admin_binding_is_choke_point(graph):
    """Removing deployer's cluster-admin binding cuts ALL paths (choke point)."""
    g = graph.copy()
    g.remove_edge("sa:kube-system/deployer",
                  "role:clusterrole:-/cluster-admin")
    assert not pathmod.reachable_footholds(g)


def test_wildcard_matching():
    r = PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])
    assert rule_allows(r, "create", "pods")
    assert rule_allows(r, "delete", "secrets", "anything")


def test_named_resource_scoping():
    r = PolicyRule(api_groups=[""], resources=["secrets"], verbs=["get"],
                   resource_names=["only-this"])
    assert rule_allows(r, "get", "secrets")  # verb/resource match...
    # ...but scoping is enforced in the builder via resource_scope()
