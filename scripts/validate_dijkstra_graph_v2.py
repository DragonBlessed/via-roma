import pickle
import random
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import LineString

from backend.routing.dijkstra import dijkstra_shortest_path


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph_v2.pkl"
)

PLACE_NODES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph_v2_place_nodes.csv"
)

VALIDATION_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "dijkstra_graph_v2_validation_pairs.csv"
)

ROUTE_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "first_real_route_v2_custom.geojson"
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RANDOM_SEED = 490

TARGET_VALIDATION_PAIRS = 20

MAX_PAIR_ATTEMPTS = 2000

DISTANCE_TOLERANCE_KM = 1e-6

ROMA_ID = 423025

CAPUA_ID = 432754


# ---------------------------------------------------------
# Load Graph v2
# ---------------------------------------------------------

print("\n=== CUSTOM DIJKSTRA GRAPH V2 VALIDATION ===")


with open(
    GRAPH_PATH,
    "rb",
) as f:

    graph = pickle.load(f)


places = pd.read_csv(
    PLACE_NODES_PATH
)


print(
    f"Graph v2: "
    f"{graph.number_of_nodes():,} nodes, "
    f"{graph.number_of_edges():,} directed edges"
)

print(
    f"Place mappings: "
    f"{len(places):,}"
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def graph_node_for_place(
    pleiades_id,
):

    matches = places[
        places[
            "pleiades_id"
        ]
        == pleiades_id
    ]


    if len(matches) == 0:

        raise RuntimeError(
            f"Pleiades place "
            f"{pleiades_id} "
            f"is not mapped to Graph v2."
        )


    return int(
        matches.iloc[0][
            "graph_node_id"
        ]
    )


def place_title(
    pleiades_id,
):

    matches = places[
        places[
            "pleiades_id"
        ]
        == pleiades_id
    ]


    if len(matches) == 0:

        return str(
            pleiades_id
        )


    return str(
        matches.iloc[0][
            "title"
        ]
    )


def sum_custom_route_edges(
    graph,
    edges,
):

    total = 0.0


    for source, target, key in edges:

        attrs = graph.edges[
            source,
            target,
            key,
        ]


        total += float(
            attrs[
                "distance_km"
            ]
        )


    return total


# ---------------------------------------------------------
# Largest weakly connected component
#
# We use weak connectivity to identify the main physical
# network, then explicitly check directed reachability for
# each candidate source/destination pair.
# ---------------------------------------------------------

components = list(
    nx.weakly_connected_components(
        graph
    )
)

components.sort(
    key=len,
    reverse=True,
)


largest_component = (
    components[0]
)


print(
    f"Largest weak component: "
    f"{len(largest_component):,} nodes"
)


# ---------------------------------------------------------
# Candidate historical place nodes
# ---------------------------------------------------------

candidate_places = (
    places[
        places[
            "graph_node_id"
        ]
        .isin(
            largest_component
        )
    ]
    .copy()
)


# Multiple Pleiades records may intentionally share one
# Graph-v2 node, so select unique routing nodes here.
candidate_places = (
    candidate_places
    .drop_duplicates(
        subset=[
            "graph_node_id"
        ]
    )
    .reset_index(
        drop=True
    )
)


print(
    f"Unique mapped place nodes "
    f"in largest component: "
    f"{len(candidate_places):,}"
)


# ---------------------------------------------------------
# 1. Deterministic custom-Dijkstra regression test
# ---------------------------------------------------------

print(
    "\n=== CUSTOM DIJKSTRA VS NETWORKX ==="
)


random.seed(
    RANDOM_SEED
)


validation_rows = []

attempts = 0


while (
    len(validation_rows)
    < TARGET_VALIDATION_PAIRS
    and attempts
    < MAX_PAIR_ATTEMPTS
):

    attempts += 1


    source_row, target_row = (
        random.sample(
            list(
                candidate_places.iterrows()
            ),
            2,
        )
    )


    source_row = (
        source_row[1]
    )

    target_row = (
        target_row[1]
    )


    source = int(
        source_row[
            "graph_node_id"
        ]
    )

    target = int(
        target_row[
            "graph_node_id"
        ]
    )


    if source == target:

        continue


    # Weak connectivity does not guarantee that the
    # directed path exists.
    if not nx.has_path(
        graph,
        source,
        target,
    ):

        continue


    nx_distance = (
        nx.shortest_path_length(
            graph,
            source,
            target,
            weight="distance_km",
        )
    )


    result = (
        dijkstra_shortest_path(
            graph,
            source,
            target,
            weight="distance_km",
        )
    )


    custom_distance = float(
        result[
            "distance"
        ]
    )


    edge_sum = (
        sum_custom_route_edges(
            graph,
            result[
                "edges"
            ],
        )
    )


    nx_difference = abs(
        custom_distance
        - float(
            nx_distance
        )
    )


    edge_sum_difference = abs(
        custom_distance
        - edge_sum
    )


    validation_rows.append(
        {
            "source_pleiades_id": int(
                source_row[
                    "pleiades_id"
                ]
            ),
            "source_title": (
                source_row[
                    "title"
                ]
            ),
            "source_node": source,
            "target_pleiades_id": int(
                target_row[
                    "pleiades_id"
                ]
            ),
            "target_title": (
                target_row[
                    "title"
                ]
            ),
            "target_node": target,
            "networkx_distance_km": float(
                nx_distance
            ),
            "custom_distance_km": (
                custom_distance
            ),
            "edge_sum_km": edge_sum,
            "networkx_difference_km": (
                nx_difference
            ),
            "edge_sum_difference_km": (
                edge_sum_difference
            ),
            "route_nodes": len(
                result[
                    "nodes"
                ]
            ),
            "route_edges": len(
                result[
                    "edges"
                ]
            ),
        }
    )


validation_df = pd.DataFrame(
    validation_rows
)


for index, row in (
    validation_df.iterrows()
):

    print(
        f"Pair {index + 1:02d}: "
        f"{row['source_title']} -> "
        f"{row['target_title']}"
    )

    print(
        f"  NetworkX: "
        f"{row['networkx_distance_km']:.6f} km"
    )

    print(
        f"  Custom:   "
        f"{row['custom_distance_km']:.6f} km"
    )

    print(
        f"  Difference: "
        f"{row['networkx_difference_km']:.12f} km"
    )

    print(
        f"  Edge-sum difference: "
        f"{row['edge_sum_difference_km']:.12f} km"
    )


if len(validation_df) > 0:

    max_nx_difference = (
        validation_df[
            "networkx_difference_km"
        ]
        .max()
    )

    max_edge_difference = (
        validation_df[
            "edge_sum_difference_km"
        ]
        .max()
    )

else:

    max_nx_difference = float(
        "inf"
    )

    max_edge_difference = float(
        "inf"
    )


print()

print(
    f"Valid pairs tested: "
    f"{len(validation_df):,}"
)

print(
    f"Maximum NetworkX difference: "
    f"{max_nx_difference:.12f} km"
)

print(
    f"Maximum edge-sum difference: "
    f"{max_edge_difference:.12f} km"
)


validation_df.to_csv(
    VALIDATION_OUTPUT,
    index=False,
)


# ---------------------------------------------------------
# 2. Roma -> Capua reference route
# ---------------------------------------------------------

print(
    "\n=== ROMA -> CAPUA CUSTOM DIJKSTRA ==="
)


roma_node = (
    graph_node_for_place(
        ROMA_ID
    )
)

capua_node = (
    graph_node_for_place(
        CAPUA_ID
    )
)


result = (
    dijkstra_shortest_path(
        graph,
        roma_node,
        capua_node,
        weight="distance_km",
    )
)


custom_distance = float(
    result[
        "distance"
    ]
)


nx_distance = float(
    nx.shortest_path_length(
        graph,
        roma_node,
        capua_node,
        weight="distance_km",
    )
)


edge_sum = (
    sum_custom_route_edges(
        graph,
        result[
            "edges"
        ],
    )
)


print(
    f"Roma node: "
    f"{roma_node}"
)

print(
    f"Capua node: "
    f"{capua_node}"
)

print(
    f"Custom route nodes: "
    f"{len(result['nodes']):,}"
)

print(
    f"Custom route edges: "
    f"{len(result['edges']):,}"
)

print(
    f"Custom Dijkstra distance: "
    f"{custom_distance:.6f} km"
)

print(
    f"NetworkX distance: "
    f"{nx_distance:.6f} km"
)

print(
    f"Independent edge sum: "
    f"{edge_sum:.6f} km"
)

print(
    f"Custom vs NetworkX difference: "
    f"{abs(custom_distance - nx_distance):.12f} km"
)

print(
    f"Custom vs edge-sum difference: "
    f"{abs(custom_distance - edge_sum):.12f} km"
)


# ---------------------------------------------------------
# Export custom-Dijkstra route
# ---------------------------------------------------------

route_rows = []


for route_index, (
    source,
    target,
    key,
) in enumerate(
    result[
        "edges"
    ],
    start=1,
):

    attrs = graph.edges[
        source,
        target,
        key,
    ]


    coordinates = attrs.get(
        "coordinates"
    )


    if not coordinates:

        raise RuntimeError(
            f"Route edge "
            f"{source} -> {target} "
            f"key {key} "
            f"has no geometry."
        )


    route_rows.append(
        {
            "route_order": (
                route_index
            ),
            "source_node": source,
            "target_node": target,
            "edge_key": key,
            "itinere_id": attrs.get(
                "itinere_id"
            ),
            "road_name": attrs.get(
                "road_name"
            ),
            "road_type": attrs.get(
                "road_type"
            ),
            "transport_mode": attrs.get(
                "transport_mode"
            ),
            "distance_km": float(
                attrs[
                    "distance_km"
                ]
            ),
            "geometry": LineString(
                coordinates
            ),
        }
    )


route_gdf = gpd.GeoDataFrame(
    route_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


route_gdf.to_file(
    ROUTE_OUTPUT,
    driver="GeoJSON",
)


print(
    "\nRoute segments:"
)


for row in route_rows:

    print(
        f"{row['route_order']:02d}. "
        f"{row['road_name']} "
        f"({row['distance_km']:.2f} km)"
    )


# ---------------------------------------------------------
# Final validation
# ---------------------------------------------------------

pair_count_ok = (
    len(validation_df)
    == TARGET_VALIDATION_PAIRS
)

networkx_ok = (
    max_nx_difference
    <= DISTANCE_TOLERANCE_KM
)

edge_sum_ok = (
    max_edge_difference
    <= DISTANCE_TOLERANCE_KM
)

roma_capua_ok = (
    abs(
        custom_distance
        - nx_distance
    )
    <= DISTANCE_TOLERANCE_KM
    and abs(
        custom_distance
        - edge_sum
    )
    <= DISTANCE_TOLERANCE_KM
)


print(
    "\n=== VALIDATION SUMMARY ==="
)

print(
    f"20 validation pairs: "
    f"{'PASS' if pair_count_ok else 'FAIL'}"
)

print(
    f"Custom vs NetworkX: "
    f"{'PASS' if networkx_ok else 'FAIL'}"
)

print(
    f"Custom edge reconstruction: "
    f"{'PASS' if edge_sum_ok else 'FAIL'}"
)

print(
    f"Roma -> Capua: "
    f"{'PASS' if roma_capua_ok else 'FAIL'}"
)


overall_ok = (
    pair_count_ok
    and networkx_ok
    and edge_sum_ok
    and roma_capua_ok
)


print()

print(
    "OVERALL: "
    + (
        "PASS"
        if overall_ok
        else "INVESTIGATE"
    )
)


print(
    "\n=== OUTPUT ==="
)

print(
    VALIDATION_OUTPUT
)

print(
    ROUTE_OUTPUT
)