import pickle
from pathlib import Path

import networkx as nx


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph.pkl"
)


with open(GRAPH_PATH, "rb") as f:
    graph = pickle.load(f)


print("\n=== GRAPH VALIDATION ===")

print(f"Nodes: {graph.number_of_nodes():,}")
print(f"Directed edges: {graph.number_of_edges():,}")


# Weak components ignore edge direction while testing
# whether the physical road network is connected.
components = list(
    nx.weakly_connected_components(graph)
)

components.sort(
    key=len,
    reverse=True,
)


print(
    f"Weakly connected components: "
    f"{len(components):,}"
)


if components:

    largest = components[0]

    percent = (
        len(largest)
        / graph.number_of_nodes()
        * 100
    )

    print(
        f"Largest component nodes: "
        f"{len(largest):,}"
    )

    print(
        f"Largest component percentage: "
        f"{percent:.2f}%"
    )


print("\n=== TOP 10 COMPONENT SIZES ===")

for index, component in enumerate(
    components[:10],
    start=1,
):
    print(
        f"{index:2}. "
        f"{len(component):,} nodes"
    )


# Degree diagnostics
undirected = graph.to_undirected()

degrees = [
    degree
    for _, degree
    in undirected.degree()
]


if degrees:

    print("\n=== DEGREE STATISTICS ===")

    print(
        f"Minimum degree: "
        f"{min(degrees)}"
    )

    print(
        f"Maximum degree: "
        f"{max(degrees)}"
    )

    print(
        f"Average degree: "
        f"{sum(degrees) / len(degrees):.2f}"
    )

    dead_ends = sum(
        1
        for degree in degrees
        if degree == 1
    )

    print(
        f"Degree-1 nodes: "
        f"{dead_ends:,}"
    )


print("\n=== GRAPH VALIDATION COMPLETE ===")