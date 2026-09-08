# KubeGraph — Backend

The engine and API behind KubeGraph — "the brain of the system". It collects a cluster's
RBAC state, builds a directed attack graph, computes escalation paths and choke-point
remediations, and serves everything over an authenticated REST API.

The installable Python package lives in **[`kubegraph_core/`](./kubegraph_core/)** — that
is the backend project root (it holds `pyproject.toml`). Run all backend commands from
there.

## What it does

- **Collector** — reads RBAC-relevant objects from a cluster (read-only; never reads secret
  values) into a normalised inventory.
- **Graph builder** — turns an inventory into a NetworkX attack graph; every edge is a
  documented escalation primitive, split into *structural* (unchangeable) and *removable*
  (actionable) edges.
- **Analysis engine** — attack paths, blast radius, a transparent exposure score, and the
  headline **choke-point remediation ranking** (exact per-edge impact + a cheap
  attacker-to-target edge-betweenness approximation).
- **API** — FastAPI app exposing the pipeline over REST, with JWT authentication protecting
  the analysis routes.

## Run

```bash
cd kubegraph_core
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                       # 15 tests
uvicorn kubegraph.api.app:app --reload --port 8000
```

API on http://localhost:8000, interactive docs at **/docs**.

## CLI

```bash
python tests/fixtures/build_fixture.py          # build the synthetic demo cluster
kubegraph paths   -i tests/fixtures/vulnerable_cluster.json
kubegraph collect -o inventory.json             # real cluster, read-only (kubeconfig)
kubegraph build   -i inventory.json
```

## Principal API endpoints

| Method & path | Auth | Returns |
|---|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | public / bearer | registration, JWT, current user |
| `POST /demo` | bearer | load the bundled synthetic cluster |
| `POST /inventory` | bearer | load a supplied inventory JSON |
| `GET /stats` | bearer | posture score, band, path & choke-point counts |
| `GET /graph` | bearer | Cytoscape-serialised attack graph |
| `GET /paths`, `GET /paths/detail` | bearer | footholds reaching the target; full path detail |
| `GET /remediations` | bearer | ranked choke-point fixes |
| `GET /blast-radius` | bearer | everything a node can reach |
| `GET /snapshots`, `GET /fleet` | bearer | snapshot list; multi-cluster posture summary |
| `GET /` | public | service name + version (health) |

## Configuration

Copy `kubegraph_core/.env.example` and adjust as needed:

| Variable | Default | Purpose |
|---|---|---|
| `KUBEGRAPH_SECRET_KEY` | `dev-insecure-change-me` | JWT signing secret — **change in production** |
| `KUBEGRAPH_TOKEN_TTL_MIN` | `720` | Access-token lifetime (minutes) |
| `DATABASE_URL` | `sqlite:///./kubegraph.db` | Swap to PostgreSQL with `postgresql+psycopg://...` |

## Package layout

```
kubegraph_core/src/kubegraph/
├── collector/     live cluster -> inventory (read-only)
├── models/        inventory, graph metamodel, user (SQLAlchemy)
├── graph/         rbac resolver, builder, path engine
├── analysis/      chokepoint (remediation ranking), posture (exposure score)
├── api/           FastAPI app, schemas, serialisation, snapshot store
├── auth/          JWT security, schemas, dependencies, router
├── db.py          SQLAlchemy engine/session (SQLite -> PostgreSQL)
└── cli.py         collect / build / paths
```

For the design in depth, see [`docs/`](./kubegraph_core/docs/): `architecture.md`,
`edge-taxonomy.md`, `threat-model.md`.
