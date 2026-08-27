# kubegraph
KubeGraph is a full-stack tool that models a Kubernetes cluster as a directed graph, and computes the routes an attacker could take from a low-privilege foothold to cluster-admin, then ranks the single fixes that break the most attack paths.

## kubegraph_backend 
Kubegraph_backend is the backend part of the whole kubegraph application. It consists of all the API's, Algorithms and technical analysis of the K8s cluster. It is actually the brain of the whole system.
