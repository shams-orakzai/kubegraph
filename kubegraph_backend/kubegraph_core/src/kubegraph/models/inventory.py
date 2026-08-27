"""Normalized, security-relevant view of a Kubernetes cluster.

The collector turns raw API-server objects into these models; everything
downstream (graph builder, analysis engine) consumes ``Inventory`` only.
Keeping this boundary means the graph engine is fully testable offline
against synthetic inventories, with no cluster required.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """A single RBAC rule (one entry in a Role/ClusterRole ``rules`` list)."""

    api_groups: list[str] = Field(default_factory=lambda: [""])
    resources: list[str] = Field(default_factory=list)
    verbs: list[str] = Field(default_factory=list)
    resource_names: list[str] = Field(default_factory=list)


class RoleRef(BaseModel):
    kind: str  # "Role" | "ClusterRole"
    name: str


class Subject(BaseModel):
    kind: str  # "ServiceAccount" | "User" | "Group"
    name: str
    namespace: str | None = None


class Role(BaseModel):
    kind: str  # "Role" | "ClusterRole"
    name: str
    namespace: str | None = None  # None for ClusterRole
    rules: list[PolicyRule] = Field(default_factory=list)


class Binding(BaseModel):
    kind: str  # "RoleBinding" | "ClusterRoleBinding"
    name: str
    namespace: str | None = None  # None for ClusterRoleBinding
    role_ref: RoleRef
    subjects: list[Subject] = Field(default_factory=list)


class ServiceAccount(BaseModel):
    name: str
    namespace: str
    automount: bool = True


class Pod(BaseModel):
    name: str
    namespace: str
    service_account: str = "default"
    node: str | None = None
    # Security-context flags reserved for the v2 node-breakout layer.
    privileged: bool = False
    host_pid: bool = False
    host_network: bool = False
    host_path: bool = False


class Secret(BaseModel):
    name: str
    namespace: str
    type: str = "Opaque"
    # Set when type == kubernetes.io/service-account-token: the SA it mints for.
    sa_token_for: str | None = None


class Node(BaseModel):
    name: str
    control_plane: bool = False


class Namespace(BaseModel):
    name: str


class Inventory(BaseModel):
    """Complete security-relevant snapshot of one cluster at one point in time."""

    cluster_name: str = "unknown"
    namespaces: list[Namespace] = Field(default_factory=list)
    service_accounts: list[ServiceAccount] = Field(default_factory=list)
    pods: list[Pod] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)
    bindings: list[Binding] = Field(default_factory=list)
    secrets: list[Secret] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)

    def role_index(self) -> dict[tuple[str, str, str | None], Role]:
        """(kind, name, namespace) -> Role. ClusterRole namespace is None."""
        idx: dict[tuple[str, str, str | None], Role] = {}
        for r in self.roles:
            idx[(r.kind, r.name, r.namespace)] = r
        return idx
