import json
from pathlib import Path
from collections import Counter

from shapely.geometry import shape
import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "itinere"
    / "route-segments-all-1788681284419.ndjson"
)


rows = []

with open(PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        record = json.loads(line)
        props = record["properties"]

        pleiades_places = record.get("pleiadesPlaces", [])

        rows.append(
            {
                "id": record["id"],
                "name": props.get("name"),
                "road_type": props.get("type"),
                "lower_date": props.get("lowerDate"),
                "lower_date_error": props.get("lowerDateError"),
                "upper_date": props.get("upperDate"),
                "upper_date_error": props.get("upperDateError"),
                "construction_period": props.get("constructionPeriod"),
                "certainty": props.get("segmentCertainty"),
                "description": props.get("description"),
                "itinerary": props.get("itinerary"),
                "author": props.get("author"),
                "bibliography": props.get("bibliography"),
                "length_km": props.get("_lengthInKm"),
                "pass_forward": props.get("passability", {}).get("forward"),
                "pass_backward": props.get("passability", {}).get("backward"),
                "pleiades_count": len(pleiades_places),
                "pleiades_ids": [p["id"] for p in pleiades_places],
                "geometry": shape(record["geometry"]),
            }
        )


roads = gpd.GeoDataFrame(
    rows,
    geometry="geometry",
    crs="EPSG:4326"
)


print("\n=== BASIC INFORMATION ===")
print(f"Road segments: {len(roads):,}")
print(f"CRS: {roads.crs}")


print("\n=== GEOMETRY TYPES ===")
print(roads.geometry.geom_type.value_counts())


print("\n=== ROAD TYPES ===")
print(roads["road_type"].value_counts(dropna=False))


print("\n=== CERTAINTY ===")
print(roads["certainty"].value_counts(dropna=False))


print("\n=== CONSTRUCTION PERIODS ===")
print(roads["construction_period"].value_counts(dropna=False).head(30))


print("\n=== PASSABILITY ===")
print(
    roads[
        ["pass_forward", "pass_backward"]
    ].value_counts(dropna=False)
)


print("\n=== PLEIADES ASSOCIATIONS ===")
with_pleiades = (roads["pleiades_count"] > 0).sum()

print(f"Segments with Pleiades places: {with_pleiades:,}")
print(
    f"Percentage: "
    f"{with_pleiades / len(roads) * 100:.2f}%"
)

print("\nNumber of Pleiades places per segment:")
print(roads["pleiades_count"].value_counts().sort_index().head(20))


print("\n=== LENGTH STATISTICS (KM) ===")
print(roads["length_km"].describe())


print("\n=== DATE STATISTICS ===")
print("Lower date:")
print(roads["lower_date"].describe())

print("\nUpper date:")
print(roads["upper_date"].describe())


print("\n=== NULL COUNTS ===")

important_columns = [
    "name",
    "road_type",
    "lower_date",
    "upper_date",
    "construction_period",
    "certainty",
    "bibliography",
    "length_km",
]

for column in important_columns:
    null_count = roads[column].isna().sum()

    print(
        f"{column:25} "
        f"{null_count:6} "
        f"({null_count / len(roads) * 100:6.2f}%)"
    )


print("\n=== SAMPLE RECORD ===")

sample_columns = [
    "id",
    "name",
    "road_type",
    "length_km",
    "lower_date",
    "upper_date",
    "certainty",
    "pleiades_ids",
]

print(roads[sample_columns].iloc[0])