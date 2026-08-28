"""Cluster posture metrics derived from the attack graph.

The exposure score is a transparent 0-100 heuristic, documented so it can be
justified in the dissertation rather than being a black box:

    score = 100 * (0.75 * reach_ratio + 0.25 * path_density)

where reach_ratio is the fraction of footholds that can reach a high-value
target, and path_density reflects how many distinct escalation paths exist per
reachable foothold (capped). More footholds reaching admin, and more redundant
paths, both push the score up.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from kubegraph.analysis import chokepoint
from kubegraph.graph import paths as pathmod


@dataclass
class Posture:
    score: int
    band: str
    footholds: int
    footholds_reaching: int
    paths: int
    choke_points: int


def _band(score: int) -> str:
    if score < 30:
        return "Low"
    if score < 60:
        return "Medium"
    return "High"


def compute_posture(g: nx.DiGraph, cutoff: int = 6) -> Posture:
    footholds = pathmod.footholds(g)
    reaching = list(pathmod.reachable_footholds(g).keys())
    n_fh, n_reach = len(footholds), len(reaching)
    total_paths = sum(len(pathmod.all_attack_paths(g, fh, cutoff=cutoff)) for fh in reaching)

    reach_ratio = (n_reach / n_fh) if n_fh else 0.0
    density = min(total_paths / (n_reach * 10), 1.0) if n_reach else 0.0
    score = round(min(100, 100 * (0.75 * reach_ratio + 0.25 * density)))

    # A choke point = a single removable edge whose removal cuts *every*
    # currently-reachable foothold.
    choke_points = 0
    if n_reach:
        for r in chokepoint.rank_remediations(g, cutoff=cutoff):
            if r.footholds_cut >= n_reach:
                choke_points += 1
            else:
                break  # ranking is sorted desc, so we can stop early

    return Posture(score=score, band=_band(score), footholds=n_fh,
                   footholds_reaching=n_reach, paths=total_paths,
                   choke_points=choke_points)
