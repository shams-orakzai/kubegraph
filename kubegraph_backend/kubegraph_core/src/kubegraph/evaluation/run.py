"""KubeGraph evaluation harness.

Reproduces the study in the dissertation, live and from real code:

  1. Detection    — coverage + false positives on the C1-C5 ground-truth corpus
  2. Ranking      — choke-point (exact & centrality) vs a severity baseline,
                    measured as exposure eliminated per remediation
  3. Aggregate    — mean AUC + a paired Wilcoxon signed-rank test
  4. Fidelity     — Spearman correlation between the centrality and exact rankings
  5. Scalability  — exact per-edge recompute vs the centrality approximation

Run:  python -m kubegraph.evaluation.run
      python -m kubegraph.evaluation.run --json results.json
"""

from __future__ import annotations

import argparse
import json
import random
import time

import networkx as nx
from rich.console import Console
from rich.table import Table

from kubegraph.analysis import chokepoint
from kubegraph.evaluation import clusters as C
from kubegraph.graph import paths as pathmod
from kubegraph.graph.builder import build_graph

console = Console()
SEV_RUNS = 200          # random tie-break averaging for the severity baseline
random.seed(7)


# ---------- small helpers ----------
def exposure(g: nx.DiGraph) -> int:
    """Number of footholds that can still reach cluster-admin."""
    return len(pathmod.reachable_footholds(g))


def _simulate(g: nx.DiGraph, order: list[str]) -> list[float]:
    """Remove candidate edges one at a time in `order`; return the fraction of
    exposure eliminated after each fix (relative to the starting exposure)."""
    base = exposure(g)
    if base == 0:
        return [0.0] * len(order)
    h = g.copy(); out = []
    for eid in order:
        u, v = eid.split("->")
        if h.has_edge(u, v):
            h.remove_edge(u, v)
        out.append((base - exposure(h)) / base)
    return out


def _auc(curve: list[float]) -> float:
    """Mean fraction eliminated across the applied fixes (1.0 == first fix
    clears everything)."""
    return sum(curve) / len(curve) if curve else 0.0


def _spearman(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return 1.0
    def rank(xs):
        order = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((ra[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((rb[i] - mb) ** 2 for i in range(n)) ** 0.5
    return 1.0 if da == 0 or db == 0 else num / (da * db)


def _wilcoxon_W(diffs: list[float]) -> tuple[float, int]:
    """Signed-rank W over non-zero paired differences (returns W and n_nonzero)."""
    nz = [d for d in diffs if abs(d) > 1e-9]
    if not nz:
        return 0.0, 0
    order = sorted(range(len(nz)), key=lambda i: abs(nz[i]))
    ranks = [0.0] * len(nz)
    for pos, idx in enumerate(order):
        ranks[idx] = pos + 1
    w_pos = sum(ranks[i] for i in range(len(nz)) if nz[i] > 0)
    w_neg = sum(ranks[i] for i in range(len(nz)) if nz[i] < 0)
    return min(w_pos, w_neg), len(nz)


# ---------- 1 & 2: detection + ranking per cluster ----------
def evaluate_cluster(s: C.Scenario) -> dict:
    g = build_graph(s.inv)
    reached = set(pathmod.reachable_footholds(g).keys())

    coverage = len(reached & s.ground_truth) / len(s.ground_truth) if s.ground_truth else 1.0
    false_neg = len(s.ground_truth - reached)
    false_pos = len(reached - s.ground_truth)          # anything reachable we didn't plant
    control_leak = len(reached & s.controls)

    # exact per-candidate impact + centrality
    base = exposure(g)
    cent_map = chokepoint.subset_edge_betweenness(g)
    cands = []
    for eid, sev, label in s.candidates:
        u, v = eid.split("->")
        cut = 0
        if g.has_edge(u, v):
            h = g.copy(); h.remove_edge(u, v)
            cut = base - exposure(h)
        cands.append({"eid": eid, "sev": sev, "label": label,
                      "cut": cut, "cent": round(cent_map.get((u, v), 0.0), 3)})

    # orderings
    exact_order = [c["eid"] for c in sorted(cands, key=lambda c: (c["cut"], c["cent"]), reverse=True)]
    cent_order = [c["eid"] for c in sorted(cands, key=lambda c: (c["cent"], c["cut"]), reverse=True)]

    exact_curve = _simulate(g, exact_order)
    cent_curve = _simulate(g, cent_order)

    # severity baseline: order by severity desc, random tie-break, averaged
    by_sev: list[list[str]] = []
    sev_curves = []
    for _ in range(SEV_RUNS):
        shuffled = cands[:]
        random.shuffle(shuffled)                       # break ties randomly...
        order = [c["eid"] for c in sorted(shuffled, key=lambda c: c["sev"], reverse=True)]  # ...then stable-sort by severity
        sev_curves.append(_simulate(g, order))
    sev_curve = [sum(col) / SEV_RUNS for col in zip(*sev_curves)]
    _ = by_sev

    fidelity = _spearman([c["cut"] for c in cands], [c["cent"] for c in cands])

    return {
        "name": s.name, "purpose": s.purpose,
        "footholds": len(pathmod.footholds(g)), "reached": len(reached),
        "coverage": coverage, "false_neg": false_neg, "false_pos": false_pos,
        "control_leak": control_leak,
        "candidates": cands,
        "k1_exact": exact_curve[0] if exact_curve else 0.0,
        "k1_cent": cent_curve[0] if cent_curve else 0.0,
        "k1_sev": sev_curve[0] if sev_curve else 0.0,
        "auc_exact": _auc(exact_curve), "auc_cent": _auc(cent_curve), "auc_sev": _auc(sev_curve),
        "fidelity": fidelity,
    }


# ---------- 5: scalability ----------
def scalability(sizes=(10, 20, 40, 80, 160, 320)) -> list[dict]:
    rows = []
    for n in sizes:
        g = build_graph(C.build_star(n))
        t0 = time.perf_counter(); chokepoint.rank_remediations(g); t_exact = time.perf_counter() - t0
        t0 = time.perf_counter(); chokepoint.subset_edge_betweenness(g); t_cent = time.perf_counter() - t0
        rows.append({"footholds": n, "nodes": g.number_of_nodes(), "edges": g.number_of_edges(),
                     "exact_s": t_exact, "cent_s": t_cent,
                     "speedup": (t_exact / t_cent) if t_cent else float("inf")})
    return rows


# ---------- reporting ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write raw results to this file")
    ap.add_argument("--no-scale", action="store_true", help="skip the scalability benchmark")
    args = ap.parse_args()

    console.rule("[bold]KubeGraph — evaluation harness")
    results = [evaluate_cluster(s) for s in C.all_scenarios()]

    # 1) detection
    t = Table(title="1 · Detection (ground-truth corpus)", header_style="bold cyan")
    for col in ("Cluster", "Footholds", "Reached", "Coverage", "False neg", "False pos", "Control leak"):
        t.add_column(col)
    for r in results:
        t.add_row(r["name"], str(r["footholds"]), str(r["reached"]),
                  f"{r['coverage']*100:.0f}%", str(r["false_neg"]), str(r["false_pos"]), str(r["control_leak"]))
    console.print(t)

    # 2) ranking
    t = Table(title="2 · Ranking — exposure eliminated (k=1 first fix, AUC over all fixes)", header_style="bold cyan")
    for col in ("Cluster", "k=1 choke", "k=1 severity", "AUC choke", "AUC severity", "Fidelity ρ"):
        t.add_column(col)
    for r in results:
        diverges = abs(r["auc_cent"] - r["auc_sev"]) > 1e-6
        style = "bold red" if diverges else ""
        t.add_row(r["name"], f"{r['k1_cent']:.2f}", f"{r['k1_sev']:.2f}",
                  f"{r['auc_cent']:.3f}", f"{r['auc_sev']:.3f}", f"{r['fidelity']:.3f}", style=style)
    console.print(t)

    # 3) aggregate
    auc_choke = [r["auc_cent"] for r in results]
    auc_sev = [r["auc_sev"] for r in results]
    diffs = [c - s for c, s in zip(auc_choke, auc_sev)]
    W, nnz = _wilcoxon_W(diffs)
    mean_choke, mean_sev = sum(auc_choke) / len(results), sum(auc_sev) / len(results)
    wins = sum(1 for d in diffs if d > 1e-9); ties = sum(1 for d in diffs if abs(d) <= 1e-9)
    console.print(
        f"\n[bold]3 · Aggregate[/]  mean AUC: choke-point [green]{mean_choke:.3f}[/] vs severity {mean_sev:.3f}"
        f"   ·  Wilcoxon W={W:.1f} on {nnz} non-zero diff(s) ({wins} win, {ties} ties)"
        f"   ·  choke-point never worse: {all(d >= -1e-9 for d in diffs)}")
    console.print("[dim]   Small corpus by design → the test speaks to direction & mechanism, not a population effect.[/]")

    # 4) fidelity summary
    fid = min(r["fidelity"] for r in results)
    console.print(f"[bold]4 · Rank fidelity[/]  centrality vs exact: Spearman ρ ≥ [green]{fid:.3f}[/] on every cluster")

    # 5) scalability
    scale = []
    if not args.no_scale:
        scale = scalability()
        t = Table(title="5 · Scalability — exact per-edge recompute vs centrality", header_style="bold cyan")
        for col in ("Footholds", "Nodes", "Edges", "Exact (s)", "Centrality (s)", "Speedup"):
            t.add_column(col)
        for row in scale:
            t.add_row(str(row["footholds"]), str(row["nodes"]), str(row["edges"]),
                      f"{row['exact_s']:.4f}", f"{row['cent_s']:.4f}", f"{row['speedup']:.0f}x")
        console.print(t)

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"clusters": results, "scalability": scale,
                       "aggregate": {"mean_auc_choke": mean_choke, "mean_auc_sev": mean_sev,
                                     "wilcoxon_W": W, "n_nonzero": nnz}}, f, indent=2)
        console.print(f"\n[dim]raw results → {args.json}[/]")


if __name__ == "__main__":
    main()
