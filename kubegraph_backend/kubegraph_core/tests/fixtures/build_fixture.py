"""Construct a synthetic vulnerable cluster with KNOWN escalation paths.

This is the seed of the ground-truth corpus used by the evaluation harness.
It is designed with a deliberate CHOKE POINT: three separate low-privilege
footholds all escalate through the single privileged service account
``kube-system/deployer`` (bound to cluster-admin). Later phases will show that
removing one edge collapses many paths — exactly what choke-point ranking is
meant to find.

Run:  python tests/fixtures/build_fixture.py   # writes vulnerable_cluster.json
"""

from __future__ import annotations

import json
from pathlib import Path

from kubegraph.models.inventory import (
    Binding, Inventory, Namespace, Pod, PolicyRule, Role, RoleRef,
    Secret, ServiceAccount, Subject,
)


def build() -> Inventory:
    inv = Inventory(cluster_name="synthetic-vulnerable-01")
    inv.namespaces = [Namespace(name=n) for n in ("default", "prod", "kube-system")]

    inv.service_accounts = [
        ServiceAccount(name="web", namespace="default"),
        ServiceAccount(name="api", namespace="default"),
        ServiceAccount(name="worker", namespace="prod"),
        ServiceAccount(name="secops", namespace="prod"),
        ServiceAccount(name="deployer", namespace="kube-system"),  # crown jewel
        ServiceAccount(name="default", namespace="default"),
    ]

    inv.pods = [
        Pod(name="web-frontend", namespace="default", service_account="web"),
        Pod(name="api-server", namespace="default", service_account="api"),
        Pod(name="batch-worker", namespace="prod", service_account="worker"),
        Pod(name="audit-agent", namespace="prod", service_account="secops"),
    ]

    inv.secrets = [
        Secret(name="deployer-token", namespace="kube-system",
               type="kubernetes.io/service-account-token", sa_token_for="deployer"),
    ]

    inv.roles = [
        # The crown jewel: real cluster-admin.
        Role(kind="ClusterRole", name="cluster-admin",
             rules=[PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])]),
        # CHOKE-POINT source: create pods cluster-wide (-> mount deployer).
        Role(kind="ClusterRole", name="pod-creator",
             rules=[PolicyRule(api_groups=[""], resources=["pods"],
                               verbs=["create", "get", "list"])]),
        # Alt path: read secrets (ClusterRole, confined to kube-system by the
        # RoleBinding below) -> deployer token.
        Role(kind="ClusterRole", name="secret-reader",
             rules=[PolicyRule(api_groups=[""], resources=["secrets"],
                               verbs=["get", "list"])]),
        # A benign role that should NOT create a path (true-negative control).
        Role(kind="Role", name="configmap-viewer", namespace="default",
             rules=[PolicyRule(api_groups=[""], resources=["configmaps"],
                               verbs=["get", "list"])]),
    ]

    inv.bindings = [
        # deployer -> cluster-admin (the crown-jewel binding).
        Binding(kind="ClusterRoleBinding", name="deployer-admin",
                role_ref=RoleRef(kind="ClusterRole", name="cluster-admin"),
                subjects=[Subject(kind="ServiceAccount", name="deployer",
                                  namespace="kube-system")]),
        # web + api + worker all get pod-creator -> all funnel through deployer.
        Binding(kind="ClusterRoleBinding", name="web-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="web", namespace="default")]),
        Binding(kind="ClusterRoleBinding", name="api-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="api", namespace="default")]),
        Binding(kind="ClusterRoleBinding", name="worker-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="worker", namespace="prod")]),
        # secops -> read kube-system secrets (alternate route to deployer token).
        Binding(kind="RoleBinding", name="secops-secretreader", namespace="kube-system",
                role_ref=RoleRef(kind="ClusterRole", name="secret-reader"),
                subjects=[Subject(kind="ServiceAccount", name="secops", namespace="prod")]),
        # benign binding (control).
        Binding(kind="RoleBinding", name="web-cmviewer", namespace="default",
                role_ref=RoleRef(kind="Role", name="configmap-viewer"),
                subjects=[Subject(kind="ServiceAccount", name="web", namespace="default")]),
    ]
    return inv


# Ground-truth labels: footholds that SHOULD reach cluster-admin.
GROUND_TRUTH_REACHABLE = {
    "pod:default/web-frontend",
    "pod:default/api-server",
    "pod:prod/batch-worker",
    "pod:prod/audit-agent",
}


if __name__ == "__main__":
    out = Path(__file__).with_name("vulnerable_cluster.json")
    out.write_text(build().model_dump_json(indent=2))
    print(f"wrote {out}")
