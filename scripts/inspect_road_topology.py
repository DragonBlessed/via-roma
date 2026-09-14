from pathlib import Path
from collections import Counter

import geopandas as gpd
from shapely.geometry import Point


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROADS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_itinere_roads.geojson"
)


roads = gpd.read_file(ROADS_PATH)


print("\n=== ROAD TOPOLOGY INSPECTION ===")
print(f"Road segments: {len(roads):,}")


# ---------------------------------------------------------
# Extract first and last coordinate of every road
# ---------------------------------------------------------

endpoints = []

for _, road in roads.iterrows():

    geometry = road.geometry

    if geometry is None:
        continue

    if geometry.geom_type == "LineString":

        coordinates = list(geometry.coords)

        start = coordinates[0]
        end = coordinates[-1]

        endpoints.append(
            {
                "road_id": road["itinere_id"],
                "endpoint": "start",
                "longitude": start[0],
                "latitude": start[1],
            }
        )

        endpoints.append(
            {
                "road_id": road["itinere_id"],
                "endpoint": "end",
                "longitude": end[0],
                "latitude": end[1],
            }
        )


print(f"Total endpoints: {len(endpoints):,}")


# ---------------------------------------------------------
# Exact coordinate matches
# ---------------------------------------------------------

exact_coordinates = Counter(
    (
        item["longitude"],
        item["latitude"],
    )
    for item in endpoints
)


unique_exact = len(exact_coordinates)

shared_exact = sum(
    1
    for count in exact_coordinates.values()
    if count > 1
)


endpoints_in_exact_matches = sum(
    count
    for count in exact_coordinates.values()
    if count > 1
)


print("\n=== EXACT ENDPOINT MATCHING ===")

print(
    f"Unique exact endpoint coordinates: "
    f"{unique_exact:,}"
)

print(
    f"Coordinates shared by multiple roads: "
    f"{shared_exact:,}"
)

print(
    f"Endpoints participating in exact matches: "
    f"{endpoints_in_exact_matches:,}"
)

print(
    f"Percentage of endpoints in exact matches: "
    f"{endpoints_in_exact_matches / len(endpoints) * 100:.2f}%"
)


# ---------------------------------------------------------
# Rounded coordinate matching
# ---------------------------------------------------------

for decimals in [6, 5, 4, 3]:

    rounded = Counter(
        (
            round(item["longitude"], decimals),
            round(item["latitude"], decimals),
        )
        for item in endpoints
    )

    shared = sum(
        count
        for count in rounded.values()
        if count > 1
    )

    print(
        f"\nRounded to {decimals} decimals:"
    )

    print(
        f"Endpoints participating in shared coordinates: "
        f"{shared:,}"
    )

    print(
        f"Percentage: "
        f"{shared / len(endpoints) * 100:.2f}%"
    )