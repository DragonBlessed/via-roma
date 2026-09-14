import json
from pathlib import Path
from collections import Counter

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ITINERE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "itinere"
    / "route-segments-all-1788681284419.ndjson"
)

PLEIADES_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "pleiades"
    / "gis"
    / "places.csv"
)


# ---------------------------------------------------------
# Load Pleiades IDs
# ---------------------------------------------------------

places = pd.read_csv(PLEIADES_PATH, low_memory=False)

pleiades_ids = set(
    pd.to_numeric(
        places["id"],
        errors="coerce"
    )
    .dropna()
    .astype(int)
)


# ---------------------------------------------------------
# Inspect Itiner-e Pleiades references
# ---------------------------------------------------------

itinere_refs = []
segment_counts = Counter()

segments_total = 0
segments_with_refs = 0

with open(ITINERE_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        record = json.loads(line)

        segments_total += 1

        refs = record.get("pleiadesPlaces", [])

        segment_counts[len(refs)] += 1

        if refs:
            segments_with_refs += 1

        for place in refs:
            itinere_refs.append(place["id"])


itinere_unique = set(itinere_refs)


# ---------------------------------------------------------
# Compare datasets
# ---------------------------------------------------------

matched = itinere_unique & pleiades_ids
missing = itinere_unique - pleiades_ids


print("\n=== DATASET OVERLAP ===")

print(f"Itiner-e road segments: {segments_total:,}")
print(
    f"Segments with at least one Pleiades reference: "
    f"{segments_with_refs:,}"
)

print(
    f"Percentage of segments with references: "
    f"{segments_with_refs / segments_total * 100:.2f}%"
)


print("\n=== PLEIADES ID MATCHING ===")

print(
    f"Unique Pleiades IDs referenced by Itiner-e: "
    f"{len(itinere_unique):,}"
)

print(
    f"IDs found in Pleiades places.csv: "
    f"{len(matched):,}"
)

print(
    f"IDs not found: "
    f"{len(missing):,}"
)

if itinere_unique:
    print(
        f"Exact match rate: "
        f"{len(matched) / len(itinere_unique) * 100:.2f}%"
    )


print("\n=== ASSOCIATED PLACES PER ROAD SEGMENT ===")

for count, number_of_segments in sorted(segment_counts.items()):
    print(
        f"{count:2} places: "
        f"{number_of_segments:6,} segments"
    )


if missing:
    print("\n=== SAMPLE MISSING IDS ===")

    for value in list(sorted(missing))[:20]:
        print(value)