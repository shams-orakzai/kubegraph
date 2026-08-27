"""KubeGraph command-line interface.

    kubegraph collect  -o inventory.json      # live cluster -> inventory
    kubegraph build    -i inventory.json      # inventory -> graph stats
    kubegraph paths    -i inventory.json      # attack paths to cluster-admin
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import typer
from rich.console import Console
from rich.table import Table

from kubegraph.graph import paths as pathmod
from kubegraph.graph.builder import build_graph
from kubegraph.models.graph import TARGET_CLUSTER_ADMIN
from kubegraph.models.inventory import Inventory

app = typer.Typer(add_completion=False, help="KubeGraph — Kubernetes attack-path analysis")
console = Console()


def _load(path: Path) -> Inventory:
    return Inventory.model_validate_json(path.read_text())


@app.command()
def collect(
    output: Path = typer.Option("inventory.json", "-o", "--output"),
    context: str = typer.Option(None, "--context", help="kubeconfig context"),
    name: str = typer.Option("collected", "--name", help="cluster label"),
) -> None:
    """Collect a live cluster into a normalized inventory (read-only)."""
    from kubegraph.collector.collector import collect as run_collect

    inv = run_collect(context=context, cluster_name=name)
    output.write_text(inv.model_dump_json(indent=2))
    console.print(f"[green]Collected[/] {len(inv.service_accounts)} SAs, "
                  f"{len(inv.pods)} pods, {len(inv.roles)} roles, "
                  f"{len(inv.bindings)} bindings → [bold]{output}[/]")


@app.command()
def build(inp: Path = typer.Option(..., "-i", "--input")) -> None:
    """Build the attack graph and print summary statistics."""
    g = build_graph(_load(inp))
    removable = sum(1 for *_, d in g.edges(data=True) if d.get("removable"))
    console.print(f"[bold]Graph:[/] {g.number_of_nodes()} nodes, "
                  f"{g.number_of_edges()} edges ({removable} removable)")


@app.command()
def paths(
    inp: Path = typer.Option(..., "-i", "--input"),
    cutoff: int = typer.Option(8, help="max path length for enumeration"),
) -> None:
    """Enumerate attack paths from pod footholds to cluster-admin."""
    g = build_graph(_load(inp))
    reachable = pathmod.reachable_footholds(g)

    table = Table(title="Footholds with a path to cluster-admin",
                  show_lines=False, header_style="bold red")
    table.add_column("Foothold (pod)")
    table.add_column("Shortest", justify="right")
    table.add_column("# paths", justify="right")
    for fh, sp in sorted(reachable.items(), key=lambda kv: kv[1].length):
        n = len(pathmod.all_attack_paths(g, fh, cutoff=cutoff))
        table.add_row(g.nodes[fh]["label"], str(sp.length), str(n))
    console.print(table)

    total_fh = len(pathmod.footholds(g))
    console.print(f"\n[bold]{len(reachable)}/{total_fh}[/] footholds can reach "
                  f"[red]cluster-admin[/].\n")

    for fh, sp in sorted(reachable.items(), key=lambda kv: kv[1].length)[:5]:
        console.print(f"[dim]•[/] {pathmod.render_path(g, sp)}")


if __name__ == "__main__":
    app()
