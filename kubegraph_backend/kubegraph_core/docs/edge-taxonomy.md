# KubeGraph Edge Taxonomy (v1 — RBAC identity core)

Every edge models a documented Kubernetes privilege-escalation primitive. Edges
are either **structural** (facts that cannot be remediated) or **removable**
(actionable grants — the only candidates the choke-point engine ranks).

## Node types

| Node | Meaning |
|---|---|
| `ServiceAccount` | Workload identity; holder of a mountable token |
| `User` / `Group` | External / implicit identities (incl. `system:serviceaccounts*`) |
| `Pod` | Attacker foothold; carries its SA token |
| `Role` | Role or ClusterRole (a bundle of grants) |
| `Secret` | Credential store; SA-token secrets link back to an SA |
| `Node` | Worker/control-plane node (v2 breakout layer) |
| `Target` | Abstract crown jewel, e.g. `cluster-admin` |

## Structural edges (never remediated)

| Edge | From → To | Meaning |
|---|---|---|
| `USES_SA` | Pod → ServiceAccount | Compromising the pod yields its SA token |
| `TOKEN_FOR` | Secret → ServiceAccount | A read token secret grants that SA |

## Removable edges (remediation targets)

| Edge | Trigger (verb on resource) | Escalation |
|---|---|---|
| `GRANTED_ROLE` | RoleBinding / ClusterRoleBinding | Identity inherits a role's grants |
| `IS_CLUSTER_ADMIN` | role has `*/*/*` (or built-in cluster-admin) | Role → Target |
| `CAN_CREATE_POD` | `create` on pods/deployments/daemonsets/statefulsets/replicasets/jobs/cronjobs/replicationcontrollers | Create a pod that mounts any SA → steal its token |
| `CAN_EXEC` | `create` on `pods/exec` | Exec into a pod, inherit its SA |
| `CAN_EPHEMERAL` | `create/update/patch` on `pods/ephemeralcontainers` | Inject a container into a running pod |
| `CAN_GET_SECRET` | `get`/`list` on `secrets` | Read an SA token or credential |
| `CAN_CREATE_TOKEN` | `create` on `serviceaccounts/token` | Mint a token for a target SA |
| `CAN_IMPERSONATE` | `impersonate` on users/groups/serviceaccounts | Act as another (higher-priv) identity |
| `CAN_ESCALATE` | `escalate` on roles/clusterroles | Grant yourself arbitrary rights |
| `CAN_BIND` | `bind` on roles/clusterroles | Bind yourself to an existing admin role |
| `CAN_UPDATE_RBAC` | `create/update/patch` on rolebindings/clusterrolebindings | Rewrite a binding to point at admin |
| `CAN_APPROVE_CSR` | `update` on `certificatesigningrequests/approval` | Approve a CSR → mint a client cert |

## Scope semantics

* A **ClusterRoleBinding** grant applies cluster-wide (`scope = None`).
* A **RoleBinding** confines even a ClusterRole's rules to the binding's
  namespace (`scope = <namespace>`).
* `resourceNames` on a rule narrows the reachable objects (reduces false
  positives, e.g. `get secret X` links only to secret X).
* A full `*/*/*` grant is represented **only** via `IS_CLUSTER_ADMIN`; it does
  not spawn redundant capability edges.

## Planned v2 extension (node-breakout layer)

`CAN_CREATE_PRIVILEGED_POD`, `hostPath`/`hostPID`/`hostNetwork` →
`CONTAINER_ESCAPE` → `Node` → every SA token on that node. Deferred until the
RBAC core + evaluation loop is complete.
