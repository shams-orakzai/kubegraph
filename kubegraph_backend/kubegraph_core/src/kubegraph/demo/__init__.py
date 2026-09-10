"""Selectable synthetic demo clusters (the dashboard's cluster dropdown).

The catalog exposes a set of deliberately *different* synthetic clusters so the
UI can switch between them and show naturally different graphs, exposure scores
and remediations. It includes the original vulnerable fixture, several
purpose-built scenarios, and the C1-C5 evaluation corpus.
"""

from kubegraph.demo.catalog import CATALOG, DemoCluster, get, items

__all__ = ["CATALOG", "DemoCluster", "get", "items"]
