"""Read-only collector: turns a live cluster (via kubeconfig) into an Inventory.

Requires only read access to RBAC, pods, service accounts, secrets (metadata),
namespaces and nodes. Secret *values* are never read — only enough metadata to
know whether a secret is a service-account token. The heavy import of the
kubernetes client is local so the rest of the package works with no cluster.
"""

from __future__ import annotations

from kubegraph.models.inventory import (
    Binding,
    Inventory,
    Namespace,
    Node,
    Pod,
    PolicyRule,
    Role,
    RoleRef,
    Secret,
    ServiceAccount,
    Subject,
)


def collect(context: str | None = None, cluster_name: str = "collected") -> Inventory:
    from kubernetes import client, config  # local import by design

    try:
        config.load_kube_config(context=context)
    except Exception:
        config.load_incluster_config()

    core = client.CoreV1Api()
    rbac = client.RbacAuthorizationV1Api()

    inv = Inventory(cluster_name=cluster_name)
    inv.namespaces = [Namespace(name=ns.metadata.name)
                      for ns in core.list_namespace().items]
    inv.nodes = [Node(name=n.metadata.name) for n in core.list_node().items]

    for sa in core.list_service_account_for_all_namespaces().items:
        automount = sa.automount_service_account_token
        inv.service_accounts.append(ServiceAccount(
            name=sa.metadata.name, namespace=sa.metadata.namespace,
            automount=True if automount is None else automount,
        ))

    for pod in core.list_pod_for_all_namespaces().items:
        spec = pod.spec
        sc = spec.security_context
        host_path = any(v.host_path is not None for v in (spec.volumes or []))
        privileged = any(
            (c.security_context and c.security_context.privileged)
            for c in (spec.containers or [])
        )
        inv.pods.append(Pod(
            name=pod.metadata.name, namespace=pod.metadata.namespace,
            service_account=spec.service_account_name or "default",
            node=spec.node_name,
            privileged=bool(privileged),
            host_pid=bool(spec.host_pid),
            host_network=bool(spec.host_network),
            host_path=host_path,
        ))

    for sec in core.list_secret_for_all_namespaces().items:
        sa_for = None
        if sec.type == "kubernetes.io/service-account-token":
            sa_for = (sec.metadata.annotations or {}).get(
                "kubernetes.io/service-account.name")
        inv.secrets.append(Secret(
            name=sec.metadata.name, namespace=sec.metadata.namespace,
            type=sec.type or "Opaque", sa_token_for=sa_for,
        ))

    inv.roles.extend(_convert_roles(rbac.list_role_for_all_namespaces().items, "Role"))
    inv.roles.extend(_convert_roles(rbac.list_cluster_role().items, "ClusterRole"))
    inv.bindings.extend(_convert_bindings(
        rbac.list_role_binding_for_all_namespaces().items, "RoleBinding"))
    inv.bindings.extend(_convert_bindings(
        rbac.list_cluster_role_binding().items, "ClusterRoleBinding"))
    return inv


def _convert_roles(items, kind: str) -> list[Role]:
    out = []
    for r in items:
        rules = [PolicyRule(
            api_groups=list(rule.api_groups or [""]),
            resources=list(rule.resources or []),
            verbs=list(rule.verbs or []),
            resource_names=list(rule.resource_names or []),
        ) for rule in (r.rules or [])]
        out.append(Role(kind=kind, name=r.metadata.name,
                        namespace=r.metadata.namespace if kind == "Role" else None,
                        rules=rules))
    return out


def _convert_bindings(items, kind: str) -> list[Binding]:
    out = []
    for b in items:
        subjects = [Subject(kind=s.kind, name=s.name, namespace=s.namespace)
                    for s in (b.subjects or [])]
        out.append(Binding(
            kind=kind, name=b.metadata.name,
            namespace=b.metadata.namespace if kind == "RoleBinding" else None,
            role_ref=RoleRef(kind=b.role_ref.kind, name=b.role_ref.name),
            subjects=subjects,
        ))
    return out
