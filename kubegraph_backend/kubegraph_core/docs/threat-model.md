# KubeGraph Threat Model

## Attacker model

* **Initial position:** the attacker controls a single low-privilege **pod**
  (e.g. via app RCE or a supply-chain compromise). Every pod is therefore a
  candidate **foothold**.
* **Capability:** the attacker can use the mounted ServiceAccount token and any
  Kubernetes API permission it grants, and can chain permissions across
  identities (create pods, exec, read secrets, mint tokens, impersonate, etc.).
* **Goal (crown jewels):** reach a **high-value target** — v1 defines this as
  `cluster-admin`. Future targets: sensitive credential secrets, control-plane
  node access.
* **Out of scope (v1):** control-plane 0-days, etcd-level attacks, cloud IAM
  pivots, network-policy bypass, and runtime exploitation. The tool is a
  *static, point-in-time* configuration analysis, not a runtime detector.

## What "an attack path" means

A directed path in the graph from a foothold pod to a target, where each hop is
a real escalation primitive (see edge-taxonomy.md). A path is **viable** if the
attacker starting in the foothold can execute every hop with the privileges
accumulated so far.

## What "a remediation" means

Removal of one **removable** edge (a real, actionable RBAC/config change — e.g.
delete a RoleBinding, drop a verb from a Role). Structural edges are never
remediations. The core research question is which single removable edge, once
removed, severs the most viable foothold→target paths.

## Dual-use posture

KubeGraph is defensive: it consumes only clusters the operator owns, emits
remediation rankings (not exploitation steps), and bundles no attack execution
capability. See the proposal's ethics section; usage is bound by the Computer
Misuse Act 1990 and the BCS Code of Conduct.
