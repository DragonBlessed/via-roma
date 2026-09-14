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

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
# Italy development bounding box
#
# longitude: 6 -> 19
# latitude: 36 -> 47.5
# ---------------------------------------------------------

ITALY_BBOX = box(
    6.0,
    36.0,
    19.0,
    47.5,
)


# ---------------------------------------------------------
# Load Pleiades
# ---------------------------------------------------------

places = pd.read_csv(
    PLACES_PATH,
    low_memory=False
)

relationships = pd.read_csv(
    REL_PATH,
    low_memory=False
)


relevant_rel = relationships[
    relationships["place_type"].isin(ROUTING_PLACE_TYPES)
].copy()


# One place may have multiple useful types.
place_type_lists = (
    relevant_rel
    .groupby("place_id")["place_type"]
    .apply(lambda values: sorted(set(values)))
    .reset_index()
    .rename(columns={"place_type": "routing_types"})
)


places = places.merge(
    place_type_lists,
    left_on="id",
    right_on="place_id",
    how="inner",
)


# Coordinates to numeric form
places["representative_longitude"] = pd.to_numeric(
    places["representative_longitude"],
    errors="coerce",
)

places["representative_latitude"] = pd.to_numeric(
    places["representative_latitude"],
    errors="coerce",
)


# Remove places that cannot be mapped
places = places.dropna(
    subset=[
        "representative_longitude",
        "representative_latitude",
    ]
)


places_gdf = gpd.GeoDataFrame(
    places,
    geometry=gpd.points_from_xy(
        places["representative_longitude"],
        places["representative_latitude"],
    ),
    crs="EPSG:4326",
)


places_italy = places_gdf[
    places_gdf.geometry.within(ITALY_BBOX)
].copy()


# ---------------------------------------------------------
# Load Itiner-e roads
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

        record = json.loads(line)

        geometry = shape(record["geometry"])

        if not geometry.intersects(ITALY_BBOX):
            continue

        props = record["properties"]

        road_rows.append(
            {
                "itinere_id": record["id"],
                "road_name": props.get("name"),
                "road_type": props.get("type"),
                "certainty": props.get("segmentCertainty"),
                "length_km": props.get("_lengthInKm"),
                "geometry": geometry,
            }
        )


roads_italy = gpd.GeoDataFrame(
    road_rows,
    geometry="geometry",
    crs="EPSG:4326",
)


# ---------------------------------------------------------
# Basic counts
# ---------------------------------------------------------

print("\n=== ITALY DEVELOPMENT SUBSET ===")

print(
    f"Routing-relevant Pleiades places: "
    f"{len(places_italy):,}"
)

print(
    f"Itiner-e road segments: "
    f"{len(roads_italy):,}"
)


print("\n=== PLACE TYPES IN ITALY ===")

type_counts = (
    relevant_rel[
        relevant_rel["place_id"].isin(
            places_italy["id"]
        )
    ]["place_type"]
    .value_counts()
)

print(type_counts)


# ---------------------------------------------------------
# Convert to metric CRS
#
# EPSG:3035 uses meters and works well for Italy.
# ---------------------------------------------------------

places_metric = places_italy.to_crs("EPSG:3035")
roads_metric = roads_italy.to_crs("EPSG:3035")


# ---------------------------------------------------------
# Find nearest Itiner-e road
# ---------------------------------------------------------

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
    distance_col="distance_to_road_m",
)


nearest["distance_to_road_km"] = (
    nearest["distance_to_road_m"] / 1000
)


# In rare cases, equal-distance roads can produce duplicates.
# Keep only the closest row for each Pleiades place.
nearest = (
    nearest
    .sort_values("distance_to_road_km")
    .drop_duplicates(subset="id")
    .copy()
)


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

print("\n=== DISTANCE TO NEAREST ITINER-E ROAD ===")

print(
    nearest["distance_to_road_km"]
    .describe()
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


print("\n=== DISTANCE THRESHOLDS ===")

for threshold in thresholds:

    count = (
        nearest["distance_to_road_km"]
        <= threshold
    ).sum()

    percent = (
        count
        / len(nearest)
        * 100
    )

    print(
        f"<= {threshold:5.2f} km: "
        f"{count:5,} "
        f"({percent:6.2f}%)"
    )


# ---------------------------------------------------------
# Examples
# ---------------------------------------------------------

display_columns = [
    "id",
    "title",
    "routing_types",
    "distance_to_road_km",
    "itinere_id",
    "road_name",
]


print("\n=== 20 CLOSEST PLACES ===")

print(
    nearest[
        display_columns
    ]
    .sort_values("distance_to_road_km")
    .head(20)
    .to_string(index=False)
)


print("\n=== 30 FARTHEST PLACES ===")

print(
    nearest[
        display_columns
    ]
    .sort_values(
        "distance_to_road_km",
        ascending=False,
    )
    .head(30)
    .to_string(index=False)
)


# ---------------------------------------------------------
# Save outputs
# ---------------------------------------------------------

output_csv = (
    OUTPUT_DIR
    / "italy_place_road_proximity.csv"
)

nearest.drop(
    columns="geometry"
).to_csv(
    output_csv,
    index=False,
)


places_output = (
    OUTPUT_DIR
    / "italy_routing_places.geojson"
)

roads_output = (
    OUTPUT_DIR
    / "italy_itinere_roads.geojson"
)


places_italy.to_file(
    places_output,
    driver="GeoJSON",
)

roads_italy.to_file(
    roads_output,
    driver="GeoJSON",
)


print("\n=== OUTPUT FILES ===")

print(output_csv)
print(places_output)
print(roads_output)