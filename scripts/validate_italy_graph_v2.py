import pickle
import random
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import LineString


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_V1_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph.pkl"
)

GRAPH_V2_PATH = (
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
    / "graph_v2_validation_pairs.csv"
)

ROUTE_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "first_real_route_v2_reference.geojson"
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RANDOM_SEED = 490

TARGET_VALIDATION_PAIRS = 20

MAX_PAIR_ATTEMPTS = 1000

DISTANCE_TOLERANCE_KM = 1e-6


IMPORTANT_PLACES = {
    423025: "Roma",
    432754: "Capua",
    433014: "Parthenope/Neapolis",
    432721: "Beneventum/Maleventum",
    442509: "Brundisium/Brentesion",
}


# ---------------------------------------------------------
# Load graphs
# ---------------------------------------------------------

print("\n=== GRAPH V2 VALIDATION ===")


with open(
    GRAPH_V1_PATH,
    "rb",
) as f:
    graph_v1 = pickle.load(f)


with open(
    GRAPH_V2_PATH,
    "rb",
) as f:
    graph_v2 = pickle.load(f)


places = pd.read_csv(
    PLACE_NODES_PATH
)


print(
    f"Week 1 graph: "
    f"{graph_v1.number_of_nodes():,} nodes, "
    f"{graph_v1.number_of_edges():,} directed edges"
)

print(
    f"Graph v2: "
    f"{graph_v2.number_of_nodes():,} nodes, "
    f"{graph_v2.number_of_edges():,} directed edges"
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def coordinate_for_node(
    graph,
    node_id,
):

    attrs = graph.nodes[
        node_id
    ]

    return (
        float(
            attrs["longitude"]
        ),
        float(
            attrs["latitude"]
        ),
    )


def best_edge_between(
    graph,
    source,
    target,
):

    edge_options = graph.get_edge_data(
        source,
        target,
    )


    if not edge_options:
        raise RuntimeError(
            f"No edge from "
            f"{source} to {target}"
        )


    edge_key, attrs = min(
        edge_options.items(),
        key=lambda item:
        float(
            item[1].get(
                "distance_km",
                float("inf"),
            )
        ),
    )


    return edge_key, attrs


# ---------------------------------------------------------
# 1. Original endpoint preservation
# ---------------------------------------------------------

print(
    "\n=== ENDPOINT PRESERVATION ==="
)


v2_endpoints_by_coordinate = {}


for node_id, attrs in (
    graph_v2.nodes(
        data=True
    )
):

    if (
        attrs.get("node_type")
        != "road_endpoint"
    ):
        continue


    coordinate = (
        float(
            attrs["longitude"]
        ),
        float(
            attrs["latitude"]
        ),
    )


    v2_endpoints_by_coordinate[
        coordinate
    ] = node_id


v1_to_v2_node = {}

missing_endpoints = []


for v1_node in graph_v1.nodes:

    coordinate = coordinate_for_node(
        graph_v1,
        v1_node,
    )


    v2_node = (
        v2_endpoints_by_coordinate.get(
            coordinate
        )
    )


    if v2_node is None:

        missing_endpoints.append(
            (
                v1_node,
                coordinate,
            )
        )

    else:

        v1_to_v2_node[
            v1_node
        ] = v2_node


print(
    f"Week 1 endpoints: "
    f"{graph_v1.number_of_nodes():,}"
)

print(
    f"Matched in Graph v2: "
    f"{len(v1_to_v2_node):,}"
)

print(
    f"Missing endpoints: "
    f"{len(missing_endpoints):,}"
)


if missing_endpoints:

    print(
        "\nWARNING: Week 1 endpoints "
        "are missing from Graph v2."
    )

    for item in (
        missing_endpoints[:10]
    ):

        print(
            f"  {item}"
        )


# ---------------------------------------------------------
# 2. Component preservation
# ---------------------------------------------------------

print(
    "\n=== COMPONENT PRESERVATION ==="
)


v1_components = list(
    nx.weakly_connected_components(
        graph_v1
    )
)

v1_components.sort(
    key=len,
    reverse=True,
)


v2_components = list(
    nx.weakly_connected_components(
        graph_v2
    )
)

v2_components.sort(
    key=len,
    reverse=True,
)


v2_component_for_node = {}


for component_id, component in enumerate(
    v2_components
):

    for node_id in component:

        v2_component_for_node[
            node_id
        ] = component_id


component_mapping = {}

component_split_detected = False


for v1_component_id, component in enumerate(
    v1_components
):

    mapped_v2_components = set()


    for v1_node in component:

        v2_node = v1_to_v2_node.get(
            v1_node
        )


        if v2_node is None:
            continue


        mapped_v2_components.add(
            v2_component_for_node[
                v2_node
            ]
        )


    component_mapping[
        v1_component_id
    ] = mapped_v2_components


    if len(mapped_v2_components) != 1:

        component_split_detected = True


for component_id, component in enumerate(
    v1_components
):

    mapped = component_mapping[
        component_id
    ]

    print(
        f"Week 1 component "
        f"{component_id}: "
        f"{len(component):,} old nodes "
        f"-> Graph v2 component(s) "
        f"{sorted(mapped)}"
    )


mapped_component_ids = [
    next(
        iter(mapped)
    )
    for mapped
    in component_mapping.values()
    if len(mapped) == 1
]


component_merge_detected = (
    len(
        set(
            mapped_component_ids
        )
    )
    != len(
        mapped_component_ids
    )
)


print()

print(
    f"Week 1 component count: "
    f"{len(v1_components):,}"
)

print(
    f"Graph v2 component count: "
    f"{len(v2_components):,}"
)

print(
    f"Old component split detected: "
    f"{component_split_detected}"
)

print(
    f"Old component merge detected: "
    f"{component_merge_detected}"
)


# ---------------------------------------------------------
# 3. Shortest-path regression test
#
# Compare distances between original Week 1 endpoint
# coordinates in both versions of the graph.
# ---------------------------------------------------------

print(
    "\n=== SHORTEST-PATH REGRESSION ==="
)


largest_v1_component = (
    v1_components[0]
)


candidate_nodes = list(
    largest_v1_component
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


    source_v1, target_v1 = (
        random.sample(
            candidate_nodes,
            2,
        )
    )


    source_v2 = (
        v1_to_v2_node[
            source_v1
        ]
    )

    target_v2 = (
        v1_to_v2_node[
            target_v1
        ]
    )


    try:

        distance_v1 = (
            nx.shortest_path_length(
                graph_v1,
                source_v1,
                target_v1,
                weight="distance_km",
            )
        )


        distance_v2 = (
            nx.shortest_path_length(
                graph_v2,
                source_v2,
                target_v2,
                weight="distance_km",
            )
        )


    except nx.NetworkXNoPath:

        continue


    difference = abs(
        float(distance_v1)
        - float(distance_v2)
    )


    validation_rows.append(
        {
            "source_v1": source_v1,
            "target_v1": target_v1,
            "source_v2": source_v2,
            "target_v2": target_v2,
            "distance_v1_km": (
                distance_v1
            ),
            "distance_v2_km": (
                distance_v2
            ),
            "absolute_difference_km": (
                difference
            ),
        }
    )


validation_df = pd.DataFrame(
    validation_rows
)


if len(validation_df) > 0:

    max_difference = (
        validation_df[
            "absolute_difference_km"
        ].max()
    )

else:

    max_difference = float(
        "nan"
    )


for index, row in (
    validation_df.iterrows()
):

    print(
        f"Pair {index + 1:02d}: "
        f"{row['distance_v1_km']:.6f} km "
        f"vs "
        f"{row['distance_v2_km']:.6f} km "
        f"| diff = "
        f"{row['absolute_difference_km']:.12f}"
    )


print()

print(
    f"Valid pairs tested: "
    f"{len(validation_df):,}"
)

print(
    f"Maximum distance difference: "
    f"{max_difference:.12f} km"
)


validation_df.to_csv(
    VALIDATION_OUTPUT,
    index=False,
)


# ---------------------------------------------------------
# 4. Place-node validation
# ---------------------------------------------------------

print(
    "\n=== IMPORTANT PLACE NODES ==="
)


missing_graph_nodes = (
    ~places[
        "graph_node_id"
    ]
    .isin(
        graph_v2.nodes
    )
).sum()


print(
    f"Place mappings: "
    f"{len(places):,}"
)

print(
    f"Mappings pointing to missing nodes: "
    f"{missing_graph_nodes:,}"
)


important_rows = {}


for pleiades_id, expected_title in (
    IMPORTANT_PLACES.items()
):

    matches = places[
        places[
            "pleiades_id"
        ]
        == pleiades_id
    ]


    if len(matches) == 0:

        print(
            f"{expected_title}: "
            f"NOT FOUND"
        )

        continue


    row = matches.iloc[0]

    node_id = int(
        row[
            "graph_node_id"
        ]
    )


    component_id = (
        v2_component_for_node[
            node_id
        ]
    )


    important_rows[
        pleiades_id
    ] = row


    print(
        f"{expected_title}:"
    )

    print(
        f"  graph node: "
        f"{node_id}"
    )

    print(
        f"  component: "
        f"{component_id}"
    )

    print(
        f"  road: "
        f"{row['road_name']}"
    )

    print(
        f"  road type: "
        f"{row['road_type']}"
    )

    print(
        f"  distance to network: "
        f"{float(row['distance_to_network_km']):.3f} km"
    )


# ---------------------------------------------------------
# 5. Graph-v2 reference route:
#    Roma -> Capua
# ---------------------------------------------------------

print(
    "\n=== ROMA -> CAPUA GRAPH V2 ROUTE ==="
)


ROMA_ID = 423025

CAPUA_ID = 432754


if (
    ROMA_ID not in important_rows
    or CAPUA_ID not in important_rows
):

    raise RuntimeError(
        "Roma or Capua is missing from "
        "the Graph-v2 place mapping."
    )


roma_node = int(
    important_rows[
        ROMA_ID
    ][
        "graph_node_id"
    ]
)

capua_node = int(
    important_rows[
        CAPUA_ID
    ][
        "graph_node_id"
    ]
)


route_nodes = nx.shortest_path(
    graph_v2,
    roma_node,
    capua_node,
    weight="distance_km",
)


route_distance = (
    nx.shortest_path_length(
        graph_v2,
        roma_node,
        capua_node,
        weight="distance_km",
    )
)


route_rows = []

independent_distance_sum = 0.0


for route_index in range(
    len(route_nodes) - 1
):

    source = route_nodes[
        route_index
    ]

    target = route_nodes[
        route_index + 1
    ]


    edge_key, attrs = (
        best_edge_between(
            graph_v2,
            source,
            target,
        )
    )


    distance_km = float(
        attrs[
            "distance_km"
        ]
    )


    independent_distance_sum += (
        distance_km
    )


    coordinates = attrs.get(
        "coordinates"
    )


    route_rows.append(
        {
            "route_order": (
                route_index + 1
            ),
            "source_node": source,
            "target_node": target,
            "edge_key": edge_key,
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
            "distance_km": (
                distance_km
            ),
            "geometry": LineString(
                coordinates
            ),
        }
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
    f"Route nodes: "
    f"{len(route_nodes):,}"
)

print(
    f"Route edges: "
    f"{len(route_rows):,}"
)

print(
    f"NetworkX route distance: "
    f"{route_distance:.6f} km"
)

print(
    f"Independent edge sum: "
    f"{independent_distance_sum:.6f} km"
)

print(
    f"Difference: "
    f"{abs(route_distance - independent_distance_sum):.12f} km"
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
# Final verdict
# ---------------------------------------------------------

endpoint_ok = (
    len(missing_endpoints)
    == 0
)

components_ok = (
    len(v1_components)
    == len(v2_components)
    and not component_split_detected
    and not component_merge_detected
)

paths_ok = (
    len(validation_df)
    == TARGET_VALIDATION_PAIRS
    and max_difference
    <= DISTANCE_TOLERANCE_KM
)

places_ok = (
    missing_graph_nodes
    == 0
)


print(
    "\n=== VALIDATION SUMMARY ==="
)

print(
    f"Endpoint preservation: "
    f"{'PASS' if endpoint_ok else 'FAIL'}"
)

print(
    f"Component preservation: "
    f"{'PASS' if components_ok else 'FAIL'}"
)

print(
    f"Old shortest-path preservation: "
    f"{'PASS' if paths_ok else 'FAIL'}"
)

print(
    f"Place-node references: "
    f"{'PASS' if places_ok else 'FAIL'}"
)


overall_ok = (
    endpoint_ok
    and components_ok
    and paths_ok
    and places_ok
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