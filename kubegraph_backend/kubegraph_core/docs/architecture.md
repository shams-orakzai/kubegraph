# KubeGraph Architecture

```
kubeconfig ──▶ Collector ──▶ Inventory (JSON) ──▶ Graph Builder ──▶ Attack graph
                (read-only)     (normalized)         (edge rules)     (NetworkX)
                                                                          │
                                              ┌───────────────────────────┤
                                              ▼                           ▼
                                        Path / choke-point        FastAPI backend
                                        engine (Phase 3)          + PostgreSQL (Phase 4)
                                                                          │
                                                                          ▼
                                                          React + Cytoscape.js UI (Phase 5)
```

## Design principles

1. **Inventory is the seam.** The collector's only job is
   live-cluster → `Inventory`. Everything downstream consumes `Inventory`, so
   the entire engine is testable offline against synthetic inventories — no
   cluster required for development or CI.
2. **Compute in memory, persist results.** Graph algorithms (paths, centrality)
   run in NetworkX (→ rustworkx for scale). PostgreSQL stores inventory
   snapshots and analysis outputs, not the live graph. This resolves the
   "Postgres is not a graph engine" concern while honouring the proposed stack.
3. **Rules are data.** Each edge type is one small, independently testable
   derivation rule, so detection coverage and false-positive behaviour can be
   reasoned about per primitive.
4. **Removable vs structural.** Baked into every edge, so remediation ranking
   only ever proposes real, actionable changes.

## Module map

| Module | Responsibility |
|---|---|
| `models/inventory.py` | Normalized cluster snapshot |
| `models/graph.py` | Node/edge taxonomy, id helpers, removable/structural split |
| `graph/rbac.py` | RBAC matching, effective-grant resolution, admin detection |
| `graph/builder.py` | Inventory → attack graph (edge rules) |
| `graph/paths.py` | Reachability + path enumeration |
| `analysis/chokepoint.py` | Remediation ranking: exact per-edge impact + centrality approximation; blast radius |
| `api/app.py` | FastAPI backend (stats, graph, paths, remediations, blast-radius) |
| `api/schemas.py` | Response contract consumed by the React frontend |
| `api/serialize.py` | Graph → Cytoscape.js elements |
| `api/store.py` | Snapshot store (in-memory; Postgres layer next) |
| `collector/collector.py` | Live cluster → Inventory (kubernetes client) |
| `cli.py` | `collect` / `build` / `paths` commands |

## Phase status

- [x] Phase 0 — scaffold, threat model, edge taxonomy
- [x] Phase 1 — collector
- [x] Phase 2 — graph builder + path engine + synthetic ground-truth fixture
- [~] Phase 3 — choke-point engine DONE (exact + centrality); eval harness + object-level remediation + synthetic generator pending
- [~] Phase 4 — FastAPI backend DONE; PostgreSQL persistence layer pending
- [ ] Phase 5 — React + Cytoscape.js dashboard
- [ ] Phase 6 — containerisation + kind/EKS deploy
- [ ] Phase 7–8 — ground-truth corpus, experiments, results

## Known analytical refinement (surfaced by the engine itself)

Remediation ranking is currently *edge-level*. The demo shows why *object-level*
grouping is the necessary next step: removing a single `CAN_CREATE_POD` edge cuts
0 footholds, because "create pods cluster-wide" produces a redundant mesh of
edges (compromise one SA, hop through any other). The correct single fix is
removing the underlying **Role rule** (which deletes all those edges at once).
Edge provenance → object-level remediation is the immediate Phase 3 refinement.
