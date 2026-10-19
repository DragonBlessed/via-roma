import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, box


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

GIS_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "pleiades"
    / "gis"
)

PLACES_PATH = GIS_DIR / "places.csv"
REL_PATH = GIS_DIR / "places_place_types.csv"

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


# ---------------------------------------------------------
# Routing-relevant Pleiades types
# ---------------------------------------------------------

ROUTING_PLACE_TYPES = {
    "settlement",
    "station",
    "port",
    "harbor",
    "anchorage",
    "fortified-settlement",
    "fort",
    "fort-2",
    "fortlet",
    "castellum",
}


# ---------------------------------------------------------
# Named geographic scopes
#
# italy reproduces the original development region exactly.
# mediterranean is the first scale-up target.
# roman_world is available for a later, broader experiment.
# ---------------------------------------------------------

SCOPE_BBOXES = {
    "italy": (
        6.0,
        36.0,
        19.0,
        47.5,
    ),
    "mediterranean": (
        -10.0,
        28.0,
        42.0,
        48.0,
    ),
    "roman_world": (
        -11.0,
        23.0,
        45.0,
        58.0,
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a regional Pleiades routing-place subset and "
            "Itiner-e transportation subset."
        )
    )

    parser.add_argument(
        "--scope",
        default="italy",
        choices=sorted(SCOPE_BBOXES),
        help=(
            "Named geographic scope. "
            "Use mediterranean for the first scale-up test."
        ),
    )

    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        default=None,
        help=(
            "Optional WGS84 bounding box override. "
            "If supplied, it replaces the named scope's preset box."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated regional files.",
    )

    return parser.parse_args()


ARGS = parse_args()

SCOPE = (
    ARGS.scope
    .strip()
    .lower()
    .replace(" ", "_")
)

BBOX_VALUES = (
    tuple(ARGS.bbox)
    if ARGS.bbox is not None
    else SCOPE_BBOXES[SCOPE]
)

REGION_BBOX = box(
    *BBOX_VALUES
)

OUTPUT_DIR = ARGS.output_dir

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# Output paths
# ---------------------------------------------------------

PROXIMITY_OUTPUT = (
    OUTPUT_DIR
    / f"{SCOPE}_place_road_proximity.csv"
)

PLACES_OUTPUT = (
    OUTPUT_DIR
    / f"{SCOPE}_routing_places.geojson"
)

ROADS_OUTPUT = (
    OUTPUT_DIR
    / f"{SCOPE}_itinere_roads.geojson"
)


# ---------------------------------------------------------
# Load Pleiades
# ---------------------------------------------------------

places = pd.read_csv(
    PLACES_PATH,
    low_memory=False,
)

relationships = pd.read_csv(
    REL_PATH,
    low_memory=False,
)


relevant_rel = relationships[
    relationships[
        "place_type"
    ].isin(
        ROUTING_PLACE_TYPES
    )
].copy()


# One place may have multiple routing-relevant types.
place_type_lists = (
    relevant_rel
    .groupby(
        "place_id"
    )[
        "place_type"
    ]
    .apply(
        lambda values:
        sorted(
            set(values)
        )
    )
    .reset_index()
    .rename(
        columns={
            "place_type":
            "routing_types"
        }
    )
)


places = places.merge(
    place_type_lists,
    left_on="id",
    right_on="place_id",
    how="inner",
)


places[
    "representative_longitude"
] = pd.to_numeric(
    places[
        "representative_longitude"
    ],
    errors="coerce",
)

places[
    "representative_latitude"
] = pd.to_numeric(
    places[
        "representative_latitude"
    ],
    errors="coerce",
)


# Remove places that cannot be mapped.
places = places.dropna(
    subset=[
        "representative_longitude",
        "representative_latitude",
    ]
)


places_gdf = gpd.GeoDataFrame(
    places,
    geometry=gpd.points_from_xy(
        places[
            "representative_longitude"
        ],
        places[
            "representative_latitude"
        ],
    ),
    crs="EPSG:4326",
)


# Preserve the original behavior: place representative
# points must fall strictly within the configured box.
places_region = places_gdf[
    places_gdf.geometry.within(
        REGION_BBOX
    )
].copy()


# ---------------------------------------------------------
# Load Itiner-e transportation segments
#
# Preserve the original behavior: if a complete Itiner-e
# LineString intersects the region, retain the complete
# segment rather than clipping it at the rectangular border.
# ---------------------------------------------------------

road_rows = []

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

        geometry = shape(
            geometry_data
        )

        if geometry.geom_type != "LineString":
            continue

        if not geometry.intersects(
            REGION_BBOX
        ):
            continue

        props = record.get(
            "properties",
            {},
        )

        road_rows.append(
            {
                "itinere_id":
                    record["id"],
                "road_name":
                    props.get("name"),
                "road_type":
                    props.get("type"),
                "certainty":
                    props.get(
                        "segmentCertainty"
                    ),
                "length_km":
                    props.get(
                        "_lengthInKm"
                    ),
                "geometry":
                    geometry,
            }
        )


roads_region = gpd.GeoDataFrame(
    road_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


# ---------------------------------------------------------
# Basic counts
# ---------------------------------------------------------

print(
    "\n=== REGIONAL TRANSPORTATION SUBSET ==="
)

print(
    f"Scope: {SCOPE}"
)

print(
    "Bounding box "
    f"(W, S, E, N): "
    f"{BBOX_VALUES}"
)

print(
    "Routing-relevant Pleiades places: "
    f"{len(places_region):,}"
)

print(
    "Itiner-e transportation segments: "
    f"{len(roads_region):,}"
)


print(
    "\n=== PLACE TYPES IN REGION ==="
)

type_counts = (
    relevant_rel[
        relevant_rel[
            "place_id"
        ].isin(
            places_region[
                "id"
            ]
        )
    ][
        "place_type"
    ]
    .value_counts()
)

print(
    type_counts
)


# ---------------------------------------------------------
# Nearest-network statistics
#
# Keep EPSG:3035 for this scale-up experiment so the
# projection behavior stays consistent with the validated
# Italy pipeline. We can revisit CRS strategy separately
# after we have benchmarked the larger region.
# ---------------------------------------------------------

if (
    len(places_region) > 0
    and len(roads_region) > 0
):

    places_metric = (
        places_region.to_crs(
            "EPSG:3035"
        )
    )

    roads_metric = (
        roads_region.to_crs(
            "EPSG:3035"
        )
    )


    nearest = gpd.sjoin_nearest(
        places_metric,
        roads_metric[
            [
                "itinere_id",
                "road_name",
                "road_type",
                "certainty",
                "geometry",
            ]
        ],
        how="left",
        distance_col=(
            "distance_to_road_m"
        ),
    )


    nearest[
        "distance_to_road_km"
    ] = (
        nearest[
            "distance_to_road_m"
        ]
        / 1000
    )


    # Equal-distance segments can occasionally duplicate
    # a Pleiades place. Keep one closest record.
    nearest = (
        nearest
        .sort_values(
            "distance_to_road_km"
        )
        .drop_duplicates(
            subset="id"
        )
        .copy()
    )


    print(
        "\n=== DISTANCE TO NEAREST "
        "ITINER-E SEGMENT ==="
    )

    print(
        nearest[
            "distance_to_road_km"
        ].describe()
    )


    thresholds = [
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
    ]


    print(
        "\n=== DISTANCE THRESHOLDS ==="
    )

    for threshold in thresholds:

        count = (
            nearest[
                "distance_to_road_km"
            ]
            <= threshold
        ).sum()

        percentage = (
            count
            / len(nearest)
            * 100
        )

        print(
            f"<= {threshold:5.2f} km: "
            f"{count:6,} "
            f"({percentage:6.2f}%)"
        )


    nearest.drop(
        columns="geometry"
    ).to_csv(
        PROXIMITY_OUTPUT,
        index=False,
    )

else:

    nearest = None

    print(
        "\nNo proximity statistics generated "
        "because the selected scope contains "
        "no places or no transportation segments."
    )


# ---------------------------------------------------------
# Save regional source layers
# ---------------------------------------------------------

places_region.to_file(
    PLACES_OUTPUT,
    driver="GeoJSON",
)

roads_region.to_file(
    ROADS_OUTPUT,
    driver="GeoJSON",
)


print(
    "\n=== OUTPUT FILES ==="
)

if nearest is not None:
    print(
        PROXIMITY_OUTPUT
    )

print(
    PLACES_OUTPUT
)

print(
    ROADS_OUTPUT
)

print(
    "\nRegional subset complete."
)
