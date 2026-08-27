# KubeGraph

**A graph-theoretic tool for identifying and remediating privilege-escalation
paths in Kubernetes.**

KubeGraph models a cluster as a directed attack graph — pods, service accounts,
roles, bindings and secrets as nodes; escalation primitives as edges — then
computes the routes an attacker could take from a low-privilege foothold to
`cluster-admin`, and (from Phase 3) ranks the single fixes that break the most
attack paths via choke-point / centrality analysis.

> MSc Cyber Security dissertation project. Defensive use only, against clusters
> you own and operate. See `docs/threat-model.md`.

## Status

Phases 0–2 complete: collector, attack-graph builder, and path engine, validated
against a synthetic ground-truth cluster. See `docs/architecture.md`.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart (offline, no cluster needed)

```bash
# Build the synthetic vulnerable ground-truth cluster
python tests/fixtures/build_fixture.py

# Find every foothold that can reach cluster-admin
kubegraph paths -i tests/fixtures/vulnerable_cluster.json
```

Example output (all four footholds escalate through one choke point,
`kube-system/deployer`):

```
default/web-frontend ─[USES_SA]→ default/web ─[CAN_CREATE_POD]→
kube-system/deployer ─[GRANTED_ROLE]→ ClusterRole/cluster-admin ─[IS_CLUSTER_ADMIN]→ cluster-admin

prod/audit-agent ─[USES_SA]→ prod/secops ─[CAN_GET_SECRET]→ kube-system/deployer-token
─[TOKEN_FOR]→ kube-system/deployer ─[GRANTED_ROLE]→ ClusterRole/cluster-admin ─[IS_CLUSTER_ADMIN]→ cluster-admin
```

## Against a real cluster (read-only)

```bash
kubegraph collect -o inventory.json          # uses current kubeconfig context
kubegraph paths   -i inventory.json
```

## Backend API

```bash
uvicorn kubegraph.api.app:app --reload      # http://127.0.0.1:8000
# interactive docs at /docs
```

```bash
curl -X POST localhost:8000/demo            # load synthetic vulnerable cluster
curl localhost:8000/remediations?top=5      # ranked choke-point fixes
curl localhost:8000/paths                   # attack paths to cluster-admin
curl localhost:8000/graph                   # Cytoscape.js elements for the UI
```

## Test

```bash
pytest -q
```

## Docs

- `docs/threat-model.md` — attacker model, what a path/remediation means
- `docs/edge-taxonomy.md` — every edge ↔ escalation primitive
- `docs/architecture.md` — pipeline, module map, phase plan
