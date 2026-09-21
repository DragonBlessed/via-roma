from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLACES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_routing_places.geojson"
)

ROADS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_itinere_roads.geojson"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

CSV_OUTPUT = (
    OUTPUT_DIR
    / "place_network_projections.csv"
)

POINT_OUTPUT = (
    OUTPUT_DIR
    / "place_network_projection_points.geojson"
)


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

places = gpd.read_file(
    PLACES_PATH
)

roads = gpd.read_file(
    ROADS_PATH
)


print("\n=== PLACE TO NETWORK PROJECTION ===")

print(
    f"Places: "
    f"{len(places):,}"
)

print(
    f"Transportation segments: "
    f"{len(roads):,}"
)


# ---------------------------------------------------------
# Work in a metric CRS
#
# EPSG:3035 lets us calculate projection locations and
# distances in meters.
# ---------------------------------------------------------

places_metric = places.to_crs(
    "EPSG:3035"
)

roads_metric = roads.to_crs(
    "EPSG:3035"
)


# ---------------------------------------------------------
# Find nearest road for each historical place
# ---------------------------------------------------------

nearest = gpd.sjoin_nearest(
    places_metric,
    roads_metric[
        [
            "itinere_id",
            "road_name",
            "road_type",
            "certainty",
            "length_km",
            "geometry",
        ]
    ],
    how="left",
    distance_col="distance_to_network_m",
)


nearest = (
    nearest
    .sort_values(
        "distance_to_network_m"
    )
    .drop_duplicates(
        subset="id"
    )
    .copy()
)


# ---------------------------------------------------------
# Project each place onto its nearest road
# ---------------------------------------------------------

road_geometry_by_index = (
    roads_metric.geometry.to_dict()
)


projection_geometries = []

distance_along_segment_m = []

segment_fraction = []


for _, row in nearest.iterrows():

    road_index = row["index_right"]

    road = road_geometry_by_index[
        road_index
    ]

    place = row.geometry


    # Distance measured along the LineString from its
    # first coordinate to the closest point.
    along = road.project(
        place
    )


    # Exact closest point on the road.
    projected_point = road.interpolate(
        along
    )


    total_length = road.length


    if total_length > 0:
        fraction = (
            along
            / total_length
        )
    else:
        fraction = 0.0


    projection_geometries.append(
        projected_point
    )

    distance_along_segment_m.append(
        along
    )

    segment_fraction.append(
        fraction
    )


nearest[
    "projected_geometry"
] = projection_geometries

nearest[
    "distance_along_segment_m"
] = distance_along_segment_m

nearest[
    "segment_fraction"
] = segment_fraction


nearest[
    "distance_to_network_km"
] = (
    nearest[
        "distance_to_network_m"
    ]
    / 1000
)


nearest[
    "distance_along_segment_km"
] = (
    nearest[
        "distance_along_segment_m"
    ]
    / 1000
)


# ---------------------------------------------------------
# Classification
# ---------------------------------------------------------

def projection_status(distance_km):

    if distance_km <= 2:
        return "automatic"

    if distance_km <= 5:
        return "review"

    return "far"


nearest[
    "projection_status"
] = (
    nearest[
        "distance_to_network_km"
    ]
    .apply(
        projection_status
    )
)


# ---------------------------------------------------------
# Create projected-point GeoDataFrame
# ---------------------------------------------------------

projection_points = (
    gpd.GeoDataFrame(
        nearest.drop(
            columns="geometry"
        ),
        geometry=nearest[
            "projected_geometry"
        ],
        crs="EPSG:3035",
    )
)


# Original projected_geometry column is no longer needed
# separately once it becomes the active geometry.
if (
    "projected_geometry"
    in projection_points.columns
):

    projection_points = (
        projection_points.drop(
            columns=[
                "projected_geometry"
            ]
        )
    )


# Convert back to geographic coordinates for web/QGIS use.
projection_points = (
    projection_points.to_crs(
        "EPSG:4326"
    )
)


projection_points[
    "projected_longitude"
] = (
    projection_points.geometry.x
)

projection_points[
    "projected_latitude"
] = (
    projection_points.geometry.y
)


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

print(
    "\n=== PROJECTION DISTANCE STATISTICS ==="
)

print(
    nearest[
        "distance_to_network_km"
    ].describe()
)


print(
    "\n=== PROJECTION STATUS ==="
)

print(
    nearest[
        "projection_status"
    ].value_counts()
)


print(
    "\n=== DISTANCE THRESHOLDS ==="
)


for threshold in [
    0.25,
    0.5,
    1,
    2,
    5,
    10,
    20,
]:

    count = (
        nearest[
            "distance_to_network_km"
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
        f"{count:5,} "
        f"({percentage:6.2f}%)"
    )


# ---------------------------------------------------------
# Important cities
# ---------------------------------------------------------

print(
    "\n=== IMPORTANT TEST PLACES ==="
)


test_names = [
    "Roma",
    "Capua",
    "Parthenope/Neapolis",
    "Beneventum/Maleventum",
    "Brundisium/Brentesion",
]


for name in test_names:

    matches = projection_points[
        projection_points[
            "title"
        ]
        == name
    ]

    if len(matches) == 0:

        print(
            f"{name}: NOT FOUND"
        )

        continue


    print(
        matches[
            [
                "id",
                "title",
                "itinere_id",
                "road_name",
                "distance_to_network_km",
                "distance_along_segment_km",
                "segment_fraction",
                "projection_status",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()


# ---------------------------------------------------------
# Export CSV
# ---------------------------------------------------------

csv_columns = [
    "id",
    "title",
    "routing_types",
    "itinere_id",
    "road_name",
    "road_type",
    "certainty",
    "distance_to_network_km",
    "distance_along_segment_km",
    "segment_fraction",
    "projection_status",
    "projected_longitude",
    "projected_latitude",
]


projection_points[
    csv_columns
].to_csv(
    CSV_OUTPUT,
    index=False,
)


# ---------------------------------------------------------
# Export projected points
# ---------------------------------------------------------

projection_points[
    csv_columns
    + ["geometry"]
].to_file(
    POINT_OUTPUT,
    driver="GeoJSON",
)


print(
    "\n=== OUTPUT ==="
)

print(
    CSV_OUTPUT
)

print(
    POINT_OUTPUT
)

print(
    "\nProjection complete."
)
