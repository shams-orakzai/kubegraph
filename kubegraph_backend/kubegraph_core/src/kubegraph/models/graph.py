"""The attack-graph vocabulary: node types, edge types, and the crucial
distinction between STRUCTURAL edges (facts about the cluster that cannot be
"fixed") and REMOVABLE edges (actionable RBAC/config grants).

Only REMOVABLE edges are ever candidate remediations. The choke-point engine
(Phase 3) ranks removable edges by how many attacker->target paths their
removal severs. This split is what makes remediation ranking meaningful.
"""

from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    SERVICE_ACCOUNT = "ServiceAccount"
    USER = "User"
    GROUP = "Group"
    POD = "Pod"
    ROLE = "Role"          # covers Role and ClusterRole
    SECRET = "Secret"
    NODE = "Node"
    TARGET = "Target"      # abstract crown-jewel (e.g. cluster-admin)


class EdgeType(StrEnum):
    # --- structural: part of the graph, never a remediation ---
    USES_SA = "USES_SA"            # Pod -> ServiceAccount (token is in the pod)
    TOKEN_FOR = "TOKEN_FOR"        # Secret -> ServiceAccount (token secret)

    # --- removable: real permission grants; these are remediation targets ---
    GRANTED_ROLE = "GRANTED_ROLE"        # Identity -> Role (via a binding)
    IS_CLUSTER_ADMIN = "IS_CLUSTER_ADMIN"  # Role -> Target (role grants */*)
    CAN_CREATE_POD = "CAN_CREATE_POD"    # can create pod/workload -> mount any SA
    CAN_EXEC = "CAN_EXEC"                # pods/exec -> enter pod, use its SA
    CAN_EPHEMERAL = "CAN_EPHEMERAL"      # pods/ephemeralcontainers -> inject
    CAN_GET_SECRET = "CAN_GET_SECRET"    # get/list secrets -> read token/creds
    CAN_CREATE_TOKEN = "CAN_CREATE_TOKEN"  # serviceaccounts/token -> mint token
    CAN_IMPERSONATE = "CAN_IMPERSONATE"  # impersonate verb -> become identity
    CAN_ESCALATE = "CAN_ESCALATE"        # escalate verb -> grant self anything
    CAN_BIND = "CAN_BIND"                # bind verb -> bind self to admin role
    CAN_UPDATE_RBAC = "CAN_UPDATE_RBAC"  # patch/update roles or bindings
    CAN_APPROVE_CSR = "CAN_APPROVE_CSR"  # approve CSR -> mint client cert


STRUCTURAL_EDGES: frozenset[EdgeType] = frozenset(
    {EdgeType.USES_SA, EdgeType.TOKEN_FOR}
)

# Edges the engine is allowed to propose removing.
REMOVABLE_EDGES: frozenset[EdgeType] = frozenset(
    e for e in EdgeType if e not in STRUCTURAL_EDGES
)


# --- node id helpers: stable, human-readable, collision-free -----------------

def sa_id(namespace: str, name: str) -> str:
    return f"sa:{namespace}/{name}"


def pod_id(namespace: str, name: str) -> str:
    return f"pod:{namespace}/{name}"


def role_id(kind: str, name: str, namespace: str | None) -> str:
    scope = namespace if kind == "Role" else "-"
    return f"role:{kind.lower()}:{scope}/{name}"


def secret_id(namespace: str, name: str) -> str:
    return f"secret:{namespace}/{name}"


def node_id(name: str) -> str:
    return f"node:{name}"


def user_id(name: str) -> str:
    return f"user:{name}"


def group_id(name: str) -> str:
    return f"group:{name}"


TARGET_CLUSTER_ADMIN = "target:cluster-admin"
