import argparse
import math
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import substring, transform


# ---------------------------------------------------------
# Paths / arguments
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build an experimental multimodal Graph v3 by "
            "connecting strong Pleiades maritime-transfer "
            "candidates to both land and sea transportation."
        )
    )

    parser.add_argument(
        "--scope",
        default="mediterranean",
        help="Regional filename prefix, e.g. mediterranean.",
    )

    parser.add_argument(
        "--include-review",
        action="store_true",
        help=(
            "Also include review_candidate records. "
            "Default is strong_candidate only."
        ),
    )

    parser.add_argument(
        "--endpoint-tolerance-m",
        type=float,
        default=10.0,
        help=(
            "Reuse an existing graph node when the new "
            "projection falls within this distance of it."
        ),
    )

    return parser.parse_args()


ARGS = parse_args()
SCOPE = ARGS.scope.strip().lower().replace(" ", "_")

GRAPH_INPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v2_candidate.pkl"
)

PLACE_MAPPING_INPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v2_candidate_place_nodes.csv"
)

ROADS_INPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_itinere_roads.geojson"
)

CANDIDATES_INPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_maritime_transfer_candidates.csv"
)

GRAPH_OUTPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v3_candidate.pkl"
)

PLACE_MAPPING_OUTPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v3_candidate_place_nodes.csv"
)

TRANSFER_LOG_OUTPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v3_transfer_log.csv"
)

TRANSFER_GEOJSON_OUTPUT = (
    PROCESSED_DIR
    / f"{SCOPE}_graph_v3_maritime_transfers.geojson"
)


# ---------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------

TO_METRIC = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:3035",
    always_xy=True,
)

TO_WGS84 = Transformer.from_crs(
    "EPSG:3035",
    "EPSG:4326",
    always_xy=True,
)


def wgs_to_metric(geometry):
    return transform(
        TO_METRIC.transform,
        geometry,
    )


def metric_to_wgs(geometry):
    return transform(
        TO_WGS84.transform,
        geometry,
    )


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def node_coordinate(graph, node_id):
    attrs = graph.nodes[node_id]

    return (
        float(attrs["longitude"]),
        float(attrs["latitude"]),
    )


def metric_distance_km(coord_a, coord_b):
    point_a = wgs_to_metric(
        Point(coord_a)
    )
    point_b = wgs_to_metric(
        Point(coord_b)
    )

    return float(
        point_a.distance(point_b)
        / 1000.0
    )


def project_place_to_line(
    place_coord,
    line_wgs,
):
    """
    Project a Pleiades representative point onto one
    original Itiner-e LineString.

    Returns:
        global fraction along the original line,
        projected WGS84 coordinate,
        point-to-line distance in km.
    """

    place_metric = wgs_to_metric(
        Point(place_coord)
    )

    line_metric = wgs_to_metric(
        line_wgs
    )

    total_length = float(
        line_metric.length
    )

    if total_length <= 0:
        raise ValueError(
            "Cannot project onto a zero-length segment."
        )

    along_m = float(
        line_metric.project(
            place_metric
        )
    )

    projected_metric = (
        line_metric.interpolate(
            along_m
        )
    )

    projected_wgs = metric_to_wgs(
        projected_metric
    )

    fraction = (
        along_m
        / total_length
    )

    distance_km = float(
        place_metric.distance(
            projected_metric
        )
        / 1000.0
    )

    return (
        fraction,
        (
            float(projected_wgs.x),
            float(projected_wgs.y),
        ),
        distance_km,
    )


def edge_matches_itinere(
    data,
    itinere_id,
):
    value = data.get(
        "itinere_id"
    )

    if value is None:
        return False

    try:
        return int(value) == int(itinere_id)
    except (
        TypeError,
        ValueError,
    ):
        return False


def interval_edges_for_fraction(
    graph,
    itinere_id,
    fraction,
):
    """
    Find current Graph-v2/v3 edge intervals belonging to
    one Itiner-e segment that contain the requested original
    segment fraction.
    """

    candidates = []

    for (
        source,
        target,
        key,
        data,
    ) in graph.edges(
        keys=True,
        data=True,
    ):

        if not edge_matches_itinere(
            data,
            itinere_id,
        ):
            continue

        start_fraction = data.get(
            "start_fraction"
        )

        end_fraction = data.get(
            "end_fraction"
        )

        if (
            start_fraction is None
            or end_fraction is None
        ):
            continue

        start_fraction = float(
            start_fraction
        )

        end_fraction = float(
            end_fraction
        )

        if (
            start_fraction - 1e-12
            <= fraction
            <= end_fraction + 1e-12
        ):
            candidates.append(
                (
                    source,
                    target,
                    key,
                    data,
                    start_fraction,
                    end_fraction,
                )
            )

    return candidates


def split_graph_segment(
    graph,
    itinere_id,
    fraction,
    projected_coord,
    next_node_id,
    endpoint_tolerance_m,
):
    """
    Insert/reuse a graph node at one fractional position
    along an original Itiner-e segment.

    If the point lies inside an existing Graph-v2
    subsegment, both directed versions of that physical
    subsegment are replaced by two smaller subsegments.

    Total transportation distance is conserved exactly
    through proportional distance splitting.
    """

    interval_edges = (
        interval_edges_for_fraction(
            graph,
            itinere_id,
            fraction,
        )
    )

    if not interval_edges:
        raise ValueError(
            f"No current graph edge contains fraction "
            f"{fraction:.8f} of Itiner-e segment "
            f"{itinere_id}."
        )

    # -----------------------------------------------------
    # First reuse an existing nearby interval endpoint.
    # This also handles a projection that lands on a split
    # created earlier in this same v3 build.
    # -----------------------------------------------------

    endpoint_nodes = set()

    for (
        source,
        target,
        _,
        _,
        _,
        _,
    ) in interval_edges:

        endpoint_nodes.add(
            int(source)
        )
        endpoint_nodes.add(
            int(target)
        )

    nearest_existing = None

    for node_id in endpoint_nodes:

        distance_m = (
            metric_distance_km(
                projected_coord,
                node_coordinate(
                    graph,
                    node_id,
                ),
            )
            * 1000.0
        )

        if (
            nearest_existing is None
            or distance_m
            < nearest_existing[0]
        ):
            nearest_existing = (
                distance_m,
                node_id,
            )

    if (
        nearest_existing is not None
        and nearest_existing[0]
        <= endpoint_tolerance_m
    ):
        return (
            int(
                nearest_existing[1]
            ),
            next_node_id,
            False,
        )

    # -----------------------------------------------------
    # Pick the smallest current interval containing the
    # desired fraction. This is important after earlier
    # transfer points have already split the same segment.
    # -----------------------------------------------------

    interval_edges.sort(
        key=lambda item:
        (
            item[5] - item[4],
            item[4],
        )
    )

    chosen = interval_edges[0]

    chosen_start = float(
        chosen[4]
    )
    chosen_end = float(
        chosen[5]
    )

    if (
        not chosen_start
        < fraction
        < chosen_end
    ):
        # Numerical boundary case: use closest endpoint.
        source = int(
            chosen[0]
        )
        target = int(
            chosen[1]
        )

        source_distance = (
            metric_distance_km(
                projected_coord,
                node_coordinate(
                    graph,
                    source,
                ),
            )
        )

        target_distance = (
            metric_distance_km(
                projected_coord,
                node_coordinate(
                    graph,
                    target,
                ),
            )
        )

        return (
            source
            if source_distance
            <= target_distance
            else target,
            next_node_id,
            False,
        )

    representative_data = (
        chosen[3]
    )

    subsegment_index = (
        representative_data.get(
            "subsegment_index"
        )
    )

    # All directions of this one physical interval.
    physical_edges = []

    for (
        source,
        target,
        key,
        data,
    ) in graph.edges(
        keys=True,
        data=True,
    ):

        if not edge_matches_itinere(
            data,
            itinere_id,
        ):
            continue

        if (
            data.get(
                "subsegment_index"
            )
            != subsegment_index
        ):
            continue

        start_value = data.get(
            "start_fraction"
        )

        end_value = data.get(
            "end_fraction"
        )

        if (
            start_value is None
            or end_value is None
        ):
            continue

        if (
            abs(
                float(start_value)
                - chosen_start
            )
            > 1e-12
            or abs(
                float(end_value)
                - chosen_end
            )
            > 1e-12
        ):
            continue

        physical_edges.append(
            (
                source,
                target,
                key,
                data.copy(),
            )
        )

    if not physical_edges:
        raise RuntimeError(
            "Unable to identify the physical "
            "subsegment directions to split."
        )

    forward_record = next(
        (
            record
            for record
            in physical_edges
            if record[3].get(
                "direction"
            )
            == "forward"
        ),
        None,
    )

    backward_record = next(
        (
            record
            for record
            in physical_edges
            if record[3].get(
                "direction"
            )
            == "backward"
        ),
        None,
    )

    if forward_record is not None:
        original_start_node = int(
            forward_record[0]
        )
        original_end_node = int(
            forward_record[1]
        )
        forward_coordinates = list(
            forward_record[3][
                "coordinates"
            ]
        )
        base_data = (
            forward_record[3].copy()
        )

    elif backward_record is not None:
        original_start_node = int(
            backward_record[1]
        )
        original_end_node = int(
            backward_record[0]
        )
        forward_coordinates = list(
            reversed(
                backward_record[3][
                    "coordinates"
                ]
            )
        )
        base_data = (
            backward_record[3].copy()
        )

    else:
        raise RuntimeError(
            "Physical interval has neither a "
            "forward nor backward edge."
        )

    # -----------------------------------------------------
    # Split the current geometry at the projected point.
    # -----------------------------------------------------

    forward_line_wgs = LineString(
        forward_coordinates
    )

    forward_line_metric = (
        wgs_to_metric(
            forward_line_wgs
        )
    )

    projected_metric = wgs_to_metric(
        Point(
            projected_coord
        )
    )

    local_along_m = float(
        forward_line_metric.project(
            projected_metric
        )
    )

    local_along_m = max(
        0.0,
        min(
            float(
                forward_line_metric.length
            ),
            local_along_m,
        ),
    )

    first_metric = substring(
        forward_line_metric,
        0.0,
        local_along_m,
        normalized=False,
    )

    second_metric = substring(
        forward_line_metric,
        local_along_m,
        float(
            forward_line_metric.length
        ),
        normalized=False,
    )

    if (
        first_metric.geom_type
        != "LineString"
        or second_metric.geom_type
        != "LineString"
    ):
        raise RuntimeError(
            f"Splitting Itiner-e segment "
            f"{itinere_id} produced a non-LineString."
        )

    first_wgs = metric_to_wgs(
        first_metric
    )

    second_wgs = metric_to_wgs(
        second_metric
    )

    first_coordinates = [
        tuple(coord)
        for coord in first_wgs.coords
    ]

    second_coordinates = [
        tuple(coord)
        for coord in second_wgs.coords
    ]

    # Force exact graph/geometry endpoint agreement.
    first_coordinates[0] = (
        node_coordinate(
            graph,
            original_start_node,
        )
    )
    first_coordinates[-1] = (
        projected_coord
    )

    second_coordinates[0] = (
        projected_coord
    )
    second_coordinates[-1] = (
        node_coordinate(
            graph,
            original_end_node,
        )
    )

    # -----------------------------------------------------
    # New projection node.
    # -----------------------------------------------------

    new_node = int(
        next_node_id
    )

    graph.add_node(
        new_node,
        longitude=float(
            projected_coord[0]
        ),
        latitude=float(
            projected_coord[1]
        ),
        node_type=(
            "maritime_transfer_projection"
        ),
        source_itinere_id=int(
            itinere_id
        ),
    )

    next_node_id += 1

    # -----------------------------------------------------
    # Preserve exact parent distance.
    # -----------------------------------------------------

    parent_distance_km = float(
        base_data[
            "distance_km"
        ]
    )

    fraction_within_interval = (
        (
            fraction
            - chosen_start
        )
        / (
            chosen_end
            - chosen_start
        )
    )

    first_distance_km = (
        parent_distance_km
        * fraction_within_interval
    )

    second_distance_km = (
        parent_distance_km
        - first_distance_km
    )

    # Remove old direction(s).
    for (
        source,
        target,
        key,
        _,
    ) in physical_edges:

        graph.remove_edge(
            source,
            target,
            key,
        )

    # Copy historical attributes but replace the fields
    # that describe this physical interval.
    for field in [
        "coordinates",
        "direction",
        "distance_km",
        "start_fraction",
        "end_fraction",
    ]:
        base_data.pop(
            field,
            None,
        )

    had_forward = (
        forward_record
        is not None
    )

    had_backward = (
        backward_record
        is not None
    )

    if had_forward:

        graph.add_edge(
            original_start_node,
            new_node,
            **base_data,
            direction="forward",
            distance_km=(
                first_distance_km
            ),
            start_fraction=(
                chosen_start
            ),
            end_fraction=(
                fraction
            ),
            coordinates=(
                first_coordinates
            ),
        )

        graph.add_edge(
            new_node,
            original_end_node,
            **base_data,
            direction="forward",
            distance_km=(
                second_distance_km
            ),
            start_fraction=(
                fraction
            ),
            end_fraction=(
                chosen_end
            ),
            coordinates=(
                second_coordinates
            ),
        )

    if had_backward:

        graph.add_edge(
            original_end_node,
            new_node,
            **base_data,
            direction="backward",
            distance_km=(
                second_distance_km
            ),
            start_fraction=(
                fraction
            ),
            end_fraction=(
                chosen_end
            ),
            coordinates=list(
                reversed(
                    second_coordinates
                )
            ),
        )

        graph.add_edge(
            new_node,
            original_start_node,
            **base_data,
            direction="backward",
            distance_km=(
                first_distance_km
            ),
            start_fraction=(
                chosen_start
            ),
            end_fraction=(
                fraction
            ),
            coordinates=list(
                reversed(
                    first_coordinates
                )
            ),
        )

    return (
        new_node,
        next_node_id,
        True,
    )


def add_transfer_connector(
    graph,
    source_node,
    target_node,
    coordinates,
    distance_km,
    title,
    pleiades_id,
    side,
):
    """
    Add a bidirectional synthetic transfer connector.

    Transfer distance is the point-to-network distance
    between the Pleiades port position and the relevant
    projected transport node.
    """

    common = {
        "itinere_id": None,
        "road_name": (
            f"{title} maritime transfer"
        ),
        "road_type": (
            "Maritime Transfer"
        ),
        "transport_mode": (
            "transfer"
        ),
        "certainty": (
            "inferred_from_strong_candidate"
        ),
        "lower_date": None,
        "upper_date": None,
        "construction_period": None,
        "bibliography": None,
        "original_distance_km": None,
        "subsegment_index": (
            f"maritime:{pleiades_id}:{side}"
        ),
        "distance_km": float(
            distance_km
        ),
        "start_fraction": None,
        "end_fraction": None,
        "transfer_pleiades_id": int(
            pleiades_id
        ),
        "transfer_side": side,
    }

    graph.add_edge(
        source_node,
        target_node,
        **common,
        direction="forward",
        coordinates=coordinates,
    )

    graph.add_edge(
        target_node,
        source_node,
        **common,
        direction="backward",
        coordinates=list(
            reversed(
                coordinates
            )
        ),
    )


# ---------------------------------------------------------
# Load inputs
# ---------------------------------------------------------

print(
    "\n=== MULTIMODAL GRAPH V3 BUILD ==="
)

print(
    f"Scope: {SCOPE}"
)

print(
    f"Graph input: {GRAPH_INPUT}"
)

print(
    f"Transfer candidates: "
    f"{CANDIDATES_INPUT}"
)


with open(
    GRAPH_INPUT,
    "rb",
) as f:
    graph = pickle.load(
        f
    )


place_mapping = pd.read_csv(
    PLACE_MAPPING_INPUT
)

roads = gpd.read_file(
    ROADS_INPUT
)

candidates = pd.read_csv(
    CANDIDATES_INPUT
)


# Itiner-e IDs should be unique in the regional source layer.
roads[
    "itinere_id"
] = (
    roads[
        "itinere_id"
    ]
    .astype(int)
)

if roads[
    "itinere_id"
].duplicated().any():
    raise RuntimeError(
        "Regional Itiner-e source contains duplicate "
        "itinere_id rows."
    )


road_geometry_by_id = {
    int(row["itinere_id"]):
    row.geometry
    for _, row
    in roads.iterrows()
}


# ---------------------------------------------------------
# Choose candidates
# ---------------------------------------------------------

allowed_statuses = {
    "strong_candidate",
}

if ARGS.include_review:
    allowed_statuses.add(
        "review_candidate"
    )


selected = candidates[
    candidates[
        "candidate_status"
    ].isin(
        allowed_statuses
    )
    & candidates[
        "would_merge_components"
    ].fillna(
        False
    )
].copy()


selected = selected.sort_values(
    [
        "max_transfer_distance_km",
        "id",
    ]
).reset_index(
    drop=True
)


print(
    f"Selected transfer places: "
    f"{len(selected):,}"
)

print(
    f"Statuses: "
    f"{sorted(allowed_statuses)}"
)


# ---------------------------------------------------------
# Baseline graph statistics
# ---------------------------------------------------------

before_components = list(
    nx.weakly_connected_components(
        graph
    )
)

before_components.sort(
    key=len,
    reverse=True,
)

before_nodes = (
    graph.number_of_nodes()
)

before_edges = (
    graph.number_of_edges()
)


if len(graph.nodes) == 0:
    raise RuntimeError(
        "Input graph is empty."
    )


next_node_id = (
    max(
        int(node_id)
        for node_id
        in graph.nodes
    )
    + 1
)


mapping_index_by_id = {
    int(row["pleiades_id"]):
    index
    for index, row
    in place_mapping.iterrows()
}


transfer_log = []
transfer_features = []

split_nodes_created = 0
port_nodes_created = 0
connector_physical_edges = 0
connector_directed_edges = 0
connector_distance_km = 0.0


# ---------------------------------------------------------
# Build transfer connections
# ---------------------------------------------------------

for row_number, row in (
    selected.iterrows()
):

    pleiades_id = int(
        row["id"]
    )

    title = str(
        row["title"]
    )

    place_coord = (
        float(
            row["longitude"]
        ),
        float(
            row["latitude"]
        ),
    )

    land_itinere_id = int(
        row[
            "land_itinere_id"
        ]
    )

    sea_itinere_id = int(
        row[
            "sea_itinere_id"
        ]
    )


    if (
        land_itinere_id
        not in road_geometry_by_id
    ):
        raise RuntimeError(
            f"{title}: land Itiner-e segment "
            f"{land_itinere_id} is missing."
        )

    if (
        sea_itinere_id
        not in road_geometry_by_id
    ):
        raise RuntimeError(
            f"{title}: sea Itiner-e segment "
            f"{sea_itinere_id} is missing."
        )


    (
        land_fraction,
        land_coord,
        land_distance_km,
    ) = project_place_to_line(
        place_coord,
        road_geometry_by_id[
            land_itinere_id
        ],
    )


    (
        sea_fraction,
        sea_coord,
        sea_distance_km,
    ) = project_place_to_line(
        place_coord,
        road_geometry_by_id[
            sea_itinere_id
        ],
    )


    (
        land_node,
        next_node_id,
        land_created,
    ) = split_graph_segment(
        graph,
        land_itinere_id,
        land_fraction,
        land_coord,
        next_node_id,
        ARGS.endpoint_tolerance_m,
    )


    (
        sea_node,
        next_node_id,
        sea_created,
    ) = split_graph_segment(
        graph,
        sea_itinere_id,
        sea_fraction,
        sea_coord,
        next_node_id,
        ARGS.endpoint_tolerance_m,
    )


    split_nodes_created += int(
        land_created
    )
    split_nodes_created += int(
        sea_created
    )


    # Create a central node at the Pleiades place itself.
    # This makes the model explicitly:
    #
    # land -> historical port -> sea
    #
    # rather than directly welding two unrelated lines.
    port_node = int(
        next_node_id
    )

    next_node_id += 1

    graph.add_node(
        port_node,
        longitude=float(
            place_coord[0]
        ),
        latitude=float(
            place_coord[1]
        ),
        node_type=(
            "maritime_transfer_place"
        ),
        source_itinere_id=None,
        attached_places=[
            {
                "pleiades_id":
                    pleiades_id,
                "title":
                    title,
            }
        ],
    )

    port_nodes_created += 1


    # Remove stale attached-place metadata from a previous
    # Graph-v2 mapping node, if this place was already mapped.
    if (
        pleiades_id
        in mapping_index_by_id
    ):

        mapping_index = (
            mapping_index_by_id[
                pleiades_id
            ]
        )

        old_node = int(
            place_mapping.at[
                mapping_index,
                "graph_node_id",
            ]
        )

        if (
            old_node
            in graph.nodes
        ):

            attached = (
                graph.nodes[
                    old_node
                ].get(
                    "attached_places",
                    [],
                )
            )

            graph.nodes[
                old_node
            ][
                "attached_places"
            ] = [
                item
                for item
                in attached
                if int(
                    item.get(
                        "pleiades_id",
                        -1,
                    )
                )
                != pleiades_id
            ]


    # Land projection -> port.
    add_transfer_connector(
        graph,
        land_node,
        port_node,
        [
            land_coord,
            place_coord,
        ],
        land_distance_km,
        title,
        pleiades_id,
        "land",
    )

    # Port -> sea projection.
    add_transfer_connector(
        graph,
        port_node,
        sea_node,
        [
            place_coord,
            sea_coord,
        ],
        sea_distance_km,
        title,
        pleiades_id,
        "sea",
    )

    connector_physical_edges += 2
    connector_directed_edges += 4

    connector_distance_km += (
        land_distance_km
        + sea_distance_km
    )


    # -----------------------------------------------------
    # Update/add Pleiades -> graph-node mapping.
    # -----------------------------------------------------

    new_mapping_values = {
        "pleiades_id":
            pleiades_id,
        "title":
            title,
        "routing_types":
            row[
                "routing_types"
            ],
        "graph_node_id":
            port_node,
        "itinere_id":
            None,
        "road_name":
            f"{title} maritime transfer",
        "road_type":
            "Maritime Transfer",
        "transport_mode":
            "transfer",
        "distance_to_network_km":
            0.0,
        "segment_fraction":
            None,
        "node_longitude":
            float(
                place_coord[0]
            ),
        "node_latitude":
            float(
                place_coord[1]
            ),
    }


    if (
        pleiades_id
        in mapping_index_by_id
    ):

        mapping_index = (
            mapping_index_by_id[
                pleiades_id
            ]
        )

        for (
            column,
            value,
        ) in new_mapping_values.items():

            place_mapping.at[
                mapping_index,
                column,
            ] = value

    else:

        place_mapping = pd.concat(
            [
                place_mapping,
                pd.DataFrame(
                    [
                        new_mapping_values
                    ]
                ),
            ],
            ignore_index=True,
        )

        mapping_index_by_id[
            pleiades_id
        ] = (
            len(place_mapping)
            - 1
        )


    transfer_log.append(
        {
            "pleiades_id":
                pleiades_id,
            "title":
                title,
            "candidate_status":
                row[
                    "candidate_status"
                ],
            "port_node":
                port_node,
            "land_itinere_id":
                land_itinere_id,
            "land_node":
                land_node,
            "land_projection_created":
                bool(
                    land_created
                ),
            "land_distance_km":
                land_distance_km,
            "sea_itinere_id":
                sea_itinere_id,
            "sea_node":
                sea_node,
            "sea_projection_created":
                bool(
                    sea_created
                ),
            "sea_distance_km":
                sea_distance_km,
            "total_transfer_distance_km":
                (
                    land_distance_km
                    + sea_distance_km
                ),
        }
    )


    # GeoJSON visualization of the two inferred connectors.
    transfer_features.append(
        {
            "type": "Feature",
            "properties": {
                "pleiades_id":
                    pleiades_id,
                "title":
                    title,
                "side":
                    "land",
                "distance_km":
                    land_distance_km,
                "candidate_status":
                    row[
                        "candidate_status"
                    ],
            },
            "geometry": {
                "type":
                    "LineString",
                "coordinates": [
                    list(
                        land_coord
                    ),
                    list(
                        place_coord
                    ),
                ],
            },
        }
    )

    transfer_features.append(
        {
            "type": "Feature",
            "properties": {
                "pleiades_id":
                    pleiades_id,
                "title":
                    title,
                "side":
                    "sea",
                "distance_km":
                    sea_distance_km,
                "candidate_status":
                    row[
                        "candidate_status"
                    ],
            },
            "geometry": {
                "type":
                    "LineString",
                "coordinates": [
                    list(
                        place_coord
                    ),
                    list(
                        sea_coord
                    ),
                ],
            },
        }
    )


# ---------------------------------------------------------
# Validation / statistics
# ---------------------------------------------------------

after_components = list(
    nx.weakly_connected_components(
        graph
    )
)

after_components.sort(
    key=len,
    reverse=True,
)


duplicate_mapping_ids = (
    place_mapping[
        "pleiades_id"
    ].duplicated().sum()
)

if duplicate_mapping_ids:
    raise RuntimeError(
        f"Graph v3 mapping contains "
        f"{duplicate_mapping_ids} duplicate "
        f"Pleiades IDs."
    )


print(
    "\n=== GRAPH V3 RESULTS ==="
)

print(
    f"Graph nodes: "
    f"{before_nodes:,} -> "
    f"{graph.number_of_nodes():,}"
)

print(
    f"Directed graph edges: "
    f"{before_edges:,} -> "
    f"{graph.number_of_edges():,}"
)

print(
    f"Transport split nodes created: "
    f"{split_nodes_created:,}"
)

print(
    f"Maritime place nodes created: "
    f"{port_nodes_created:,}"
)

print(
    f"Synthetic transfer connectors: "
    f"{connector_physical_edges:,} physical / "
    f"{connector_directed_edges:,} directed"
)

print(
    f"Total synthetic transfer distance: "
    f"{connector_distance_km:.6f} km"
)

print(
    f"Mapped Pleiades places: "
    f"{len(place_mapping):,}"
)


print(
    "\n=== CONNECTIVITY ==="
)

print(
    f"Weak components: "
    f"{len(before_components):,} -> "
    f"{len(after_components):,}"
)

if after_components:

    largest = len(
        after_components[0]
    )

    print(
        f"Largest component nodes: "
        f"{largest:,}"
    )

    print(
        f"Largest component percentage: "
        f"{largest / graph.number_of_nodes() * 100:.2f}%"
    )


# ---------------------------------------------------------
# Save outputs
# ---------------------------------------------------------

with open(
    GRAPH_OUTPUT,
    "wb",
) as f:

    pickle.dump(
        graph,
        f,
    )


place_mapping.to_csv(
    PLACE_MAPPING_OUTPUT,
    index=False,
)


transfer_log_df = pd.DataFrame(
    transfer_log
)

transfer_log_df.to_csv(
    TRANSFER_LOG_OUTPUT,
    index=False,
)


transfer_geojson = {
    "type": "FeatureCollection",
    "feature_count":
        len(
            transfer_features
        ),
    "features":
        transfer_features,
}

import json

with open(
    TRANSFER_GEOJSON_OUTPUT,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        transfer_geojson,
        f,
        ensure_ascii=False,
    )


print(
    "\n=== OUTPUT ==="
)

print(
    GRAPH_OUTPUT
)

print(
    PLACE_MAPPING_OUTPUT
)

print(
    TRANSFER_LOG_OUTPUT
)

print(
    TRANSFER_GEOJSON_OUTPUT
)

print(
    "\nGraph v3 candidate construction complete."
)
