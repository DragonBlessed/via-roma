import ast
import json
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd

from pyproj import Transformer
from shapely.geometry import (
    LineString,
    Point,
    box,
)
from shapely.ops import (
    substring,
    transform,
)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ITINERE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "itinere"
    / "route-segments-all-1788681284419.ndjson"
)

PROJECTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "place_network_projections.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

GRAPH_OUTPUT = (
    OUTPUT_DIR
    / "italy_graph_v2.pkl"
)

NODES_OUTPUT = (
    OUTPUT_DIR
    / "italy_graph_v2_nodes.geojson"
)

EDGES_OUTPUT = (
    OUTPUT_DIR
    / "italy_graph_v2_edges.geojson"
)

PLACE_NODE_OUTPUT = (
    OUTPUT_DIR
    / "italy_graph_v2_place_nodes.csv"
)


# ---------------------------------------------------------
# Development region
#
# This is the same rectangular development region used in
# Week 1. It is broader than the modern boundary of Italy.
# ---------------------------------------------------------

DEVELOPMENT_BBOX = box(
    6.0,
    36.0,
    19.0,
    47.5,
)


# ---------------------------------------------------------
# Graph-v2 configuration
# ---------------------------------------------------------

# Only places <= 2 km from the network are inserted
# automatically during this stage.
ACCEPTED_PROJECTION_STATUS = {
    "automatic",
}


# If two projected places occur within this distance along
# the SAME Itiner-e segment, they will use one graph node.
#
# This avoids tiny graph edges when multiple Pleiades
# records describe nearly the same location.
SPLIT_CLUSTER_TOLERANCE_M = 10.0


# A projection this close to an existing road endpoint will
# reuse the endpoint instead of creating a new split node.
ENDPOINT_TOLERANCE_M = 10.0


MARITIME_PLACE_TYPES = {
    "port",
    "harbor",
    "anchorage",
}


# ---------------------------------------------------------
# Coordinate transformers
# ---------------------------------------------------------

to_metric = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:3035",
    always_xy=True,
)

to_wgs84 = Transformer.from_crs(
    "EPSG:3035",
    "EPSG:4326",
    always_xy=True,
)


def wgs_to_metric(geometry):

    return transform(
        to_metric.transform,
        geometry,
    )


def metric_to_wgs(geometry):

    return transform(
        to_wgs84.transform,
        geometry,
    )


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def parse_routing_types(value):
    """
    Convert the routing_types CSV representation back into
    a Python set.

    Example:
        "['port', 'settlement']"
    """

    if pd.isna(value):
        return set()

    if isinstance(value, list):
        return set(value)

    try:
        parsed = ast.literal_eval(
            str(value)
        )

        if isinstance(parsed, list):
            return set(parsed)

    except (
        ValueError,
        SyntaxError,
    ):
        pass

    return {
        str(value)
    }


def transport_mode(road_type):

    if road_type == "Sea Lane":
        return "sea"

    if road_type == "River":
        return "river"

    return "road"


# ---------------------------------------------------------
# Load projections
# ---------------------------------------------------------

projections = pd.read_csv(
    PROJECTIONS_PATH
)


print("\n=== GRAPH V2 CONSTRUCTION ===")

print(
    f"Projection records loaded: "
    f"{len(projections):,}"
)


projections[
    "routing_type_set"
] = (
    projections[
        "routing_types"
    ]
    .apply(
        parse_routing_types
    )
)


# ---------------------------------------------------------
# Initial acceptance filter
# ---------------------------------------------------------

accepted = projections[
    projections[
        "projection_status"
    ]
    .isin(
        ACCEPTED_PROJECTION_STATUS
    )
].copy()


print(
    f"Automatic projections: "
    f"{len(accepted):,}"
)


# ---------------------------------------------------------
# Sea-lane safeguard
#
# Generic settlements should not automatically become
# sea-lane transfer nodes.
# ---------------------------------------------------------

sea_lane_mask = (
    accepted[
        "road_type"
    ]
    == "Sea Lane"
)


maritime_place_mask = (
    accepted[
        "routing_type_set"
    ]
    .apply(
        lambda place_types:
        bool(
            place_types
            & MARITIME_PLACE_TYPES
        )
    )
)


excluded_sea_lane = accepted[
    sea_lane_mask
    & ~maritime_place_mask
].copy()


accepted = accepted[
    ~(
        sea_lane_mask
        & ~maritime_place_mask
    )
].copy()


print(
    f"Sea-lane projections excluded "
    f"for non-maritime places: "
    f"{len(excluded_sea_lane):,}"
)

print(
    f"Accepted projections for Graph v2: "
    f"{len(accepted):,}"
)


# Make Itiner-e IDs consistent.
accepted[
    "itinere_id"
] = (
    accepted[
        "itinere_id"
    ]
    .astype(int)
)


# Group accepted projections by original road segment.
projections_by_segment = {
    int(itinere_id): group.copy()
    for itinere_id, group
    in accepted.groupby(
        "itinere_id"
    )
}


print(
    f"Itiner-e segments receiving "
    f"at least one projected place: "
    f"{len(projections_by_segment):,}"
)


# ---------------------------------------------------------
# Graph setup
# ---------------------------------------------------------

graph = nx.MultiDiGraph()


next_node_id = 0


# Original road endpoints ARE allowed to merge globally.
#
# This preserves the exact endpoint topology validated in
# Week 1.
endpoint_coordinate_to_node = {}


def get_or_create_endpoint_node(
    coordinate,
):

    global next_node_id

    lon = float(
        coordinate[0]
    )

    lat = float(
        coordinate[1]
    )

    key = (
        lon,
        lat,
    )


    if key in endpoint_coordinate_to_node:

        return (
            endpoint_coordinate_to_node[
                key
            ]
        )


    node_id = next_node_id

    next_node_id += 1


    graph.add_node(
        node_id,
        longitude=lon,
        latitude=lat,
        node_type="road_endpoint",
        source_itinere_id=None,
    )


    endpoint_coordinate_to_node[
        key
    ] = node_id


    return node_id


def create_split_node(
    coordinate,
    itinere_id,
):

    """
    Internal split nodes are deliberately NOT merged with
    internal points from other Itiner-e segments.

    This prevents Graph v2 from accidentally inventing new
    intersections simply because two geometries cross.
    """

    global next_node_id


    node_id = next_node_id

    next_node_id += 1


    graph.add_node(
        node_id,
        longitude=float(
            coordinate[0]
        ),
        latitude=float(
            coordinate[1]
        ),
        node_type="place_projection",
        source_itinere_id=int(
            itinere_id
        ),
    )


    return node_id


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

road_segments_loaded = 0

physical_subsegments_created = 0

directed_edges_created = 0

split_nodes_created = 0

zero_length_intervals_skipped = 0


original_network_distance_km = 0.0

v2_network_distance_km = 0.0


place_node_rows = []

physical_edge_rows = []


# ---------------------------------------------------------
# Process Itiner-e
# ---------------------------------------------------------

with open(
    ITINERE_PATH,
    "r",
    encoding="utf-8",
) as f:

    for line in f:

        line = line.strip()

        if not line:
            continue


        record = json.loads(
            line
        )


        geometry_data = record.get(
            "geometry"
        )


        if not geometry_data:
            continue


        if (
            geometry_data.get("type")
            != "LineString"
        ):
            continue


        coordinates = (
            geometry_data.get(
                "coordinates",
                [],
            )
        )


        if len(coordinates) < 2:
            continue


        road_wgs = LineString(
            coordinates
        )


        if not road_wgs.intersects(
            DEVELOPMENT_BBOX
        ):
            continue


        road_segments_loaded += 1


        itinere_id = int(
            record["id"]
        )


        props = record.get(
            "properties",
            {}
        )


        road_name = props.get(
            "name"
        )

        road_type = props.get(
            "type"
        )

        mode = transport_mode(
            road_type
        )


        original_distance = props.get(
            "_lengthInKm"
        )


        road_metric = wgs_to_metric(
            road_wgs
        )


        total_metric_length = (
            road_metric.length
        )


        if total_metric_length <= 0:

            continue


        if original_distance is None:

            original_distance = (
                total_metric_length
                / 1000
            )


        original_distance = float(
            original_distance
        )


        original_network_distance_km += (
            original_distance
        )


        # -------------------------------------------------
        # Accepted projections for this segment
        # -------------------------------------------------

        segment_places = (
            projections_by_segment.get(
                itinere_id
            )
        )


        projection_items = []


        if segment_places is not None:

            for _, place_row in (
                segment_places.iterrows()
            ):

                along_m = float(
                    place_row[
                        "distance_along_segment_km"
                    ]
                ) * 1000


                # Keep values within the real segment.
                along_m = max(
                    0.0,
                    min(
                        total_metric_length,
                        along_m,
                    ),
                )


                # Reuse road endpoint if sufficiently close.
                if (
                    along_m
                    <= ENDPOINT_TOLERANCE_M
                ):

                    along_m = 0.0


                elif (
                    total_metric_length
                    - along_m
                    <= ENDPOINT_TOLERANCE_M
                ):

                    along_m = (
                        total_metric_length
                    )


                projection_items.append(
                    {
                        "along_m": along_m,
                        "row": place_row,
                    }
                )


        projection_items.sort(
            key=lambda item:
            item["along_m"]
        )


        # -------------------------------------------------
        # Cluster near-identical projection locations
        # -------------------------------------------------

        clusters = []


        for item in projection_items:

            along_m = item[
                "along_m"
            ]


            if not clusters:

                clusters.append(
                    {
                        "positions": [
                            along_m
                        ],
                        "rows": [
                            item["row"]
                        ],
                        "last_position": (
                            along_m
                        ),
                    }
                )

                continue


            previous = clusters[-1]


            if (
                along_m
                - previous[
                    "last_position"
                ]
                <= SPLIT_CLUSTER_TOLERANCE_M
            ):

                previous[
                    "positions"
                ].append(
                    along_m
                )

                previous[
                    "rows"
                ].append(
                    item["row"]
                )

                previous[
                    "last_position"
                ] = along_m


            else:

                clusters.append(
                    {
                        "positions": [
                            along_m
                        ],
                        "rows": [
                            item["row"]
                        ],
                        "last_position": (
                            along_m
                        ),
                    }
                )


        # -------------------------------------------------
        # Convert clusters into split locations
        # -------------------------------------------------

        internal_cuts = []

        start_place_rows = []

        end_place_rows = []


        for cluster in clusters:

            positions = cluster[
                "positions"
            ]


            # Endpoint clusters remain exact endpoints.
            if all(
                position == 0.0
                for position
                in positions
            ):

                start_place_rows.extend(
                    cluster[
                        "rows"
                    ]
                )

                continue


            if all(
                position
                == total_metric_length
                for position
                in positions
            ):

                end_place_rows.extend(
                    cluster[
                        "rows"
                    ]
                )

                continue


            representative_position = (
                sum(
                    positions
                )
                / len(
                    positions
                )
            )


            internal_cuts.append(
                {
                    "along_m": (
                        representative_position
                    ),
                    "rows": (
                        cluster["rows"]
                    ),
                }
            )


        internal_cuts.sort(
            key=lambda cut:
            cut["along_m"]
        )


        # -------------------------------------------------
        # Create the segment's nodes
        # -------------------------------------------------

        original_start_coordinate = (
            coordinates[0]
        )

        original_end_coordinate = (
            coordinates[-1]
        )


        start_node = (
            get_or_create_endpoint_node(
                original_start_coordinate
            )
        )

        end_node = (
            get_or_create_endpoint_node(
                original_end_coordinate
            )
        )


        cut_records = [
            {
                "along_m": 0.0,
                "node_id": start_node,
                "coordinate": (
                    original_start_coordinate
                ),
                "rows": start_place_rows,
            }
        ]


        for cut in internal_cuts:

            along_m = cut[
                "along_m"
            ]


            metric_point = (
                road_metric.interpolate(
                    along_m
                )
            )


            point_wgs = metric_to_wgs(
                metric_point
            )


            coordinate = (
                float(point_wgs.x),
                float(point_wgs.y),
            )


            node_id = (
                create_split_node(
                    coordinate,
                    itinere_id,
                )
            )


            split_nodes_created += 1


            cut_records.append(
                {
                    "along_m": along_m,
                    "node_id": node_id,
                    "coordinate": coordinate,
                    "rows": cut[
                        "rows"
                    ],
                }
            )


        cut_records.append(
            {
                "along_m": (
                    total_metric_length
                ),
                "node_id": end_node,
                "coordinate": (
                    original_end_coordinate
                ),
                "rows": end_place_rows,
            }
        )


        # -------------------------------------------------
        # Map Pleiades places to their Graph-v2 nodes
        # -------------------------------------------------

        for cut in cut_records:

            node_id = cut[
                "node_id"
            ]


            for place_row in cut[
                "rows"
            ]:

                place_node_rows.append(
                    {
                        "pleiades_id": int(
                            place_row["id"]
                        ),
                        "title": (
                            place_row["title"]
                        ),
                        "routing_types": (
                            place_row[
                                "routing_types"
                            ]
                        ),
                        "graph_node_id": (
                            node_id
                        ),
                        "itinere_id": (
                            itinere_id
                        ),
                        "road_name": (
                            road_name
                        ),
                        "road_type": (
                            road_type
                        ),
                        "transport_mode": (
                            mode
                        ),
                        "distance_to_network_km": float(
                            place_row[
                                "distance_to_network_km"
                            ]
                        ),
                        "segment_fraction": float(
                            place_row[
                                "segment_fraction"
                            ]
                        ),
                        "node_longitude": float(
                            graph.nodes[
                                node_id
                            ][
                                "longitude"
                            ]
                        ),
                        "node_latitude": float(
                            graph.nodes[
                                node_id
                            ][
                                "latitude"
                            ]
                        ),
                    }
                )


        # -------------------------------------------------
        # Passability
        # -------------------------------------------------

        passability = (
            props.get(
                "passability"
            )
            or {}
        )


        forward_allowed = (
            passability.get(
                "forward",
                1,
            )
            != 0
        )


        backward_allowed = (
            passability.get(
                "backward",
                1,
            )
            != 0
        )


        # -------------------------------------------------
        # Original Itiner-e metadata
        # -------------------------------------------------

        base_attributes = {
            "itinere_id": (
                itinere_id
            ),
            "road_name": (
                road_name
            ),
            "road_type": (
                road_type
            ),
            "transport_mode": (
                mode
            ),
            "certainty": props.get(
                "segmentCertainty"
            ),
            "lower_date": props.get(
                "lowerDate"
            ),
            "upper_date": props.get(
                "upperDate"
            ),
            "construction_period": (
                props.get(
                    "constructionPeriod"
                )
            ),
            "bibliography": (
                props.get(
                    "bibliography"
                )
            ),
            "original_distance_km": (
                original_distance
            ),
            "pleiades_ids": [
                place.get(
                    "id"
                )
                for place
                in record.get(
                    "pleiadesPlaces",
                    [],
                )
                if place.get(
                    "id"
                )
                is not None
            ],
        }


        # -------------------------------------------------
        # Split original segment into subsegments
        # -------------------------------------------------

        for subsegment_index in range(
            len(cut_records) - 1
        ):

            current_cut = (
                cut_records[
                    subsegment_index
                ]
            )

            next_cut = (
                cut_records[
                    subsegment_index
                    + 1
                ]
            )


            start_m = current_cut[
                "along_m"
            ]

            end_m = next_cut[
                "along_m"
            ]


            interval_length_m = (
                end_m
                - start_m
            )


            if interval_length_m <= 0:

                zero_length_intervals_skipped += 1

                continue


            sub_metric = substring(
                road_metric,
                start_m,
                end_m,
                normalized=False,
            )


            if (
                sub_metric.geom_type
                != "LineString"
            ):

                zero_length_intervals_skipped += 1

                continue


            sub_wgs = metric_to_wgs(
                sub_metric
            )


            sub_coordinates = list(
                sub_wgs.coords
            )


            # Force exact agreement between graph nodes and
            # edge geometry endpoints.
            sub_coordinates[0] = (
                current_cut[
                    "coordinate"
                ]
            )

            sub_coordinates[-1] = (
                next_cut[
                    "coordinate"
                ]
            )


            sub_distance_km = (
                original_distance
                * (
                    interval_length_m
                    / total_metric_length
                )
            )


            v2_network_distance_km += (
                sub_distance_km
            )


            source_node = (
                current_cut[
                    "node_id"
                ]
            )

            target_node = (
                next_cut[
                    "node_id"
                ]
            )


            physical_subsegments_created += 1


            physical_edge_rows.append(
                {
                    "source_node": (
                        source_node
                    ),
                    "target_node": (
                        target_node
                    ),
                    "itinere_id": (
                        itinere_id
                    ),
                    "subsegment_index": (
                        subsegment_index
                    ),
                    "road_name": (
                        road_name
                    ),
                    "road_type": (
                        road_type
                    ),
                    "transport_mode": (
                        mode
                    ),
                    "distance_km": (
                        sub_distance_km
                    ),
                    "certainty": props.get(
                        "segmentCertainty"
                    ),
                    "start_fraction": (
                        start_m
                        / total_metric_length
                    ),
                    "end_fraction": (
                        end_m
                        / total_metric_length
                    ),
                    "geometry": LineString(
                        sub_coordinates
                    ),
                }
            )


            edge_attributes = {
                **base_attributes,
                "subsegment_index": (
                    subsegment_index
                ),
                "distance_km": (
                    sub_distance_km
                ),
                "start_fraction": (
                    start_m
                    / total_metric_length
                ),
                "end_fraction": (
                    end_m
                    / total_metric_length
                ),
            }


            if forward_allowed:

                graph.add_edge(
                    source_node,
                    target_node,
                    **edge_attributes,
                    direction="forward",
                    coordinates=(
                        sub_coordinates
                    ),
                )

                directed_edges_created += 1


            if backward_allowed:

                graph.add_edge(
                    target_node,
                    source_node,
                    **edge_attributes,
                    direction="backward",
                    coordinates=list(
                        reversed(
                            sub_coordinates
                        )
                    ),
                )

                directed_edges_created += 1


# ---------------------------------------------------------
# Attach place IDs to node attributes
# ---------------------------------------------------------

places_by_node = {}


for row in place_node_rows:

    node_id = row[
        "graph_node_id"
    ]


    places_by_node.setdefault(
        node_id,
        [],
    ).append(
        {
            "pleiades_id": row[
                "pleiades_id"
            ],
            "title": row[
                "title"
            ],
        }
    )


for node_id, places_at_node in (
    places_by_node.items()
):

    graph.nodes[
        node_id
    ][
        "attached_places"
    ] = places_at_node


# ---------------------------------------------------------
# Validate Graph v2
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


distance_difference = abs(
    original_network_distance_km
    - v2_network_distance_km
)


print("\n=== GRAPH V2 RESULTS ===")

print(
    f"Original road segments loaded: "
    f"{road_segments_loaded:,}"
)

print(
    f"Graph nodes: "
    f"{graph.number_of_nodes():,}"
)

print(
    f"New internal split nodes: "
    f"{split_nodes_created:,}"
)

print(
    f"Physical subsegments created: "
    f"{physical_subsegments_created:,}"
)

print(
    f"Directed graph edges: "
    f"{directed_edges_created:,}"
)

print(
    f"Places mapped to Graph-v2 nodes: "
    f"{len(place_node_rows):,}"
)

print(
    f"Weakly connected components: "
    f"{len(components):,}"
)

if components:

    print(
        f"Largest component nodes: "
        f"{len(components[0]):,}"
    )

    print(
        f"Largest component percentage: "
        f"{len(components[0]) / graph.number_of_nodes() * 100:.2f}%"
    )


print(
    "\n=== DISTANCE CONSERVATION ==="
)

print(
    f"Original physical network distance: "
    f"{original_network_distance_km:.6f} km"
)

print(
    f"Graph-v2 physical network distance: "
    f"{v2_network_distance_km:.6f} km"
)

print(
    f"Absolute difference: "
    f"{distance_difference:.12f} km"
)

print(
    f"Zero-length intervals skipped: "
    f"{zero_length_intervals_skipped:,}"
)


if len(components) != 11:

    print(
        "\nWARNING:"
        " Graph v2 no longer has the same "
        "11 weak components as Week 1."
    )

    print(
        "Investigate before using Graph v2 "
        "for routing."
    )


if distance_difference > 0.001:

    print(
        "\nWARNING:"
        " Graph-v2 distance is not sufficiently "
        "close to the original network distance."
    )


# ---------------------------------------------------------
# Save graph
# ---------------------------------------------------------

with open(
    GRAPH_OUTPUT,
    "wb",
) as f:

    pickle.dump(
        graph,
        f,
    )


# ---------------------------------------------------------
# Export node layer
# ---------------------------------------------------------

node_rows = []


for node_id, attrs in graph.nodes(
    data=True
):

    attached_places = attrs.get(
        "attached_places",
        [],
    )


    node_rows.append(
        {
            "node_id": node_id,
            "node_type": attrs.get(
                "node_type"
            ),
            "source_itinere_id": attrs.get(
                "source_itinere_id"
            ),
            "attached_place_count": len(
                attached_places
            ),
            "attached_place_ids": ",".join(
                str(
                    place[
                        "pleiades_id"
                    ]
                )
                for place
                in attached_places
            ),
            "geometry": Point(
                attrs[
                    "longitude"
                ],
                attrs[
                    "latitude"
                ],
            ),
        }
    )


nodes_gdf = gpd.GeoDataFrame(
    node_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


nodes_gdf.to_file(
    NODES_OUTPUT,
    driver="GeoJSON",
)


# ---------------------------------------------------------
# Export physical Graph-v2 edges
# ---------------------------------------------------------

edges_gdf = gpd.GeoDataFrame(
    physical_edge_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


edges_gdf.to_file(
    EDGES_OUTPUT,
    driver="GeoJSON",
)


# ---------------------------------------------------------
# Export place -> graph-node mapping
# ---------------------------------------------------------

place_nodes_df = pd.DataFrame(
    place_node_rows
)


place_nodes_df.to_csv(
    PLACE_NODE_OUTPUT,
    index=False,
)


# ---------------------------------------------------------
# Output paths
# ---------------------------------------------------------

print("\n=== OUTPUT ===")

print(
    GRAPH_OUTPUT
)

print(
    NODES_OUTPUT
)

print(
    EDGES_OUTPUT
)

print(
    PLACE_NODE_OUTPUT
)

print(
    "\nGraph v2 construction complete."
)