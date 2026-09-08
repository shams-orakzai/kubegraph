# KubeGraph — Frontend

The KubeGraph dashboard: a React + TypeScript single-page application that visualises the
attack graph, traces escalation paths, ranks remediations, and presents role-based views
over the analysis served by the [backend](../kubegraph_backend/kubegraph_core/).

## Stack

- **React 18 + TypeScript**, built with **Vite**
- **React Router** for routing and route guards
- **Cytoscape.js** (+ dagre layout) for the interactive attack graph
- Plain CSS design system (`src/index.css`) — one set of tokens, cinematic dark canvas for
  the graph view over a light application shell

## Run

Requires **Node ≥ 18**. The backend must be running (default `http://localhost:8000`).

```bash
npm install
npm run dev        # http://localhost:5173
```

Point at a non-default backend by creating `.env`:

```
VITE_API_URL=http://localhost:8000
```

Other scripts:

```bash
npm run build      # type-check (tsc) + production build to dist/
npm run preview    # serve the production build locally
npx tsc --noEmit   # type-check only
```

## First run

You'll hit the **login** screen. Since a fresh backend has no users, choose **Create a
workspace**, register with an email and an 8-character password, and pick a persona. You'll
land on the Overview showing live data from the bundled demo cluster.

## Project structure

```
src/
├── main.tsx                 entry point
├── App.tsx                  router: public auth routes + protected app shell
├── index.css                design system (tokens, shell, graph canvas, components)
├── api/
│   ├── client.ts            typed fetch client; attaches JWT; 401 → auto sign-out
│   └── types.ts             response types mirroring the backend schemas
├── auth/
│   ├── AuthContext.tsx      session state; validates token via /auth/me on boot
│   └── ProtectedRoute.tsx   redirects unauthenticated users to /login
├── cluster/
│   └── ClusterContext.tsx   loads the active cluster + stats; seeds the demo if empty
├── layout/
│   ├── AppShell.tsx         sidebar + top bar + role context (persona, persisted)
│   ├── Sidebar.tsx          navigation + user block
│   └── TopBar.tsx           cluster selector + persona switch
├── graph/
│   └── cyStyle.ts           Cytoscape dark stylesheet + layouts
├── components/
│   └── ExposureDonut.tsx    reusable posture donut
└── pages/
    ├── Login.tsx / Signup.tsx
    ├── Overview.tsx         role-aware; delegates to overview/{Engineer,Platform,Ciso}View
    ├── Graph.tsx            interactive Cytoscape canvas: path tracing, blast radius, cut preview
    ├── Remediations.tsx     ranked fix table; "Preview" jumps to the graph with the fix highlighted
    ├── Fleet.tsx            multi-cluster comparison
    └── Settings.tsx         profile · persona · workspace · connection/session
```

## How the pieces connect

- **`AuthContext`** holds the session. On load it validates any stored token against
  `/auth/me`; a global `kg-unauthorized` event (fired by the API client on a `401`) logs the
  user out automatically.
- **`ClusterContext`** ensures a cluster is loaded (seeding the demo if the workspace is
  empty) and exposes `stats` + a `reload()` used across pages and Settings.
- **`AppShell`** owns the **persona** (engineer / platform / CISO) via a small role context.
  The top bar and the Settings page both change it through `useRoleControl()`, and it's
  persisted to `localStorage` so it survives reloads. Existing pages read it with `useRole()`.
- **`api/client.ts`** is the single place that talks to the backend: it injects the bearer
  token, normalises errors into `ApiError`, and centralises the base URL.

## Notes

- Token storage uses `localStorage` — appropriate for this local/self-hosted tool.
- The graph view uses a dark "focus canvas" inside the otherwise light shell; colour is
  semantic (target = coral, pod = teal, service account = blue, role = amber, secret =
  violet), consistent between the graph and the surrounding UI.
