from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GIS_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "pleiades"
    / "gis"
)

PLACES_PATH = GIS_DIR / "places.csv"
TYPES_PATH = GIS_DIR / "place_types.csv"
REL_PATH = GIS_DIR / "places_place_types.csv"


places = pd.read_csv(
    PLACES_PATH,
    low_memory=False
)

types = pd.read_csv(
    TYPES_PATH,
    low_memory=False
)

relationships = pd.read_csv(
    REL_PATH,
    low_memory=False
)


# -------------------------------------------------------
# Count how often each place type occurs
# -------------------------------------------------------

counts = (
    relationships["place_type"]
    .value_counts()
    .rename_axis("key")
    .reset_index(name="count")
)


# Attach human-readable term
result = counts.merge(
    types[["key", "term"]],
    on="key",
    how="left"
)


print("\n=== MOST COMMON PLEIADES PLACE TYPES ===")

print(
    result
    .head(100)
    .to_string(index=False)
)


# -------------------------------------------------------
# Search for likely transportation / settlement types
# -------------------------------------------------------

keywords = [
    "settlement",
    "city",
    "town",
    "village",
    "port",
    "harbor",
    "harbour",
    "anchorage",
    "station",
    "fort",
    "castellum",
    "bridge",
    "road",
]

pattern = "|".join(keywords)

likely = result[
    result["term"]
    .str.contains(
        pattern,
        case=False,
        na=False
    )
]


print("\n=== POSSIBLY USEFUL ROUTING PLACE TYPES ===")

print(
    likely
    .sort_values("count", ascending=False)
    .to_string(index=False)
)