import json
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx

from shapely.geometry import LineString, Point, box


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ITINERE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "itinere"
    / "route-segments-all-1788681284419.ndjson"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_PATH = OUTPUT_DIR / "italy_graph.pkl"
NODES_PATH = OUTPUT_DIR / "italy_graph_nodes.geojson"
EDGES_PATH = OUTPUT_DIR / "italy_graph_edges.geojson"


# Development region used earlier.
ITALY_BBOX = box(
    6.0,
    36.0,
    19.0,
    47.5,
)


# Directed multigraph:
#
# - directed because Itiner-e contains passability information
# - multigraph because more than one road may connect the same nodes
graph = nx.MultiDiGraph()


# Exact coordinate -> integer graph node ID
coordinate_to_node = {}

next_node_id = 0


def get_or_create_node(coordinate):
    global next_node_id

    # GeoJSON coordinates are longitude, latitude.
    lon = float(coordinate[0])
    lat = float(coordinate[1])

    key = (lon, lat)

    if key in coordinate_to_node:
        return coordinate_to_node[key]

    node_id = next_node_id
    next_node_id += 1

    coordinate_to_node[key] = node_id

    graph.add_node(
        node_id,
        longitude=lon,
        latitude=lat,
    )

    return node_id


segments_loaded = 0
segments_skipped = 0
directed_edges_added = 0


with open(
    ITINERE_PATH,
    "r",
    encoding="utf-8",
) as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        record = json.loads(line)

        geometry_data = record.get("geometry")

        if not geometry_data:
            continue

        if geometry_data.get("type") != "LineString":
            segments_skipped += 1
            continue

        coordinates = geometry_data.get("coordinates", [])

        if len(coordinates) < 2:
            segments_skipped += 1
            continue

        geometry = LineString(coordinates)

        if not geometry.intersects(ITALY_BBOX):
            continue

        props = record.get("properties", {})

        start_coordinate = coordinates[0]
        end_coordinate = coordinates[-1]

        start_node = get_or_create_node(start_coordinate)
        end_node = get_or_create_node(end_coordinate)

        distance_km = props.get("_lengthInKm")

        # If distance is unexpectedly missing, skip the edge.
        if distance_km is None:
            segments_skipped += 1
            continue

        passability = props.get("passability") or {}

        # Treat only explicit 0 as impassable.
        # Missing/unknown values remain usable for this first graph.
        forward_allowed = (
            passability.get("forward", 1) != 0
        )

        backward_allowed = (
            passability.get("backward", 1) != 0
        )

        base_attributes = {
            "itinere_id": record.get("id"),
            "road_name": props.get("name"),
            "road_type": props.get("type"),
            "distance_km": float(distance_km),
            "certainty": props.get("segmentCertainty"),
            "lower_date": props.get("lowerDate"),
            "upper_date": props.get("upperDate"),
            "construction_period": props.get(
                "constructionPeriod"
            ),
            "bibliography": props.get("bibliography"),
        }

        if forward_allowed:

            graph.add_edge(
                start_node,
                end_node,
                **base_attributes,
                direction="forward",
                coordinates=coordinates,
            )

            directed_edges_added += 1

        if backward_allowed:

            graph.add_edge(
                end_node,
                start_node,
                **base_attributes,
                direction="backward",
                coordinates=list(reversed(coordinates)),
            )

            directed_edges_added += 1

        segments_loaded += 1


print("\n=== GRAPH CONSTRUCTION ===")

print(f"Road segments loaded: {segments_loaded:,}")
print(f"Road segments skipped: {segments_skipped:,}")

print(f"Graph nodes: {graph.number_of_nodes():,}")
print(
    f"Directed graph edges: "
    f"{graph.number_of_edges():,}"
)


# ---------------------------------------------------------
# Save graph using Python pickle
# ---------------------------------------------------------

with open(GRAPH_PATH, "wb") as f:
    pickle.dump(graph, f)


# ---------------------------------------------------------
# Export nodes for QGIS
# ---------------------------------------------------------

node_rows = []

for node_id, attrs in graph.nodes(data=True):

    node_rows.append(
        {
            "node_id": node_id,
            "geometry": Point(
                attrs["longitude"],
                attrs["latitude"],
            ),
        }
    )


nodes_gdf = gpd.GeoDataFrame(
    node_rows,
    geometry="geometry",
    crs="EPSG:4326",
)

nodes_gdf.to_file(
    NODES_PATH,
    driver="GeoJSON",
)


# ---------------------------------------------------------
# Export edges for QGIS
# ---------------------------------------------------------

edge_rows = []

for source, target, key, attrs in graph.edges(
    keys=True,
    data=True,
):

    edge_rows.append(
        {
            "source": source,
            "target": target,
            "edge_key": key,
            "itinere_id": attrs.get("itinere_id"),
            "road_name": attrs.get("road_name"),
            "road_type": attrs.get("road_type"),
            "distance_km": attrs.get("distance_km"),
            "certainty": attrs.get("certainty"),
            "direction": attrs.get("direction"),
            "geometry": LineString(
                attrs["coordinates"]
            ),
        }
    )


edges_gdf = gpd.GeoDataFrame(
    edge_rows,
    geometry="geometry",
    crs="EPSG:4326",
)

edges_gdf.to_file(
    EDGES_PATH,
    driver="GeoJSON",
)


print("\n=== OUTPUT ===")

print(GRAPH_PATH)
print(NODES_PATH)
print(EDGES_PATH)