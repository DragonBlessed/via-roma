import pickle
from collections import Counter
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import LineString, Point


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
    / "italy_places_attached.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

SUMMARY_PATH = (
    OUTPUT_DIR
    / "graph_component_summary.csv"
)

COMPONENT_EDGES_PATH = (
    OUTPUT_DIR
    / "graph_components.geojson"
)

COMPONENT_NODES_PATH = (
    OUTPUT_DIR
    / "graph_component_nodes.geojson"
)


# ---------------------------------------------------------
# Load graph
# ---------------------------------------------------------

with open(GRAPH_PATH, "rb") as f:
    graph = pickle.load(f)


# ---------------------------------------------------------
# Find weakly connected components
#
# Weak connectivity ignores direction, which is what we
# want when analyzing the physical road network.
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


print("\n=== GRAPH COMPONENT ANALYSIS ===")

print(
    f"Total components: "
    f"{len(components):,}"
)


# ---------------------------------------------------------
# Load place attachments
# ---------------------------------------------------------

places = pd.read_csv(
    PLACES_PATH
)


# ---------------------------------------------------------
# Component summary
# ---------------------------------------------------------

summary_rows = []


for component_id, component in enumerate(components):

    subgraph = graph.subgraph(component)

    node_count = (
        subgraph.number_of_nodes()
    )

    directed_edge_count = (
        subgraph.number_of_edges()
    )


    # -----------------------------------------------------
    # Geographic extent
    # -----------------------------------------------------

    longitudes = []
    latitudes = []


    for node_id in component:

        attrs = graph.nodes[node_id]

        longitudes.append(
            float(attrs["longitude"])
        )

        latitudes.append(
            float(attrs["latitude"])
        )


    min_lon = min(longitudes)
    max_lon = max(longitudes)

    min_lat = min(latitudes)
    max_lat = max(latitudes)


    # -----------------------------------------------------
    # Physical Itiner-e segments
    #
    # The current graph usually contains two directed
    # edges for each physical segment, so count the
    # Itiner-e IDs rather than dividing by two.
    # -----------------------------------------------------

    itinere_ids = set()

    road_type_by_segment = {}

    road_names = []


    for _, _, _, attrs in subgraph.edges(
        keys=True,
        data=True,
    ):

        itinere_id = attrs.get(
            "itinere_id"
        )

        if itinere_id is not None:

            itinere_ids.add(
                itinere_id
            )

            road_type = attrs.get(
                "road_type"
            )

            if (
                itinere_id
                not in road_type_by_segment
            ):
                road_type_by_segment[
                    itinere_id
                ] = road_type


        road_name = attrs.get(
            "road_name"
        )

        if (
            road_name
            and road_name not in road_names
        ):
            road_names.append(
                road_name
            )


    road_types = Counter(
        road_type
        for road_type
        in road_type_by_segment.values()
        if road_type
    )


    # -----------------------------------------------------
    # Places attached to this component
    # -----------------------------------------------------

    component_places = places[
        places["component_id"]
        == component_id
    ]


    place_count = len(
        component_places
    )


    automatic_places = (
        component_places[
            component_places[
                "attachment_status"
            ]
            == "automatic"
        ]
    )


    sample_places = (
        component_places
        .sort_values(
            "snap_distance_km"
        )[
            [
                "title",
                "snap_distance_km",
            ]
        ]
        .head(12)
    )


    top_road_types = ", ".join(
        f"{road_type}: {count}"
        for road_type, count
        in road_types.most_common(5)
    )


    summary_rows.append(
        {
            "component_id": component_id,
            "nodes": node_count,
            "directed_edges": directed_edge_count,
            "unique_itinere_segments": len(
                itinere_ids
            ),
            "attached_places": place_count,
            "automatic_places": len(
                automatic_places
            ),
            "min_longitude": min_lon,
            "max_longitude": max_lon,
            "min_latitude": min_lat,
            "max_latitude": max_lat,
            "top_transport_types": (
                top_road_types
            ),
            "sample_roads": "; ".join(
                road_names[:10]
            ),
        }
    )


    # -----------------------------------------------------
    # Console output
    # -----------------------------------------------------

    print(
        f"\n--- COMPONENT "
        f"{component_id} ---"
    )

    print(
        f"Nodes: "
        f"{node_count:,}"
    )

    print(
        f"Directed edges: "
        f"{directed_edge_count:,}"
    )

    print(
        f"Unique Itiner-e segments: "
        f"{len(itinere_ids):,}"
    )

    print(
        f"Attached places: "
        f"{place_count:,}"
    )

    print(
        f"Automatic place attachments: "
        f"{len(automatic_places):,}"
    )


    print("\nGeographic extent:")

    print(
        f"  Longitude: "
        f"{min_lon:.4f} -> "
        f"{max_lon:.4f}"
    )

    print(
        f"  Latitude:  "
        f"{min_lat:.4f} -> "
        f"{max_lat:.4f}"
    )


    print("\nTransport types:")

    for road_type, count in (
        road_types.most_common(5)
    ):

        print(
            f"  {road_type}: "
            f"{count:,}"
        )


    print("\nClosest attached places:")

    if len(sample_places) == 0:

        print(
            "  No attached places."
        )

    else:

        for _, row in (
            sample_places.iterrows()
        ):

            print(
                f"  - "
                f"{row['title']} "
                f"("
                f"{row['snap_distance_km']:.2f}"
                f" km)"
            )


    print("\nSample roads:")

    for road_name in road_names[:10]:

        print(
            f"  - {road_name}"
        )


# ---------------------------------------------------------
# Save summary CSV
# ---------------------------------------------------------

summary = pd.DataFrame(
    summary_rows
)

summary.to_csv(
    SUMMARY_PATH,
    index=False,
)


# ---------------------------------------------------------
# Export nodes
# ---------------------------------------------------------

node_rows = []


for node_id, attrs in graph.nodes(
    data=True
):

    component_id = (
        node_component[node_id]
    )

    node_rows.append(
        {
            "node_id": node_id,
            "component_id": component_id,
            "component_size": len(
                components[
                    component_id
                ]
            ),
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
    COMPONENT_NODES_PATH,
    driver="GeoJSON",
)


# ---------------------------------------------------------
# Export physical road segments
#
# Only one copy of each Itiner-e segment is written.
# ---------------------------------------------------------

edge_rows = []

seen_itinere_ids = set()


for source, target, key, attrs in (
    graph.edges(
        keys=True,
        data=True,
    )
):

    itinere_id = attrs.get(
        "itinere_id"
    )


    if itinere_id in seen_itinere_ids:
        continue


    seen_itinere_ids.add(
        itinere_id
    )


    coordinates = attrs.get(
        "coordinates"
    )

    if not coordinates:
        continue


    component_id = (
        node_component[source]
    )


    edge_rows.append(
        {
            "component_id": component_id,
            "component_size": len(
                components[
                    component_id
                ]
            ),
            "itinere_id": itinere_id,
            "road_name": attrs.get(
                "road_name"
            ),
            "road_type": attrs.get(
                "road_type"
            ),
            "distance_km": attrs.get(
                "distance_km"
            ),
            "certainty": attrs.get(
                "certainty"
            ),
            "geometry": LineString(
                coordinates
            ),
        }
    )


edges_gdf = gpd.GeoDataFrame(
    edge_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


edges_gdf.to_file(
    COMPONENT_EDGES_PATH,
    driver="GeoJSON",
)


# ---------------------------------------------------------
# Final output
# ---------------------------------------------------------

print("\n=== OUTPUT ===")

print(
    SUMMARY_PATH
)

print(
    COMPONENT_EDGES_PATH
)

print(
    COMPONENT_NODES_PATH
)

print(
    "\nComponent analysis complete."
)