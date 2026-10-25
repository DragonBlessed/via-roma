import argparse
import math
from pathlib import Path

import pandas as pd

from backend.routing.service import RoutingService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT_ROOT / "data" / "processed"

DEFAULT_GRAPH = PROCESSED / "mediterranean_graph_v3.pkl"
DEFAULT_MAPPING = PROCESSED / "mediterranean_graph_v3_place_nodes.csv"
DEFAULT_TRANSFER_LOG = PROCESSED / "mediterranean_graph_v3_transfer_log.csv"
DEFAULT_CANDIDATES = PROCESSED / "mediterranean_maritime_transfer_candidates.csv"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inspect Via Roma route mode usage."
    )
    parser.add_argument("--origin", type=int, default=423025)
    parser.add_argument("--destination", type=int, default=197488)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--transfer-log", type=Path, default=DEFAULT_TRANSFER_LOG)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--nearest-transfers", type=int, default=10)
    return parser.parse_args()


def haversine_km(lon1, lat1, lon2, lat2):
    radius_km = 6371.0088
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def ordered_unique(values):
    result = []
    seen = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def build_mode_legs(segments):
    legs = []
    for segment in segments:
        mode = segment.get("transport_mode") or "unknown"

        if not legs or legs[-1]["mode"] != mode:
            legs.append(
                {
                    "mode": mode,
                    "start_order": int(segment["route_order"]),
                    "end_order": int(segment["route_order"]),
                    "edge_count": 1,
                    "distance_km": float(segment["distance_km"]),
                    "names": [segment.get("road_name")],
                }
            )
        else:
            leg = legs[-1]
            leg["end_order"] = int(segment["route_order"])
            leg["edge_count"] += 1
            leg["distance_km"] += float(segment["distance_km"])
            leg["names"].append(segment.get("road_name"))

    for leg in legs:
        leg["names"] = ordered_unique(leg["names"])

    return legs


def place_mapping_row(mapping, pleiades_id):
    matches = mapping[mapping["pleiades_id"] == int(pleiades_id)]
    if matches.empty:
        return None
    return matches.iloc[0]


def print_place(label, place, mapping_row):
    print(f"\n{label}: {place['name']} (Pleiades {place['pleiades_id']})")
    print(f"  Graph node: {place['graph_node_id']}")
    print(
        "  Coordinates: "
        f"{float(place['latitude']):.6f}, "
        f"{float(place['longitude']):.6f}"
    )
    print(f"  Current mapping mode: {place.get('transport_mode')}")

    if mapping_row is not None:
        routing_types = mapping_row.get("routing_types")
        if pd.notna(routing_types):
            print(f"  Routing types: {routing_types}")


def print_candidate_status(path, destination_id):
    print("\n=== DESTINATION MARITIME CANDIDATE STATUS ===")

    if not path.exists():
        print(f"Candidate file not found: {path}")
        return

    candidates = pd.read_csv(path)
    matches = candidates[candidates["id"].astype(int) == int(destination_id)]

    if matches.empty:
        print("Destination is not present in the maritime-transfer candidate table.")
        print(
            "Its routing types therefore did not qualify it as a "
            "port/harbor/anchorage when that diagnostic was built."
        )
        return

    row = matches.iloc[0]
    for field in [
        "title",
        "maritime_types",
        "candidate_status",
        "land_distance_km",
        "sea_distance_km",
        "max_transfer_distance_km",
        "would_merge_components",
        "current_transport_mode",
    ]:
        if field in row.index:
            print(f"  {field}: {row[field]}")


def print_nearest_transfers(path, mapping, destination, limit):
    print("\n=== NEAREST EXISTING GRAPH-V3 MARITIME TRANSFERS ===")

    if not path.exists():
        print(f"Transfer log not found: {path}")
        return

    transfer_log = pd.read_csv(path)
    rows = []

    for _, transfer in transfer_log.iterrows():
        transfer_id = int(transfer["pleiades_id"])
        mapping_row = place_mapping_row(mapping, transfer_id)
        if mapping_row is None:
            continue

        lon = mapping_row.get("node_longitude")
        lat = mapping_row.get("node_latitude")
        if pd.isna(lon) or pd.isna(lat):
            continue

        rows.append(
            {
                "pleiades_id": transfer_id,
                "title": transfer["title"],
                "straight_line_km": haversine_km(
                    destination["longitude"],
                    destination["latitude"],
                    lon,
                    lat,
                ),
                "land_distance_km": float(transfer["land_distance_km"]),
                "sea_distance_km": float(transfer["sea_distance_km"]),
            }
        )

    if not rows:
        print("No transfer locations with usable coordinates were found.")
        return

    nearest = (
        pd.DataFrame(rows)
        .sort_values("straight_line_km")
        .head(max(1, int(limit)))
    )

    print(
        nearest.to_string(
            index=False,
            formatters={
                "straight_line_km": lambda v: f"{v:.2f}",
                "land_distance_km": lambda v: f"{v:.3f}",
                "sea_distance_km": lambda v: f"{v:.3f}",
            },
        )
    )


def main():
    args = parse_args()

    for required in [args.graph, args.mapping]:
        if not required.exists():
            raise FileNotFoundError(required)

    service = RoutingService(
        graph_path=args.graph,
        place_nodes_path=args.mapping,
    )

    mapping = pd.read_csv(args.mapping)
    mapping["pleiades_id"] = mapping["pleiades_id"].astype(int)

    origin = service.get_place(args.origin)
    destination = service.get_place(args.destination)
    route = service.route(args.origin, args.destination)

    print("\n=== VIA ROMA ROUTE DIAGNOSTIC ===")
    print_place("Origin", origin, place_mapping_row(mapping, args.origin))
    print_place(
        "Destination",
        destination,
        place_mapping_row(mapping, args.destination),
    )

    print("\n=== CURRENT DISTANCE-OPTIMAL ROUTE ===")
    print(f"Total distance: {route['distance_km']:.6f} km")
    print(f"Nodes / edges: {route['node_count']} / {route['edge_count']}")
    print("Distance by mode:")
    for mode, distance in route["distance_by_mode_km"].items():
        print(f"  {mode}: {float(distance):.6f} km")

    print("\n=== CONTIGUOUS MODE LEGS ===")
    for index, leg in enumerate(build_mode_legs(route["segments"]), start=1):
        print(f"\nLeg {index}: {leg['mode']}")
        print(f"  Route edges: {leg['start_order']}-{leg['end_order']}")
        print(f"  Edge count: {leg['edge_count']}")
        print(f"  Distance: {leg['distance_km']:.6f} km")
        if leg["names"]:
            print("  Transportation names:")
            for name in leg["names"][:8]:
                print(f"    - {name}")
            if len(leg["names"]) > 8:
                print(f"    ... {len(leg['names']) - 8} more")

    transfers = [
        segment
        for segment in route["segments"]
        if segment.get("transport_mode") == "transfer"
    ]

    print("\n=== TRANSFER EDGES USED ===")
    if not transfers:
        print("None.")
    else:
        for segment in transfers:
            print(
                f"  #{segment['route_order']}: "
                f"{segment.get('road_name')} "
                f"({segment['distance_km']:.6f} km)"
            )

    print_candidate_status(args.candidates, args.destination)

    print_nearest_transfers(
        args.transfer_log,
        mapping,
        destination,
        args.nearest_transfers,
    )

    print("\n=== INTERPRETATION CHECKLIST ===")
    print(
        "1. If the route contains little/no sea, compare its land "
        "distance with the nearest existing transfer ports."
    )
    print(
        "2. If Salona is absent from the maritime candidate table, "
        "its Pleiades types prevented a direct port transfer."
    )
    print(
        "3. If usable transfers exist but distance routing still "
        "prefers land, distance_km weighting is part of the problem."
    )
    print(
        "4. The next step is then to add travel-time weights while "
        "preserving shortest-distance routing."
    )


if __name__ == "__main__":
    main()
