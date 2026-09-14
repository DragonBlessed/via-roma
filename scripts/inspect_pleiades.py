from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GIS_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "pleiades"
    / "gis"
)

PLACES_PATH = GIS_DIR / "places.csv"
LOCATION_POINTS_PATH = GIS_DIR / "location_points.csv"
PLACE_TYPES_PATH = GIS_DIR / "place_types.csv"
PLACES_PLACE_TYPES_PATH = GIS_DIR / "places_place_types.csv"
TIME_PERIODS_PATH = GIS_DIR / "time_periods.csv"
NAMES_PATH = GIS_DIR / "names.csv"
CONNECTIONS_PATH = GIS_DIR / "connections.csv"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def load_csv(path):
    """Load a CSV and report basic information."""
    if not path.exists():
        print(f"\nWARNING: File not found: {path.name}")
        return None

    df = pd.read_csv(path, low_memory=False)

    print(f"\n=== {path.name.upper()} ===")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumn names:")
    for column in df.columns:
        print(f"  - {column}")

    return df


def print_null_stats(df, columns):
    """Print null percentages for selected columns."""
    print("\n=== NULL COUNTS ===")

    for column in columns:
        if column not in df.columns:
            continue

        null_count = df[column].isna().sum()
        percent = null_count / len(df) * 100

        print(
            f"{column:30} "
            f"{null_count:8,} "
            f"({percent:6.2f}%)"
        )


# ---------------------------------------------------------
# Load primary place dataset
# ---------------------------------------------------------

places = load_csv(PLACES_PATH)

if places is None:
    raise FileNotFoundError(
        f"Could not find {PLACES_PATH}"
    )


# ---------------------------------------------------------
# Places overview
# ---------------------------------------------------------

print("\n\n========================================")
print("PLEIADES PLACE DATASET SUMMARY")
print("========================================")

print(f"\nTotal places: {len(places):,}")


# ---------------------------------------------------------
# Coordinate statistics
# ---------------------------------------------------------

lat_col = "representative_latitude"
lon_col = "representative_longitude"

if lat_col in places.columns and lon_col in places.columns:

    # Convert to numbers safely
    places[lat_col] = pd.to_numeric(
        places[lat_col],
        errors="coerce"
    )

    places[lon_col] = pd.to_numeric(
        places[lon_col],
        errors="coerce"
    )

    has_coordinates = (
        places[lat_col].notna()
        & places[lon_col].notna()
    )

    coordinate_count = has_coordinates.sum()

    print("\n=== COORDINATES ===")

    print(
        f"Places with representative coordinates: "
        f"{coordinate_count:,}"
    )

    print(
        f"Percentage with coordinates: "
        f"{coordinate_count / len(places) * 100:.2f}%"
    )

    print("\nLatitude range:")
    print(
        f"{places[lat_col].min()} "
        f"to {places[lat_col].max()}"
    )

    print("\nLongitude range:")
    print(
        f"{places[lon_col].min()} "
        f"to {places[lon_col].max()}"
    )


# ---------------------------------------------------------
# Location precision
# ---------------------------------------------------------

if "location_precision" in places.columns:

    print("\n=== LOCATION PRECISION ===")

    print(
        places["location_precision"]
        .value_counts(dropna=False)
        .head(20)
    )


# ---------------------------------------------------------
# Provenance
# ---------------------------------------------------------

if "provenance" in places.columns:

    print("\n=== TOP PROVENANCE VALUES ===")

    print(
        places["provenance"]
        .value_counts(dropna=False)
        .head(20)
    )


# ---------------------------------------------------------
# Null statistics
# ---------------------------------------------------------

important_place_columns = [
    "id",
    "title",
    "uri",
    "description",
    "details",
    "provenance",
    "representative_latitude",
    "representative_longitude",
    "location_precision",
    "bounding_box_wkt",
]

print_null_stats(
    places,
    important_place_columns
)


# ---------------------------------------------------------
# Sample records
# ---------------------------------------------------------

sample_columns = [
    column
    for column in [
        "id",
        "title",
        "representative_latitude",
        "representative_longitude",
        "location_precision",
        "provenance",
        "uri",
    ]
    if column in places.columns
]

print("\n=== SAMPLE PLACES ===")

print(
    places[sample_columns]
    .head(10)
    .to_string(index=False)
)


# ---------------------------------------------------------
# Load supporting tables
# ---------------------------------------------------------

location_points = load_csv(LOCATION_POINTS_PATH)
place_types = load_csv(PLACE_TYPES_PATH)
places_place_types = load_csv(PLACES_PLACE_TYPES_PATH)
time_periods = load_csv(TIME_PERIODS_PATH)
names = load_csv(NAMES_PATH)
connections = load_csv(CONNECTIONS_PATH)


# ---------------------------------------------------------
# Location points summary
# ---------------------------------------------------------

if location_points is not None:

    print("\n=== LOCATION POINTS SUMMARY ===")

    print(f"Location point records: {len(location_points):,}")

    print_null_stats(
        location_points,
        list(location_points.columns[:10])
    )


# ---------------------------------------------------------
# Place types summary
# ---------------------------------------------------------

if place_types is not None:

    print("\n=== PLACE TYPES ===")

    print(
        place_types
        .head(30)
        .to_string(index=False)
    )


if places_place_types is not None:

    print("\n=== PLACE ↔ TYPE RELATIONSHIPS ===")

    print(
        f"Relationship records: "
        f"{len(places_place_types):,}"
    )

    print(
        places_place_types
        .head(10)
        .to_string(index=False)
    )


# ---------------------------------------------------------
# Time periods summary
# ---------------------------------------------------------

if time_periods is not None:

    print("\n=== TIME PERIODS ===")

    print(
        time_periods
        .head(30)
        .to_string(index=False)
    )


# ---------------------------------------------------------
# Names summary
# ---------------------------------------------------------

if names is not None:

    print("\n=== NAMES ===")

    print(f"Name records: {len(names):,}")

    print(
        names
        .head(10)
        .to_string(index=False)
    )


# ---------------------------------------------------------
# Connections summary
# ---------------------------------------------------------

if connections is not None:

    print("\n=== CONNECTIONS ===")

    print(f"Connection records: {len(connections):,}")

    print(
        connections
        .head(10)
        .to_string(index=False)
    )


print("\n========================================")
print("PLEIADES INSPECTION COMPLETE")
print("========================================")