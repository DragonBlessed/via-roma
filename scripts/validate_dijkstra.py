import pickle
import random
from pathlib import Path

import networkx as nx

from backend.routing.dijkstra import (
    dijkstra_shortest_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph.pkl"
)


# ---------------------------------------------------------
# Load graph
# ---------------------------------------------------------

with open(GRAPH_PATH, "rb") as f:
    graph = pickle.load(f)


print("\n=== DIJKSTRA VALIDATION ===")

print(
    f"Graph nodes: "
    f"{graph.number_of_nodes():,}"
)

print(
    f"Directed edges: "
    f"{graph.number_of_edges():,}"
)


# ---------------------------------------------------------
# Use largest connected component
# ---------------------------------------------------------

components = list(
    nx.weakly_connected_components(graph)
)

largest_component = max(
    components,
    key=len,
)

component_nodes = list(
    largest_component
)


print(
    f"Largest component nodes: "
    f"{len(component_nodes):,}"
)


# ---------------------------------------------------------
# Reproducible random tests
# ---------------------------------------------------------

rng = random.Random(490)

NUMBER_OF_TESTS = 10

passed = 0


for test_number in range(
    1,
    NUMBER_OF_TESTS + 1,
):

    source, target = rng.sample(
        component_nodes,
        2,
    )

    print(
        f"\n--- Test {test_number} ---"
    )

    print(
        f"Source: {source}"
    )

    print(
        f"Target: {target}"
    )


    # -----------------------------------------------------
    # Our implementation
    # -----------------------------------------------------

    ours = dijkstra_shortest_path(
        graph,
        source,
        target,
        weight="distance_km",
    )


    # -----------------------------------------------------
    # NetworkX implementation
    # -----------------------------------------------------

    expected_distance = (
        nx.shortest_path_length(
            graph,
            source,
            target,
            weight="distance_km",
        )
    )


    difference = abs(
        ours["distance"]
        - expected_distance
    )


    print(
        f"Our distance:      "
        f"{ours['distance']:.9f} km"
    )

    print(
        f"NetworkX distance: "
        f"{expected_distance:.9f} km"
    )

    print(
        f"Difference:        "
        f"{difference:.12f}"
    )

    print(
        f"Nodes in our path: "
        f"{len(ours['nodes'])}"
    )

    print(
        f"Edges in our path: "
        f"{len(ours['edges'])}"
    )


    # -----------------------------------------------------
    # Independently sum our returned edge weights
    # -----------------------------------------------------

    reconstructed_distance = 0.0

    for (
        edge_source,
        edge_target,
        edge_key,
    ) in ours["edges"]:

        edge = graph[
            edge_source
        ][
            edge_target
        ][
            edge_key
        ]

        reconstructed_distance += float(
            edge["distance_km"]
        )


    reconstruction_difference = abs(
        reconstructed_distance
        - ours["distance"]
    )


    print(
        f"Reconstructed:     "
        f"{reconstructed_distance:.9f} km"
    )

    print(
        f"Reconstruction diff: "
        f"{reconstruction_difference:.12f}"
    )


    # -----------------------------------------------------
    # Assertions
    # -----------------------------------------------------

    assert difference < 1e-9, (
        "Our Dijkstra distance does not "
        "match NetworkX."
    )

    assert reconstruction_difference < 1e-9, (
        "Returned route edges do not add "
        "up to the reported distance."
    )

    assert ours["nodes"][0] == source

    assert ours["nodes"][-1] == target

    assert (
        len(ours["nodes"])
        == len(ours["edges"]) + 1
    )


    passed += 1

    print("PASS")


# ---------------------------------------------------------
# Final result
# ---------------------------------------------------------

print(
    "\n========================================"
)

print(
    f"All {passed} Dijkstra validation "
    f"tests passed."
)

print(
    "Custom Dijkstra implementation matches "
    "NetworkX."
)

print(
    "========================================"
)