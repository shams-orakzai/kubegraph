"""Build a directed attack graph from a normalized Inventory.

Every edge added here corresponds to a documented Kubernetes privilege-
escalation primitive (see docs/edge-taxonomy.md). Edges carry an ``etype``
attribute (EdgeType) and a ``removable`` flag so the analysis engine can
restrict remediation candidates to real, actionable grants.
"""

from __future__ import annotations

import networkx as nx

from kubegraph.models.graph import (
    REMOVABLE_EDGES,
    TARGET_CLUSTER_ADMIN,
    EdgeType,
    NodeType,
    pod_id,
    role_id,
    sa_id,
    secret_id,
)
from kubegraph.models.inventory import Inventory
from kubegraph.graph import rbac

# RBAC api group for role/binding resources.
_RBAC = "rbac.authorization.k8s.io"
_CERTS = "certificates.k8s.io"

# Resources whose creation yields a pod (and therefore SA-token mounting).
_POD_SPAWNERS = {
    "pods", "deployments", "daemonsets", "statefulsets",
    "replicasets", "replicationcontrollers", "jobs", "cronjobs",
}


def build_graph(inv: Inventory) -> nx.DiGraph:
    g = nx.DiGraph()

    # Crown-jewel target node.
    g.add_node(TARGET_CLUSTER_ADMIN, ntype=NodeType.TARGET, label="cluster-admin")

    _add_entity_nodes(inv, g)
    _add_structural_edges(inv, g)
    _add_role_edges(inv, g)
    _add_capability_edges(inv, g)
    return g


# --- nodes -------------------------------------------------------------------

def _add_entity_nodes(inv: Inventory, g: nx.DiGraph) -> None:
    for sa in inv.service_accounts:
        g.add_node(sa_id(sa.namespace, sa.name), ntype=NodeType.SERVICE_ACCOUNT,
                   label=f"{sa.namespace}/{sa.name}", namespace=sa.namespace)
    for pod in inv.pods:
        g.add_node(pod_id(pod.namespace, pod.name), ntype=NodeType.POD,
                   label=f"{pod.namespace}/{pod.name}", namespace=pod.namespace)
    for sec in inv.secrets:
        g.add_node(secret_id(sec.namespace, sec.name), ntype=NodeType.SECRET,
                   label=f"{sec.namespace}/{sec.name}", namespace=sec.namespace)
    for role in inv.roles:
        g.add_node(role_id(role.kind, role.name, role.namespace),
                   ntype=NodeType.ROLE, label=f"{role.kind}/{role.name}",
                   kind=role.kind)


def _add_edge(g: nx.DiGraph, u: str, v: str, etype: EdgeType, **attrs) -> None:
    g.add_edge(u, v, etype=etype, removable=etype in REMOVABLE_EDGES, **attrs)


# --- structural edges --------------------------------------------------------

def _add_structural_edges(inv: Inventory, g: nx.DiGraph) -> None:
    for pod in inv.pods:
        target = sa_id(pod.namespace, pod.service_account)
        if g.has_node(target):
            _add_edge(g, pod_id(pod.namespace, pod.name), target, EdgeType.USES_SA)
    for sec in inv.secrets:
        if sec.sa_token_for:
            target = sa_id(sec.namespace, sec.sa_token_for)
            if g.has_node(target):
                _add_edge(g, secret_id(sec.namespace, sec.name), target,
                          EdgeType.TOKEN_FOR)


# --- GRANTED_ROLE and IS_CLUSTER_ADMIN --------------------------------------

def _add_role_edges(inv: Inventory, g: nx.DiGraph) -> None:
    for role in inv.roles:
        if rbac.role_is_cluster_admin(role):
            _add_edge(g, role_id(role.kind, role.name, role.namespace),
                      TARGET_CLUSTER_ADMIN, EdgeType.IS_CLUSTER_ADMIN)
    for sa in inv.service_accounts:
        src = sa_id(sa.namespace, sa.name)
        for role in rbac.granted_roles(inv, sa.name, sa.namespace):
            _add_edge(g, src, role_id(role.kind, role.name, role.namespace),
                      EdgeType.GRANTED_ROLE)


# --- capability edges (the escalation primitives) ---------------------------

def _in_scope(scope: str | None, namespace: str) -> bool:
    return scope is None or scope == namespace


def _add_capability_edges(inv: Inventory, g: nx.DiGraph) -> None:
    for sa in inv.service_accounts:
        src = sa_id(sa.namespace, sa.name)
        grants = rbac.effective_grants(inv, sa.name, sa.namespace)
        for grant in grants:
            _apply_grant(inv, g, src, grant)


def _is_full_wildcard(rule) -> bool:
    """A */*/* rule already means cluster-admin; its escalation is represented
    by GRANTED_ROLE -> IS_CLUSTER_ADMIN, so it must not also spawn redundant
    capability edges (which would pollute choke-point ranking)."""
    return "*" in rule.verbs and "*" in rule.resources and "*" in rule.api_groups


def _apply_grant(inv: Inventory, g: nx.DiGraph, src: str, grant) -> None:
    rule, scope = grant.rule, grant.scope
    if _is_full_wildcard(rule):
        return

    # CAN_CREATE_POD: create any pod-spawning resource -> mount any SA in scope.
    if any(rbac.rule_allows(rule, "create", res) for res in _POD_SPAWNERS):
        for sa in inv.service_accounts:
            if _in_scope(scope, sa.namespace):
                dst = sa_id(sa.namespace, sa.name)
                if dst != src:
                    _add_edge(g, src, dst, EdgeType.CAN_CREATE_POD)

    # CAN_EXEC / CAN_EPHEMERAL: enter a running pod, inherit its SA.
    exec_ok = rbac.rule_allows(rule, "create", "pods/exec")
    eph_ok = any(rbac.rule_allows(rule, v, "pods/ephemeralcontainers")
                 for v in ("create", "update", "patch"))
    for pod in inv.pods:
        if not _in_scope(scope, pod.namespace):
            continue
        dst = pod_id(pod.namespace, pod.name)
        if exec_ok and dst != src:
            _add_edge(g, src, dst, EdgeType.CAN_EXEC)
        if eph_ok and dst != src:
            _add_edge(g, src, dst, EdgeType.CAN_EPHEMERAL)

    # CAN_GET_SECRET: read a token/credential secret in scope.
    if rbac.rule_allows(rule, "get", "secrets") or rbac.rule_allows(rule, "list", "secrets"):
        names = rbac.resource_scope(rule)
        for sec in inv.secrets:
            if not _in_scope(scope, sec.namespace):
                continue
            if names is not None and sec.name not in names:
                continue
            _add_edge(g, src, secret_id(sec.namespace, sec.name),
                      EdgeType.CAN_GET_SECRET)

    # CAN_CREATE_TOKEN: mint a token for an SA via the TokenRequest API.
    if rbac.rule_allows(rule, "create", "serviceaccounts/token"):
        names = rbac.resource_scope(rule)
        for sa in inv.service_accounts:
            if not _in_scope(scope, sa.namespace):
                continue
            if names is not None and sa.name not in names:
                continue
            dst = sa_id(sa.namespace, sa.name)
            if dst != src:
                _add_edge(g, src, dst, EdgeType.CAN_CREATE_TOKEN)

    # CAN_IMPERSONATE: become any identity (broad -> straight to admin target).
    if (rbac.rule_allows(rule, "impersonate", "users")
            or rbac.rule_allows(rule, "impersonate", "groups")
            or rbac.rule_allows(rule, "impersonate", "serviceaccounts")):
        _add_edge(g, src, TARGET_CLUSTER_ADMIN, EdgeType.CAN_IMPERSONATE)

    # CAN_ESCALATE: escalate verb on roles -> grant self anything.
    if (rbac.rule_allows(rule, "escalate", "roles", _RBAC)
            or rbac.rule_allows(rule, "escalate", "clusterroles", _RBAC)):
        _add_edge(g, src, TARGET_CLUSTER_ADMIN, EdgeType.CAN_ESCALATE)

    # CAN_BIND: bind verb -> bind self to the existing cluster-admin ClusterRole.
    if (rbac.rule_allows(rule, "bind", "roles", _RBAC)
            or rbac.rule_allows(rule, "bind", "clusterroles", _RBAC)):
        _add_edge(g, src, TARGET_CLUSTER_ADMIN, EdgeType.CAN_BIND)

    # CAN_UPDATE_RBAC: rewrite a binding to point at admin.
    if any(rbac.rule_allows(rule, v, res, _RBAC)
           for v in ("update", "patch", "create")
           for res in ("rolebindings", "clusterrolebindings")):
        _add_edge(g, src, TARGET_CLUSTER_ADMIN, EdgeType.CAN_UPDATE_RBAC)

    # CAN_APPROVE_CSR: approve CSRs -> mint a client cert for any identity.
    if rbac.rule_allows(rule, "update", "certificatesigningrequests/approval", _CERTS):
        _add_edge(g, src, TARGET_CLUSTER_ADMIN, EdgeType.CAN_APPROVE_CSR)
