# KubeGraph

**A graph-theoretic tool for identifying and remediating privilege-escalation paths in Kubernetes.**

KubeGraph models a Kubernetes cluster as a directed **attack graph** — pods, service
accounts, roles, bindings and secrets become nodes; the escalation primitives that
connect them become edges — then computes the routes an attacker could take from a
single low-privilege pod to `cluster-admin`, and **ranks the single fixes that break the
most attack paths**.

Conventional scanners hand defenders a flat list of misconfigurations, each with a
severity label that describes the finding in isolation. KubeGraph reframes those findings
as a connected map of reachability and uses the *structure* of that map to answer the
question that actually matters: **which one change removes the most risk?**

> MSc Cybersecurity capstone (Teesside University, CIS4055). Defensive use only, against
> clusters you own and operate. See `kubegraph_backend/kubegraph_core/docs/threat-model.md`.

---

## What's in this repository

```
kubegraph_project/
├── kubegraph_backend/
│   ├── README.md                     backend overview
│   └── kubegraph_core/               ← the Python package (backend project root)
│       ├── pyproject.toml            install/deps live here
│       ├── docs/                     architecture · edge-taxonomy · threat-model
│       ├── src/kubegraph/            collector · graph · analysis · api · auth
│       └── tests/                    pytest suite + ground-truth fixture
└── kubegraph_frontend/               ← the React + TypeScript single-page app
    ├── package.json
    └── src/                          pages · layout · api client · contexts
```

The system is two independently runnable halves:

| Half | Path | Stack |
|------|------|-------|
| **Backend** (the engine + API) | `kubegraph_backend/kubegraph_core/` | Python 3.12, FastAPI, NetworkX, SQLAlchemy, JWT auth |
| **Frontend** (the dashboard) | `kubegraph_frontend/` | React 18, TypeScript, Vite, Cytoscape.js |

---

## How it works (the pipeline)

```
kubeconfig ─▶ Collector ─▶ Inventory ─▶ Graph builder ─▶ Attack graph
             (read-only)   (normalised   (edge rules)     (NetworkX DiGraph)
                            JSON)                               │
                              ┌─────────────────────────────────┤
                              ▼                                  ▼
                        Analysis engine                    FastAPI backend
                        (paths · choke-points ·            (REST · JWT auth ·
                         blast radius · posture)            snapshot store)
                                                                 │
                                                                 ▼
                                                   React + Cytoscape.js dashboard
```

1. **Collector** reads a cluster's RBAC-relevant objects (read-only; never reads secret
   values) and emits a normalised **inventory**.
2. **Graph builder** turns the inventory into a directed attack graph. Every edge is a
   documented escalation primitive, split into *structural* facts and *removable* grants —
   only removable edges are ever proposed as fixes.
3. **Analysis engine** computes attack paths (foothold → `cluster-admin`), blast radius,
   a transparent exposure score, and the headline feature: a **choke-point remediation
   ranking** — the removable edges whose removal severs the most attack paths, using an
   attacker-to-target restricted **edge-betweenness centrality** as a cheap approximation
   to the exact (but expensive) "recompute reachability per fix" method.
4. **API** exposes everything over REST behind token authentication.
5. **Frontend** visualises the graph, traces paths, and presents role-based dashboards for
   engineers, platform leads, and CISOs.

For the concepts in depth, see the design docs under
`kubegraph_backend/kubegraph_core/docs/`.

---

## Quick start

You need **Python ≥ 3.11** (3.12 recommended) and **Node ≥ 18**. Run the two halves in two
terminals.

### 1 · Backend  (terminal 1)

```bash
cd kubegraph_backend/kubegraph_core
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q                                              # expect: 15 passed
uvicorn kubegraph.api.app:app --reload --port 8000
```

The API is now on **http://localhost:8000**, with interactive docs at **/docs**.

### 2 · Frontend  (terminal 2)

```bash
cd kubegraph_frontend
npm install
npm run dev                                            # http://localhost:5173
```

Open **http://localhost:5173**. On first run, click **Create a workspace**, register
(email + 8-character password, pick a persona), and you'll land on the Overview showing
live data from the bundled demo cluster `synthetic-vulnerable-01`.

> If the UI shows "Can't reach the backend", the API isn't running or is on a different
> host/port — start terminal 1, or set `kubegraph_frontend/.env` →
> `VITE_API_URL=http://localhost:8000` and restart `npm run dev`.

---

## Try it from the command line (no browser)

With the backend venv active:

```bash
# Build the synthetic vulnerable cluster and find every path to cluster-admin
python tests/fixtures/build_fixture.py
kubegraph paths -i tests/fixtures/vulnerable_cluster.json

# Against a real cluster (read-only; uses your current kubeconfig context)
kubegraph collect -o inventory.json
kubegraph paths   -i inventory.json
```

Or drive the API directly:

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"name":"You","email":"you@example.com","password":"supersecret","role":"engineer"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST localhost:8000/demo          -H "Authorization: Bearer $TOKEN"
curl -s        localhost:8000/remediations   -H "Authorization: Bearer $TOKEN"
```

---

## Features

- **Attack-path discovery** — every pod that can reach `cluster-admin`, and the exact route.
- **Choke-point remediation ranking** — the single fixes that sever the most paths.
- **Blast radius** — everything a given identity can reach.
- **Exposure score** — a transparent 0–100 posture heuristic with Low/Medium/High bands.
- **Interactive graph** — Cytoscape.js dark-canvas view with path tracing and fix preview.
- **Role-based dashboards** — engineer / platform / CISO views over the same analysis.
- **Fleet view** — compare exposure across multiple clusters.
- **Import collected clusters from the UI** — drag an `inventory.json` into Settings; no curl required.
- **Authentication** — register / login / JWT, protecting every analysis endpoint.
- **Twelve escalation primitives** modelled as typed edges (see `docs/edge-taxonomy.md`).

---

## Testing

```bash
cd kubegraph_backend/kubegraph_core && source .venv/bin/activate
pytest -q          # 15 tests: RBAC rules, path recovery, choke-points, full API surface
```

```bash
cd kubegraph_frontend
npx tsc --noEmit   # type-check
npm run build      # production build
```

## Evaluation — reproduce the study

The controlled experiment from the dissertation is runnable from real code. A
version-controlled corpus of five synthetic ground-truth clusters (C1-C5) lives
in `src/kubegraph/evaluation/clusters.py`, each constructed to probe one thing;
the harness runs the engine over them and prints detection, the choke-point vs
severity ranking comparison, aggregate stats, rank fidelity, and scalability.

```bash
cd kubegraph_backend/kubegraph_core && source .venv/bin/activate
pip install -e ".[dev]"                         # once, to pick up the evaluation module
python -m kubegraph.evaluation.run              # prints the full results
python -m kubegraph.evaluation.run --json out.json   # also save raw numbers
```

| Cluster | Footholds | Probes |
|---|---|---|
| C1 single-admin | 4 | choke point coincides with a critical finding |
| C2 uneven-admins | 15 | discrimination among equal-severity findings (the divergence) |
| C3 modest-choke-decoys | 7 | a pivotal fix amid higher-noise findings |
| C4 redundant-mesh | 5 | the edge-level limitation, shown empirically |
| C5 deep-chain | 3 | detection on a long multi-hop path |

---

## Configuration

Backend (all optional; sensible dev defaults) — see
`kubegraph_backend/kubegraph_core/.env.example`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `KUBEGRAPH_SECRET_KEY` | `dev-insecure-change-me` | JWT signing secret — **change in production** |
| `KUBEGRAPH_TOKEN_TTL_MIN` | `720` | Access-token lifetime (minutes) |
| `DATABASE_URL` | `sqlite:///./kubegraph.db` | Swap to `postgresql+psycopg://…` for Postgres |

Frontend — `kubegraph_frontend/.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL |

---

## Status & roadmap

The full stack is implemented and tested: collector, graph engine, choke-point analysis,
authenticated API, and the React dashboard (Overview, Attack graph, Remediations, Fleet,
Settings). Known next steps, documented honestly:

- **Object-level remediation ranking** — rank fixes by the underlying RBAC object rather
  than the individual edge, so over-broad grants that fan out into a redundant mesh score
  correctly (the current edge-level limitation).
- **Node-breakout layer** — model container-escape → node → all tokens on that node.
- **Live-cluster validation** and a fully-powered evaluation over a generated cluster
  population.

---

## Responsible use

Attack-path analysis is dual-use. KubeGraph is defensive by construction: it consumes only
clusters you own, reads no secret values, emits remediations rather than exploitation
steps, and bundles no attack tooling. Use it only on systems for which you have explicit
authorisation (Computer Misuse Act 1990; BCS Code of Conduct).
