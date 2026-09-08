"""Ground-truth evaluation corpus (C1-C5).

Each cluster is a *synthetic inventory* — data we construct by hand — in which
the true escalation paths are documented in advance (the `ground_truth` set).
That is what makes them ground truth: we know the right answer because we
planted it. They are fed straight into the engine (no live cluster), which is
exactly why detection accuracy can be measured at all.

Each scenario also carries:
  - `controls`  : footholds that must NOT reach admin (false-positive guard)
  - `candidates`: the removable "findings" both ranking strategies rank, each
                  tagged with a severity weight (as a scanner would assign)

Every cluster is chosen to probe one thing (see `purpose`).
"""

from __future__ import annotations

from dataclasses import dataclass

from kubegraph.models.graph import (
    TARGET_CLUSTER_ADMIN, pod_id, role_id, sa_id, secret_id,
)
from kubegraph.models.inventory import (
    Binding, Inventory, Namespace, Pod, PolicyRule, Role, RoleRef, Secret,
    ServiceAccount, Subject,
)

# severity weights, as a conventional misconfiguration scanner would assign
CRIT, HIGH, MED = 4, 3, 2

WILDCARD = [PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])]
def _create_pods():   return PolicyRule(api_groups=[""], resources=["pods"], verbs=["create", "get", "list"])
def _get_secrets():   return PolicyRule(api_groups=[""], resources=["secrets"], verbs=["get", "list"])
def _exec_pods():     return PolicyRule(api_groups=[""], resources=["pods/exec"], verbs=["create"])
def _mint_tokens():   return PolicyRule(api_groups=[""], resources=["serviceaccounts/token"], verbs=["create"])


@dataclass
class Scenario:
    name: str
    purpose: str
    inv: Inventory
    ground_truth: set          # foothold pod ids that SHOULD reach admin
    controls: set              # foothold pod ids that must NOT reach admin
    candidates: list           # [(edge_id, severity_weight, label)]


# ---- tiny builder helpers (mutate an inventory) ----
class B:
    def __init__(self, name):
        self.inv = Inventory(cluster_name=name)
        self._ns = set()

    def ns(self, n):
        if n not in self._ns:
            self._ns.add(n); self.inv.namespaces.append(Namespace(name=n))

    def sa(self, ns, name):
        self.ns(ns); self.inv.service_accounts.append(ServiceAccount(name=name, namespace=ns)); return sa_id(ns, name)

    def pod(self, ns, name, sa):
        self.ns(ns); self.inv.pods.append(Pod(name=name, namespace=ns, service_account=sa)); return pod_id(ns, name)

    def crole(self, name, rules):
        self.inv.roles.append(Role(kind="ClusterRole", name=name, namespace=None, rules=rules))
        return role_id("ClusterRole", name, None)

    def crb(self, name, role, ns, sa):
        self.inv.bindings.append(Binding(kind="ClusterRoleBinding", name=name, namespace=None,
                                          role_ref=RoleRef(kind="ClusterRole", name=role),
                                          subjects=[Subject(kind="ServiceAccount", name=sa, namespace=ns)]))

    def rb(self, name, ns, role, sa_ns, sa):
        self.inv.bindings.append(Binding(kind="RoleBinding", name=name, namespace=ns,
                                          role_ref=RoleRef(kind="ClusterRole", name=role),
                                          subjects=[Subject(kind="ServiceAccount", name=sa, namespace=sa_ns)]))

    def secret(self, ns, name, token_for=None):
        self.ns(ns)
        self.inv.secrets.append(Secret(name=name, namespace=ns,
                                        type=("kubernetes.io/service-account-token" if token_for else "Opaque"),
                                        sa_token_for=token_for))
        return secret_id(ns, name)


def _granted(sa_ns, sa_name, role_name):
    return f"{sa_id(sa_ns, sa_name)}->{role_id('ClusterRole', role_name, None)}"


# ============================================================ C1
def build_c1():
    """All footholds funnel through ONE admin binding."""
    b = B("C1-single-admin")
    b.crole("cluster-admin", WILDCARD); b.crole("pod-creator", [_create_pods()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    gt = set()
    for ns, pn, san in [("default", "web-frontend", "web"), ("default", "api-server", "api"),
                        ("prod", "batch-worker", "worker"), ("prod", "audit-agent", "audit")]:
        b.sa(ns, san); b.crb(f"{san}-pc", "pod-creator", ns, san); gt.add(b.pod(ns, pn, san))
    b.sa("default", "readonly"); ctrl = b.pod("default", "dashboard", "readonly")
    cand = [(_granted("kube-system", "deployer", "cluster-admin"), CRIT, "unbind kube-system/deployer from cluster-admin")]
    return Scenario("C1 single-admin", "choke point coincides with a critical finding",
                    b.inv, gt, {ctrl}, cand)


# ============================================================ C2
def build_c2():
    """Five equally-'critical' admin bindings of very unequal impact."""
    b = B("C2-uneven-admins")
    b.crole("pod-creator", [_create_pods()])
    groups = [7, 2, 2, 2, 2]
    gt, cand = set(), []
    fh = 0
    for g, size in enumerate(groups):
        adm_ns = f"a{g}"
        b.crole(f"admin{g}", WILDCARD)
        b.sa(adm_ns, f"adm{g}"); b.crb(f"adm{g}-bind", f"admin{g}", adm_ns, f"adm{g}")
        for _ in range(size):
            san = f"svc{fh}"; b.sa("work", san)
            b.rb(f"{san}-pc", adm_ns, "pod-creator", "work", san)   # create-pods scoped to a{g} -> reaches adm{g} only
            gt.add(b.pod("work", f"pod{fh}", san)); fh += 1
        cand.append((_granted(adm_ns, f"adm{g}", f"admin{g}"), CRIT, f"unbind a{g}/adm{g} from cluster-admin (group of {size})"))
    b.sa("work", "readonly"); ctrl = b.pod("work", "dashboard", "readonly")
    return Scenario("C2 uneven-admins", "discrimination among equal-severity findings",
                    b.inv, gt, {ctrl}, cand)


# ============================================================ C3
def build_c3():
    """A pivotal fix plus lower-severity isolated decoys."""
    b = B("C3-modest-choke-decoys")
    b.crole("cluster-admin", WILDCARD); b.crole("pod-creator", [_create_pods()]); b.crole("secret-reader", [_get_secrets()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    b.secret("data", "config-secret")            # NOT a token -> a dead-end finding
    gt, cand = set(), [(_granted("kube-system", "deployer", "cluster-admin"), CRIT, "unbind deployer from cluster-admin")]
    for i in range(7):
        san = f"svc{i}"; b.sa("work", san)
        b.rb(f"{san}-pc", "kube-system", "pod-creator", "work", san)      # -> reaches deployer
        gt.add(b.pod("work", f"pod{i}", san))
        if i < 3:
            b.rb(f"{san}-sr", "data", "secret-reader", "work", san)       # decoy: reads a non-token secret (cuts nothing)
            cand.append((f"{sa_id('work', san)}->{secret_id('data', 'config-secret')}", HIGH, f"revoke get-secrets from work/{san} (decoy)"))
    b.sa("work", "readonly"); ctrl = b.pod("work", "audit", "readonly")
    return Scenario("C3 modest-choke-decoys", "pivotal grant amid higher-noise findings",
                    b.inv, gt, {ctrl}, cand)


# ============================================================ C4
def build_c4():
    """Cluster-wide create-pod -> a redundant mesh; no single create-pod edge is critical."""
    b = B("C4-redundant-mesh")
    b.crole("cluster-admin", WILDCARD); b.crole("pod-creator", [_create_pods()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    gt = set()
    for i in range(5):
        san = f"svc{i}"; b.sa("work", san)
        b.crb(f"{san}-pc", "pod-creator", "work", san)                   # CLUSTER-WIDE create-pods -> mesh
        gt.add(b.pod("work", f"pod{i}", san))
    b.sa("work", "readonly"); ctrl = b.pod("work", "audit", "readonly")
    cand = [(_granted("kube-system", "deployer", "cluster-admin"), CRIT, "unbind deployer from cluster-admin")]
    # a few individual create-pod edges: each cuts 0 (attacker reroutes through the mesh)
    for i in range(3):
        cand.append((f"{sa_id('work', f'svc{i}')}->{sa_id('kube-system', 'deployer')}", MED,
                     f"revoke pod-create edge work/svc{i} -> deployer"))
    return Scenario("C4 redundant-mesh", "the edge-level limitation, shown empirically",
                    b.inv, gt, {ctrl}, cand)


# ============================================================ C5
def build_c5():
    """A long, linear chain: exec -> mint-token -> read-secret -> admin."""
    b = B("C5-deep-chain")
    b.crole("cluster-admin", WILDCARD)
    b.crole("pod-execer", [_exec_pods()]); b.crole("token-minter", [_mint_tokens()]); b.crole("secret-reader", [_get_secrets()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    b.secret("kube-system", "dep-token", token_for="deployer")
    b.sa("sec", "secbot"); b.rb("sec-read", "kube-system", "secret-reader", "sec", "secbot")   # get-secret -> dep-token -> deployer
    b.sa("mid", "midbot"); b.rb("mid-mint", "sec", "token-minter", "mid", "midbot")            # mint token -> secbot
    b.sa("app", "entry"); midpod = b.pod("mid", "mid-pod", "midbot")                          # midbot's pod, exec target (also reaches admin)
    b.rb("entry-exec", "mid", "pod-execer", "app", "entry")                                     # entry exec -> mid-pod -> midbot
    gt = {b.pod("app", "front-a", "entry"), b.pod("app", "front-b", "entry"), midpod}           # two entry footholds + the mid-chain pod
    b.sa("app", "readonly"); ctrl = b.pod("app", "audit", "readonly")
    cand = [
        (_granted("kube-system", "deployer", "cluster-admin"), CRIT, "unbind deployer from cluster-admin"),
        (f"{sa_id('mid', 'midbot')}->{sa_id('sec', 'secbot')}", HIGH, "revoke token-mint midbot -> secbot"),
        (f"{sa_id('app', 'entry')}->{pod_id('mid', 'mid-pod')}", MED, "revoke exec entry -> mid-pod"),
    ]
    return Scenario("C5 deep-chain", "detection on a long (multi-hop) path",
                    b.inv, gt, {ctrl}, cand)


def all_scenarios():
    return [build_c1(), build_c2(), build_c3(), build_c4(), build_c5()]


# ---- star clusters for the scalability benchmark ----
def build_star(n_footholds: int) -> Inventory:
    """n footholds, each reaching a single admin via a namespace-scoped
    create-pod grant (linear in edges, so the exact recompute stays tractable
    to time)."""
    b = B(f"star-{n_footholds}")
    b.crole("cluster-admin", WILDCARD); b.crole("pod-creator", [_create_pods()])
    b.sa("kube-system", "deployer"); b.crb("deployer-admin", "cluster-admin", "kube-system", "deployer")
    for i in range(n_footholds):
        san = f"svc{i}"; b.sa("work", san)
        b.rb(f"{san}-pc", "kube-system", "pod-creator", "work", san)   # scoped -> only reaches deployer
        b.pod("work", f"pod{i}", san)
    return b.inv
