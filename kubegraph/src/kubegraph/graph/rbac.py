"""RBAC semantics: matching rules, resolving an identity's effective grants
(with correct namespace scope), and detecting cluster-admin roles.

This module is deliberately pure/functional so each rule is unit-testable and
so the false-positive characteristics (an evaluation metric) can be reasoned
about precisely.
"""

from __future__ import annotations

from dataclasses import dataclass

from kubegraph.models.inventory import Inventory, PolicyRule, Role, Subject


@dataclass(frozen=True)
class Grant:
    """One effective rule together with the scope it applies in.

    ``scope`` is None for cluster-wide grants (ClusterRoleBinding), otherwise
    the namespace the grant is confined to (RoleBinding).
    """

    rule: PolicyRule
    scope: str | None


def _match(values: list[str], target: str) -> bool:
    return "*" in values or target in values


def rule_allows(
    rule: PolicyRule, verb: str, resource: str, api_group: str = ""
) -> bool:
    """True if ``rule`` permits ``verb`` on ``resource`` in ``api_group``."""
    return (
        _match(rule.verbs, verb)
        and _match(rule.resources, resource)
        and _match(rule.api_groups, api_group)
    )


def resource_scope(rule: PolicyRule) -> set[str] | None:
    """Named-resource restriction, or None if the rule is unrestricted."""
    return set(rule.resource_names) if rule.resource_names else None


def sa_groups(namespace: str) -> set[str]:
    """Implicit groups every ServiceAccount belongs to."""
    return {
        "system:authenticated",
        "system:serviceaccounts",
        f"system:serviceaccounts:{namespace}",
    }


def _subject_matches(subject: Subject, sa_name: str, sa_ns: str) -> bool:
    if subject.kind == "ServiceAccount":
        return subject.name == sa_name and subject.namespace == sa_ns
    if subject.kind == "Group":
        return subject.name in sa_groups(sa_ns)
    return False  # User subjects handled separately


def effective_grants(inv: Inventory, sa_name: str, sa_ns: str) -> list[Grant]:
    """All grants that apply to a ServiceAccount, following every binding it
    is a subject of (directly or via an implicit system group)."""
    idx = inv.role_index()
    grants: list[Grant] = []
    for binding in inv.bindings:
        if not any(_subject_matches(s, sa_name, sa_ns) for s in binding.subjects):
            continue
        role = idx.get(
            (binding.role_ref.kind, binding.role_ref.name,
             None if binding.role_ref.kind == "ClusterRole" else binding.namespace)
        )
        if role is None:
            continue
        # A RoleBinding confines even a ClusterRole's rules to the binding's ns.
        scope = None if binding.kind == "ClusterRoleBinding" else binding.namespace
        for rule in role.rules:
            grants.append(Grant(rule=rule, scope=scope))
    return grants


def role_is_cluster_admin(role: Role) -> bool:
    """True if the role grants verb=* on resource=* in apiGroup=* (the
    built-in cluster-admin shape), or is the built-in cluster-admin ClusterRole."""
    if role.kind == "ClusterRole" and role.name == "cluster-admin":
        return True
    for r in role.rules:
        if "*" in r.verbs and "*" in r.resources and "*" in r.api_groups:
            return True
    return False


def granted_roles(inv: Inventory, sa_name: str, sa_ns: str) -> list[Role]:
    """The concrete Role/ClusterRole objects bound to a ServiceAccount."""
    idx = inv.role_index()
    out: list[Role] = []
    seen: set[tuple[str, str, str | None]] = set()
    for binding in inv.bindings:
        if not any(_subject_matches(s, sa_name, sa_ns) for s in binding.subjects):
            continue
        key = (
            binding.role_ref.kind,
            binding.role_ref.name,
            None if binding.role_ref.kind == "ClusterRole" else binding.namespace,
        )
        role = idx.get(key)
        if role is not None and key not in seen:
            seen.add(key)
            out.append(role)
    return out
