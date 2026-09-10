"""Catalog of selectable synthetic demo clusters.

Each entry is a builder that returns a fully-formed :class:`Inventory`. The
clusters are intentionally varied in topology so that the engine produces
naturally different results (graph size, exposure score, path mix, choke
points and remediation ranking). Three groups are exposed:

* ``Featured``   - hand-designed scenarios that each highlight one class of
                   misconfiguration (secret theft, impersonation, RBAC
                   self-escalation, a large messy estate, a hardened baseline).
* ``Evaluation`` - the C1-C5 ground-truth corpus used in the dissertation, so
                   the exact clusters behind the reported results are loadable
                   in the UI.

Adding a cluster is a one-liner: write a ``build_*`` function and append a
``DemoCluster`` to ``CATALOG``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from kubegraph.evaluation.clusters import (
    B, build_c1, build_c2, build_c3, build_c4, build_c5,
)
from kubegraph.models.inventory import (
    Binding, Inventory, Namespace, Pod, PolicyRule, Role, RoleRef, Secret,
    ServiceAccount, Subject,
)


@dataclass(frozen=True)
class DemoCluster:
    id: str                       # url-safe, stable identifier
    name: str                     # display name for the dropdown
    description: str              # one-line summary of what it demonstrates
    group: str                    # "Featured" | "Evaluation corpus"
    build: Callable[[], Inventory]


# --- reusable RBAC rule fragments -------------------------------------------
_RBAC = "rbac.authorization.k8s.io"
_CERTS = "certificates.k8s.io"
WILDCARD = [PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])]

def _create_pods():   return PolicyRule(api_groups=[""], resources=["pods"], verbs=["create", "get", "list"])
def _get_secrets():   return PolicyRule(api_groups=[""], resources=["secrets"], verbs=["get", "list"])
def _exec_pods():     return PolicyRule(api_groups=[""], resources=["pods/exec"], verbs=["create"])
def _impersonate():   return PolicyRule(api_groups=[""], resources=["users", "groups", "serviceaccounts"], verbs=["impersonate"])
def _escalate():      return PolicyRule(api_groups=[_RBAC], resources=["clusterroles", "roles"], verbs=["escalate"])
def _bind():          return PolicyRule(api_groups=[_RBAC], resources=["clusterroles", "roles"], verbs=["bind"])
def _write_rbac():    return PolicyRule(api_groups=[_RBAC], resources=["rolebindings", "clusterrolebindings"], verbs=["create", "update", "patch"])
def _approve_csr():   return PolicyRule(api_groups=[_CERTS], resources=["certificatesigningrequests/approval"], verbs=["update"])
def _view_config():   return PolicyRule(api_groups=[""], resources=["configmaps", "pods"], verbs=["get", "list"])


# ============================================================ original fixture
def build_synthetic_vulnerable() -> Inventory:
    """The canonical vulnerable cluster: three pod-creator footholds funnel
    through a single admin-bound deployer, plus a secret-theft alternate route."""
    inv = Inventory(cluster_name="synthetic-vulnerable-01")
    inv.namespaces = [Namespace(name=n) for n in ("default", "prod", "kube-system")]
    inv.service_accounts = [
        ServiceAccount(name="web", namespace="default"),
        ServiceAccount(name="api", namespace="default"),
        ServiceAccount(name="worker", namespace="prod"),
        ServiceAccount(name="secops", namespace="prod"),
        ServiceAccount(name="deployer", namespace="kube-system"),
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
        Role(kind="ClusterRole", name="cluster-admin", rules=WILDCARD),
        Role(kind="ClusterRole", name="pod-creator", rules=[_create_pods()]),
        Role(kind="ClusterRole", name="secret-reader", rules=[_get_secrets()]),
        Role(kind="Role", name="configmap-viewer", namespace="default",
             rules=[PolicyRule(api_groups=[""], resources=["configmaps"], verbs=["get", "list"])]),
    ]
    inv.bindings = [
        Binding(kind="ClusterRoleBinding", name="deployer-admin",
                role_ref=RoleRef(kind="ClusterRole", name="cluster-admin"),
                subjects=[Subject(kind="ServiceAccount", name="deployer", namespace="kube-system")]),
        Binding(kind="ClusterRoleBinding", name="web-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="web", namespace="default")]),
        Binding(kind="ClusterRoleBinding", name="api-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="api", namespace="default")]),
        Binding(kind="ClusterRoleBinding", name="worker-podcreator",
                role_ref=RoleRef(kind="ClusterRole", name="pod-creator"),
                subjects=[Subject(kind="ServiceAccount", name="worker", namespace="prod")]),
        Binding(kind="RoleBinding", name="secops-secretreader", namespace="kube-system",
                role_ref=RoleRef(kind="ClusterRole", name="secret-reader"),
                subjects=[Subject(kind="ServiceAccount", name="secops", namespace="prod")]),
        Binding(kind="RoleBinding", name="web-cmviewer", namespace="default",
                role_ref=RoleRef(kind="Role", name="configmap-viewer"),
                subjects=[Subject(kind="ServiceAccount", name="web", namespace="default")]),
    ]
    return inv


# ============================================================ hardened baseline
def build_hardened() -> Inventory:
    """A well-configured estate: real workloads, an admin identity — but no
    workload can reach it. Exposure should be zero (the safe-cluster contrast)."""
    b = B("hardened-baseline")
    b.crole("cluster-admin", WILDCARD)
    b.crole("viewer", [_view_config()])
    # admin exists but is only bound to a control-plane SA with no pod.
    b.sa("kube-system", "controller"); b.crb("controller-admin", "cluster-admin", "kube-system", "controller")
    for ns, pn, san in [("default", "web", "web"), ("default", "api", "api"),
                        ("payments", "ledger", "ledger"), ("payments", "worker", "worker"),
                        ("observability", "grafana", "grafana")]:
        b.sa(ns, san); b.rb(f"{san}-view", ns, "viewer", ns, san); b.pod(ns, pn, san)
    return b.inv


# ============================================================ secret sprawl
def build_secret_sprawl() -> Inventory:
    """Over-broad secret access: several apps can read the admin token secret
    in kube-system, so every one of them can steal cluster-admin."""
    b = B("secret-sprawl")
    b.crole("cluster-admin", WILDCARD)
    b.crole("secret-reader", [_get_secrets()])
    b.crole("viewer", [_view_config()])
    b.sa("kube-system", "platform-admin"); b.crb("padmin-admin", "cluster-admin", "kube-system", "platform-admin")
    b.secret("kube-system", "platform-admin-token", token_for="platform-admin")
    b.secret("kube-system", "registry-creds")   # a non-token secret (dead-end)
    for ns, pn, san in [("payments", "payments-api", "payments"), ("orders", "orders-api", "orders"),
                        ("search", "search-idx", "search"), ("notify", "notifier", "notifier"),
                        ("web", "storefront", "storefront")]:
        b.sa(ns, san)
        b.rb(f"{san}-secrets", "kube-system", "secret-reader", ns, san)   # read kube-system secrets -> admin token
        b.pod(ns, pn, san)
    # a benign workload that only reads a non-token secret: reachable-looking but a dead end
    b.sa("web", "cdn"); b.rb("cdn-secrets", "kube-system", "secret-reader", "web", "cdn")
    b.pod("web", "cdn-cache", "cdn")   # also reaches (reads the token) — realistic sprawl
    b.sa("web", "readonly"); b.rb("ro-view", "web", "viewer", "web", "readonly"); b.pod("web", "dashboard", "readonly")
    return b.inv


# ============================================================ impersonation
def build_impersonation() -> Inventory:
    """Impersonation shortcuts: several SAs can impersonate any identity, each a
    direct one-hop route to admin. No single binding is a universal choke point."""
    b = B("impersonation-abuse")
    b.crole("cluster-admin", WILDCARD)
    b.crole("impersonator", [_impersonate()])
    b.crole("pod-creator", [_create_pods()])
    b.crole("viewer", [_view_config()])
    # a normal admin identity (no pod)
    b.sa("kube-system", "sre"); b.crb("sre-admin", "cluster-admin", "kube-system", "sre")
    for ns, pn, san in [("ci", "jenkins", "jenkins"), ("support", "helpdesk", "helpdesk"),
                        ("automation", "runbook-bot", "runbook")]:
        b.sa(ns, san); b.crb(f"{san}-imp", "impersonator", ns, san); b.pod(ns, pn, san)
    # a couple of create-pod workloads for a second flavour of route
    b.sa("default", "web"); b.crb("web-pc", "pod-creator", "default", "web"); b.pod("default", "web-frontend", "web")
    b.sa("default", "readonly"); b.rb("ro-view", "default", "viewer", "default", "readonly"); b.pod("default", "audit", "readonly")
    return b.inv


# ============================================================ RBAC self-escalation
def build_rbac_selfservice() -> Inventory:
    """Self-escalation via powerful RBAC verbs: escalate, bind, write-rbac and
    approve-csr each give a workload a direct path to admin."""
    b = B("rbac-self-escalation")
    b.crole("cluster-admin", WILDCARD)
    b.crole("role-escalator", [_escalate()])
    b.crole("role-binder", [_bind()])
    b.crole("rbac-writer", [_write_rbac()])
    b.crole("csr-approver", [_approve_csr()])
    b.crole("viewer", [_view_config()])
    for ns, pn, san, role in [
        ("platform", "gitops", "gitops", "role-escalator"),
        ("platform", "operator", "operator", "role-binder"),
        ("delivery", "argocd", "argocd", "rbac-writer"),
        ("pki", "cert-manager", "certmgr", "csr-approver"),
    ]:
        b.sa(ns, san); b.crb(f"{san}-bind", role, ns, san); b.pod(ns, pn, san)
    b.sa("platform", "readonly"); b.rb("ro-view", "platform", "viewer", "platform", "readonly")
    b.pod("platform", "dashboard", "readonly")
    return b.inv


# ============================================================ enterprise sprawl
def build_enterprise_sprawl() -> Inventory:
    """A large, messy multi-namespace estate with several mixed escalation
    routes (create-pod, exec ladder, secret theft) converging on one admin."""
    b = B("enterprise-sprawl")
    b.crole("cluster-admin", WILDCARD)
    b.crole("pod-creator", [_create_pods()])
    b.crole("pod-execer", [_exec_pods()])
    b.crole("secret-reader", [_get_secrets()])
    b.crole("viewer", [_view_config()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    b.secret("kube-system", "deployer-token", token_for="deployer")

    # route 1: create-pod (scoped to kube-system) -> mount deployer
    for ns, pn, san in [("default", "web-frontend", "web"), ("default", "api-server", "api"),
                        ("payments", "billing", "billing")]:
        b.sa(ns, san); b.rb(f"{san}-pc", "kube-system", "pod-creator", ns, san); b.pod(ns, pn, san)

    # route 2: secret theft -> deployer token
    for ns, pn, san in [("data", "etl", "etl"), ("data", "reporting", "reporting")]:
        b.sa(ns, san); b.rb(f"{san}-sr", "kube-system", "secret-reader", ns, san); b.pod(ns, pn, san)

    # route 3: an exec ladder — entry execs into the CI pod, whose SA can create pods
    b.sa("ci", "jenkins"); b.rb("jenkins-pc", "kube-system", "pod-creator", "ci", "jenkins")
    ci_pod = b.pod("ci", "jenkins-main", "jenkins")   # foothold + exec target
    b.sa("ci", "runner"); b.rb("runner-exec", "ci", "pod-execer", "ci", "runner")
    b.pod("ci", "pr-runner", "runner")                # execs into jenkins-main -> jenkins -> deployer
    _ = ci_pod

    # benign noise
    for ns, pn, san in [("web", "cdn", "cdn"), ("observability", "grafana", "grafana")]:
        b.sa(ns, san); b.rb(f"{san}-view", ns, "viewer", ns, san); b.pod(ns, pn, san)
    return b.inv


# ============================================================ registry
CATALOG: list[DemoCluster] = [
    DemoCluster("synthetic-vulnerable", "Synthetic vulnerable-01",
                "Classic choke point: pod-creators + a secret route funnel through one admin binding.",
                "Featured", build_synthetic_vulnerable),
    DemoCluster("secret-sprawl", "Secret sprawl",
                "Over-broad secret access — every app can read the admin token and steal cluster-admin.",
                "Featured", build_secret_sprawl),
    DemoCluster("impersonation-abuse", "Impersonation abuse",
                "SAs that can impersonate any identity: many direct one-hop routes, no single choke point.",
                "Featured", build_impersonation),
    DemoCluster("rbac-self-escalation", "RBAC self-escalation",
                "escalate / bind / write-RBAC / approve-CSR verbs each self-promote a workload to admin.",
                "Featured", build_rbac_selfservice),
    DemoCluster("enterprise-sprawl", "Enterprise sprawl",
                "A large multi-namespace estate mixing create-pod, exec-ladder and secret-theft routes.",
                "Featured", build_enterprise_sprawl),
    DemoCluster("hardened-baseline", "Hardened baseline",
                "A well-configured cluster — workloads exist but none can reach admin. Exposure is zero.",
                "Featured", build_hardened),
    DemoCluster("c1-single-admin", "C1 · Single-admin choke point",
                "Evaluation corpus: all footholds funnel through one admin binding.",
                "Evaluation corpus", lambda: build_c1().inv),
    DemoCluster("c2-uneven-admins", "C2 · Uneven admins",
                "Evaluation corpus: five equally-critical admin bindings of very unequal impact.",
                "Evaluation corpus", lambda: build_c2().inv),
    DemoCluster("c3-modest-choke", "C3 · Modest choke + decoys",
                "Evaluation corpus: a pivotal fix amid lower-severity decoy findings.",
                "Evaluation corpus", lambda: build_c3().inv),
    DemoCluster("c4-redundant-mesh", "C4 · Redundant mesh",
                "Evaluation corpus: cluster-wide create-pod — no single edge is critical.",
                "Evaluation corpus", lambda: build_c4().inv),
    DemoCluster("c5-deep-chain", "C5 · Deep chain",
                "Evaluation corpus: a long linear exec → mint → read-secret → admin chain.",
                "Evaluation corpus", lambda: build_c5().inv),
]

_BY_ID = {c.id: c for c in CATALOG}
DEFAULT_ID = "synthetic-vulnerable"


def items() -> list[DemoCluster]:
    return list(CATALOG)


def get(cluster_id: str) -> DemoCluster | None:
    return _BY_ID.get(cluster_id)
