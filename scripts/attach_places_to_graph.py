import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph.pkl"
)

PLACES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_routing_places.geojson"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_places_attached.csv"
)


# ---------------------------------------------------------
# Load graph
# ---------------------------------------------------------

with open(GRAPH_PATH, "rb") as f:
    graph = pickle.load(f)


# ---------------------------------------------------------
# Identify weakly connected components
# ---------------------------------------------------------

components = list(
    nx.weakly_connected_components(graph)
)

components.sort(
    key=len,
    reverse=True,
)


node_component = {}

for component_id, component in enumerate(components):

    for node_id in component:
        node_component[node_id] = component_id


print("\n=== GRAPH COMPONENTS ===")
print(f"Components: {len(components):,}")

if components:
    print(
        f"Largest component: "
        f"{len(components[0]):,} nodes"
    )


# ---------------------------------------------------------
# Load Pleiades places
# ---------------------------------------------------------

places = gpd.read_file(PLACES_PATH)


# ---------------------------------------------------------
# Convert graph nodes to geographic points
# ---------------------------------------------------------

node_rows = []

for node_id, attrs in graph.nodes(data=True):

    node_rows.append(
        {
            "graph_node_id": node_id,
            "component_id": node_component[node_id],
            "is_largest_component": (
                node_component[node_id] == 0
            ),
            "node_longitude": attrs["longitude"],
            "node_latitude": attrs["latitude"],
            "geometry": Point(
                attrs["longitude"],
                attrs["latitude"],
            ),
        }
    )


nodes = gpd.GeoDataFrame(
    node_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


# ---------------------------------------------------------
# Project to meters
# ---------------------------------------------------------

places_metric = places.to_crs("EPSG:3035")
nodes_metric = nodes.to_crs("EPSG:3035")


# ---------------------------------------------------------
# Attach each place to nearest graph node
# ---------------------------------------------------------

attached = gpd.sjoin_nearest(
    places_metric,
    nodes_metric,
    how="left",
    distance_col="snap_distance_m",
)


attached["snap_distance_km"] = (
    attached["snap_distance_m"] / 1000
)


# Equal-distance nodes may duplicate rows.
attached = (
    attached
    .sort_values("snap_distance_km")
    .drop_duplicates(subset="id")
    .copy()
)


# ---------------------------------------------------------
# Classify attachment confidence
# ---------------------------------------------------------

def attachment_status(distance):

    if distance <= 2:
        return "automatic"

    if distance <= 5:
        return "review"

    return "far"


attached["attachment_status"] = (
    attached["snap_distance_km"]
    .apply(attachment_status)
)


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------

print("\n=== PLACE ATTACHMENT ===")

print(
    f"Places processed: "
    f"{len(attached):,}"
)


print("\n=== ATTACHMENT STATUS ===")

print(
    attached[
        "attachment_status"
    ].value_counts()
)


print("\n=== COMPONENT DISTRIBUTION ===")

print(
    attached[
        "component_id"
    ].value_counts()
    .sort_index()
    .head(20)
)


largest_count = (
    attached["is_largest_component"]
    .sum()
)

print(
    f"\nPlaces attached to largest component: "
    f"{largest_count:,} "
    f"({largest_count / len(attached) * 100:.2f}%)"
)


print("\n=== SNAP DISTANCE STATISTICS ===")

print(
    attached[
        "snap_distance_km"
    ].describe()
)


# ---------------------------------------------------------
# Look specifically for useful test cities
# ---------------------------------------------------------

test_names = [
    "Roma",
    "Capua",
    "Neapolis",
    "Beneventum",
    "Brundisium",
]


print("\n=== POSSIBLE TEST CITIES ===")

for name in test_names:

    matches = attached[
        attached["title"]
        .str.contains(
            name,
            case=False,
            na=False,
            regex=False,
        )
    ]

    if len(matches) == 0:
        print(f"{name}: NOT FOUND")
        continue

    print(
        matches[
            [
                "id",
                "title",
                "graph_node_id",
                "component_id",
                "snap_distance_km",
                "attachment_status",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

output_columns = [
    "id",
    "title",
    "routing_types",
    "graph_node_id",
    "component_id",
    "is_largest_component",
    "node_longitude",
    "node_latitude",
    "snap_distance_km",
    "attachment_status",
]


attached[
    output_columns
].to_csv(
    OUTPUT_PATH,
    index=False,
)


print("\nSaved:")
print(OUTPUT_PATH)