import math
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd

from backend.routing.service import RoutingService


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mediterranean_graph_v3_candidate.pkl"
)

PLACE_MAPPING_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mediterranean_graph_v3_candidate_place_nodes.csv"
)


TEST_ROUTES = [
    (
        "Roma -> Capua",
        423025,
        432754,
    ),
    (
        "Roma -> Constantinopolis",
        423025,
        520998,
    ),
    (
        "Roma -> Alexandria",
        423025,
        727070,
    ),
    (
        "Roma -> Kourion",
        423025,
        707549,
    ),
    (
        "Roma -> Gades",
        423025,
        256177,
    ),
]


print(
    "\n=== GRAPH V3 VALIDATION ==="
)

with open(
    GRAPH_PATH,
    "rb",
) as f:
    graph = pickle.load(
        f
    )

places = pd.read_csv(
    PLACE_MAPPING_PATH
)

service = RoutingService(
    graph_path=GRAPH_PATH,
    place_nodes_path=PLACE_MAPPING_PATH,
)


print(
    f"Nodes: {graph.number_of_nodes():,}"
)

print(
    f"Directed edges: "
    f"{graph.number_of_edges():,}"
)

components = list(
    nx.weakly_connected_components(
        graph
    )
)

components.sort(
    key=len,
    reverse=True,
)

print(
    f"Weak components: {len(components):,}"
)

print(
    f"Largest component: "
    f"{len(components[0]):,} nodes "
    f"({len(components[0]) / graph.number_of_nodes() * 100:.2f}%)"
)

duplicate_ids = int(
    places[
        "pleiades_id"
    ].duplicated().sum()
)

print(
    f"Duplicate Pleiades IDs: "
    f"{duplicate_ids}"
)

if duplicate_ids:
    raise RuntimeError(
        "Duplicate Pleiades IDs found."
    )


place_node_by_id = {
    int(row["pleiades_id"]):
    int(row["graph_node_id"])
    for _, row
    in places.iterrows()
}


print(
    "\n=== ROUTE COMPARISON ==="
)

all_match = True

for (
    label,
    origin_id,
    destination_id,
) in TEST_ROUTES:

    print(
        f"\n{label}"
    )

    result = service.route(
        origin_id,
        destination_id,
    )

    source_node = (
        place_node_by_id[
            origin_id
        ]
    )

    target_node = (
        place_node_by_id[
            destination_id
        ]
    )

    nx_distance = (
        nx.shortest_path_length(
            graph,
            source=source_node,
            target=target_node,
            weight="distance_km",
        )
    )

    custom_distance = float(
        result[
            "distance_km"
        ]
    )

    edge_sum = sum(
        float(
            segment[
                "distance_km"
            ]
        )
        for segment
        in result[
            "segments"
        ]
    )

    matches_networkx = (
        math.isclose(
            custom_distance,
            float(
                nx_distance
            ),
            rel_tol=1e-12,
            abs_tol=1e-9,
        )
    )

    matches_edge_sum = (
        math.isclose(
            custom_distance,
            edge_sum,
            rel_tol=1e-12,
            abs_tol=1e-9,
        )
    )

    all_match = (
        all_match
        and matches_networkx
        and matches_edge_sum
    )

    print(
        f"  Custom Dijkstra: "
        f"{custom_distance:.6f} km"
    )

    print(
        f"  NetworkX:        "
        f"{float(nx_distance):.6f} km"
    )

    print(
        f"  Edge sum:        "
        f"{edge_sum:.6f} km"
    )

    print(
        f"  Nodes / edges:   "
        f"{result['node_count']} / "
        f"{result['edge_count']}"
    )

    print(
        f"  By mode:         "
        f"{result['distance_by_mode_km']}"
    )

    print(
        f"  Matches:         "
        f"NetworkX={matches_networkx}, "
        f"edge_sum={matches_edge_sum}"
    )

    transfers = [
        segment
        for segment
        in result[
            "segments"
        ]
        if segment.get(
            "transport_mode"
        )
        == "transfer"
    ]

    if transfers:

        print(
            "  Transfer segments:"
        )

        for segment in transfers:
            print(
                "    - "
                f"{segment.get('road_name')} "
                f"({segment['distance_km']:.6f} km)"
            )

    else:

        print(
            "  Transfer segments: none"
        )


# Exact Italy regression check.
roma_capua = service.route(
    423025,
    432754,
)

expected_roma_capua = (
    197.5643240404261
)

regression_ok = math.isclose(
    float(
        roma_capua[
            "distance_km"
        ]
    ),
    expected_roma_capua,
    rel_tol=1e-12,
    abs_tol=1e-9,
)


print(
    "\n=== REGRESSION ==="
)

print(
    "Roma -> Capua unchanged: "
    f"{regression_ok}"
)


print(
    "\n=== FINAL RESULT ==="
)

if (
    all_match
    and regression_ok
):
    print(
        "PASS: Graph v3 custom routing matches "
        "NetworkX, returned edge sums are exact, "
        "and the Roma -> Capua regression is preserved."
    )
else:
    print(
        "FAIL: Investigate the mismatches above."
    )

    raise SystemExit(
        1
    )
