import argparse
import json
import pickle
from pathlib import Path

import pandas as pd

from backend.routing.dijkstra import (
    dijkstra_shortest_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph.pkl"
)

PLACES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_places_attached.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "first_real_route.geojson"
)


def find_place(places, name):
    """
    Find a Pleiades place by exact title first,
    then by partial title match.
    """

    exact_matches = places[
        places["title"].str.casefold()
        == name.casefold()
    ]

    if len(exact_matches) == 1:
        return exact_matches.iloc[0]

    if len(exact_matches) > 1:
        print(
            f"\nMultiple exact matches found for '{name}':"
        )

        print(
            exact_matches[
                [
                    "id",
                    "title",
                    "graph_node_id",
                    "component_id",
                    "snap_distance_km",
                ]
            ].to_string(index=False)
        )

        raise ValueError(
            "Use a more specific place name."
        )

    partial_matches = places[
        places["title"].str.contains(
            name,
            case=False,
            na=False,
            regex=False,
        )
    ]

    if len(partial_matches) == 0:
        raise ValueError(
            f"No place found matching '{name}'."
        )

    if len(partial_matches) > 1:
        print(
            f"\nMultiple partial matches found "
            f"for '{name}':"
        )

        print(
            partial_matches[
                [
                    "id",
                    "title",
                    "graph_node_id",
                    "component_id",
                    "snap_distance_km",
                ]
            ]
            .head(20)
            .to_string(index=False)
        )

        raise ValueError(
            "Use a more specific place name."
        )

    return partial_matches.iloc[0]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate a historical route through "
            "the Itiner-e transportation network."
        )
    )

    parser.add_argument(
        "--origin",
        required=True,
        help="Origin Pleiades place title.",
    )

    parser.add_argument(
        "--destination",
        required=True,
        help="Destination Pleiades place title.",
    )

    args = parser.parse_args()

    # -----------------------------------------------------
    # Load graph and place attachments
    # -----------------------------------------------------

    with open(GRAPH_PATH, "rb") as f:
        graph = pickle.load(f)

    places = pd.read_csv(PLACES_PATH)

    origin = find_place(
        places,
        args.origin,
    )

    destination = find_place(
        places,
        args.destination,
    )

    origin_node = int(
        origin["graph_node_id"]
    )

    destination_node = int(
        destination["graph_node_id"]
    )

    origin_component = int(
        origin["component_id"]
    )

    destination_component = int(
        destination["component_id"]
    )

    # -----------------------------------------------------
    # Display request
    # -----------------------------------------------------

    print("\n=== ROUTE REQUEST ===")

    print(
        f"Origin: {origin['title']}"
    )

    print(
        f"Origin graph node: {origin_node}"
    )

    print(
        f"Origin component: {origin_component}"
    )

    print(
        f"Origin attachment distance: "
        f"{origin['snap_distance_km']:.3f} km"
    )

    print()

    print(
        f"Destination: {destination['title']}"
    )

    print(
        f"Destination graph node: "
        f"{destination_node}"
    )

    print(
        f"Destination component: "
        f"{destination_component}"
    )

    print(
        f"Destination attachment distance: "
        f"{destination['snap_distance_km']:.3f} km"
    )

    # -----------------------------------------------------
    # Confirm connectivity before Dijkstra
    # -----------------------------------------------------

    if origin_component != destination_component:
        raise ValueError(
            f"{origin['title']} is in component "
            f"{origin_component}, but "
            f"{destination['title']} is in component "
            f"{destination_component}. "
            "No route can exist between them in "
            "the current graph."
        )

    # -----------------------------------------------------
    # Run our Dijkstra implementation
    # -----------------------------------------------------

    result = dijkstra_shortest_path(
        graph,
        origin_node,
        destination_node,
    )

    print("\n=== ROUTE RESULT ===")

    print(
        f"Network distance: "
        f"{result['distance']:.2f} km"
    )

    print(
        f"Graph nodes traversed: "
        f"{len(result['nodes']):,}"
    )

    print(
        f"Road edges traversed: "
        f"{len(result['edges']):,}"
    )

    # -----------------------------------------------------
    # Build route GeoJSON
    # -----------------------------------------------------

    features = []

    print("\n=== ROAD SEGMENTS ===")

    for sequence, (
        source,
        target,
        edge_key,
    ) in enumerate(
        result["edges"],
        start=1,
    ):

        edge = graph[
            source
        ][
            target
        ][
            edge_key
        ]

        road_name = (
            edge.get("road_name")
            or "(unnamed road)"
        )

        distance_km = float(
            edge.get("distance_km", 0)
        )

        print(
            f"{sequence:3}. "
            f"{road_name} "
            f"({distance_km:.2f} km)"
        )

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "sequence": sequence,
                    "source_node": source,
                    "target_node": target,
                    "itinere_id": (
                        edge.get("itinere_id")
                    ),
                    "road_name": road_name,
                    "road_type": (
                        edge.get("road_type")
                    ),
                    "distance_km": distance_km,
                    "certainty": (
                        edge.get("certainty")
                    ),
                    "lower_date": (
                        edge.get("lower_date")
                    ),
                    "upper_date": (
                        edge.get("upper_date")
                    ),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": (
                        edge["coordinates"]
                    ),
                },
            }
        )

    output = {
        "type": "FeatureCollection",
        "properties": {
            "origin": origin["title"],
            "destination": destination["title"],
            "network_distance_km": (
                result["distance"]
            ),
        },
        "features": features,
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n=== OUTPUT ===")

    print(
        f"Route saved to:\n{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()