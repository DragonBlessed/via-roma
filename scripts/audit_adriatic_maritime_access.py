import ast
from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT_ROOT / "data" / "processed"

PLACES_PATH = (
    PROCESSED
    / "mediterranean_routing_places.geojson"
)

ROADS_PATH = (
    PROCESSED
    / "mediterranean_itinere_roads.geojson"
)

MAPPING_PATH = (
    PROCESSED
    / "mediterranean_graph_v3_place_nodes.csv"
)

TRANSFER_LOG_PATH = (
    PROCESSED
    / "mediterranean_graph_v3_transfer_log.csv"
)

CANDIDATES_PATH = (
    PROCESSED
    / "mediterranean_maritime_transfer_candidates.csv"
)


TARGET_PATTERNS = [
    "Salona",
    "Ancon",
    "Ravenna",
    "Classis",
    "Iader",
    "Brundisium",
    "Dyrr",
]


def parse_routing_types(value):
    if value is None:
        return set()

    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return {
            str(item)
            for item in value
        }

    text = str(value)

    try:
        parsed = ast.literal_eval(
            text
        )

        if isinstance(
            parsed,
            (list, tuple, set),
        ):
            return {
                str(item)
                for item in parsed
            }

    except (
        ValueError,
        SyntaxError,
    ):
        pass

    return {
        text
    }


def transport_mode(
    road_type,
):
    if road_type == "Sea Lane":
        return "sea"

    if road_type == "River":
        return "river"

    return "road"


def nearest_transport(
    place_metric,
    segments_metric,
    prefix,
):
    joined = gpd.sjoin_nearest(
        place_metric,
        segments_metric[
            [
                "itinere_id",
                "road_name",
                "road_type",
                "transport_mode",
                "geometry",
            ]
        ],
        how="left",
        distance_col=(
            f"{prefix}_distance_m"
        ),
        lsuffix="place",
        rsuffix=prefix,
    )

    if joined.empty:
        return None

    row = (
        joined
        .sort_values(
            f"{prefix}_distance_m"
        )
        .iloc[0]
    )

    def get_value(
        base_name,
    ):
        for candidate in [
            f"{base_name}_{prefix}",
            base_name,
        ]:
            if candidate in row.index:
                return row[
                    candidate
                ]

        return None

    return {
        "itinere_id":
            get_value(
                "itinere_id"
            ),
        "road_name":
            get_value(
                "road_name"
            ),
        "road_type":
            get_value(
                "road_type"
            ),
        "transport_mode":
            get_value(
                "transport_mode"
            ),
        "distance_km":
            float(
                row[
                    f"{prefix}_distance_m"
                ]
            )
            / 1000.0,
    }


def main():

    required = [
        PLACES_PATH,
        ROADS_PATH,
        MAPPING_PATH,
        TRANSFER_LOG_PATH,
        CANDIDATES_PATH,
    ]

    missing = [
        path
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required files:\n"
            + "\n".join(
                str(path)
                for path in missing
            )
        )


    places = gpd.read_file(
        PLACES_PATH
    )

    roads = gpd.read_file(
        ROADS_PATH
    )

    mapping = pd.read_csv(
        MAPPING_PATH
    )

    transfer_log = pd.read_csv(
        TRANSFER_LOG_PATH
    )

    candidates = pd.read_csv(
        CANDIDATES_PATH
    )


    places[
        "routing_type_set"
    ] = (
        places[
            "routing_types"
        ]
        .apply(
            parse_routing_types
        )
    )


    roads[
        "transport_mode"
    ] = (
        roads[
            "road_type"
        ]
        .apply(
            transport_mode
        )
    )


    mapping[
        "pleiades_id"
    ] = (
        mapping[
            "pleiades_id"
        ]
        .astype(int)
    )


    transfer_ids = set(
        transfer_log[
            "pleiades_id"
        ]
        .astype(int)
        .tolist()
    )


    candidate_by_id = {
        int(row["id"]):
        row
        for _, row
        in candidates.iterrows()
    }


    land = roads[
        roads[
            "transport_mode"
        ]
        != "sea"
    ].to_crs(
        "EPSG:3035"
    )

    sea = roads[
        roads[
            "transport_mode"
        ]
        == "sea"
    ].to_crs(
        "EPSG:3035"
    )


    print(
        "\n=== ADRIATIC MARITIME "
        "ACCESS AUDIT ==="
    )


    for pattern in TARGET_PATTERNS:

        matches = places[
            places[
                "title"
            ]
            .str.contains(
                pattern,
                case=False,
                na=False,
                regex=False,
            )
        ].copy()


        print(
            "\n"
            + "=" * 72
        )

        print(
            f"Search: {pattern}"
        )

        if matches.empty:

            print(
                "No matching Pleiades "
                "routing place found."
            )

            continue


        for _, place in (
            matches.iterrows()
        ):

            pleiades_id = int(
                place[
                    "id"
                ]
            )

            point = (
                gpd.GeoDataFrame(
                    [place],
                    geometry="geometry",
                    crs=places.crs,
                )
                .to_crs(
                    "EPSG:3035"
                )
            )


            nearest_land = (
                nearest_transport(
                    point,
                    land,
                    "land",
                )
            )

            nearest_sea = (
                nearest_transport(
                    point,
                    sea,
                    "sea",
                )
            )


            mapping_match = mapping[
                mapping[
                    "pleiades_id"
                ]
                == pleiades_id
            ]


            candidate = (
                candidate_by_id.get(
                    pleiades_id
                )
            )


            print(
                f"\n{place['title']}"
            )

            print(
                f"  Pleiades ID: "
                f"{pleiades_id}"
            )

            print(
                "  Routing types: "
                f"{sorted(place['routing_type_set'])}"
            )

            print(
                "  Coordinates: "
                f"{float(place.geometry.y):.6f}, "
                f"{float(place.geometry.x):.6f}"
            )


            if mapping_match.empty:

                print(
                    "  Graph V3 mapping: "
                    "NOT MAPPED"
                )

            else:

                row = (
                    mapping_match
                    .iloc[0]
                )

                print(
                    "  Graph V3 mapping mode: "
                    f"{row.get('transport_mode')}"
                )

                print(
                    "  Graph node: "
                    f"{row.get('graph_node_id')}"
                )


            print(
                "  Existing Graph V3 "
                "maritime transfer: "
                + (
                    "YES"
                    if pleiades_id
                    in transfer_ids
                    else "NO"
                )
            )


            if candidate is None:

                print(
                    "  Maritime candidate status: "
                    "NOT PRESENT"
                )

            else:

                print(
                    "  Maritime candidate status: "
                    f"{candidate.get('candidate_status')}"
                )

                print(
                    "  Candidate land distance: "
                    f"{float(candidate.get('land_distance_km')):.3f} km"
                )

                print(
                    "  Candidate sea distance: "
                    f"{float(candidate.get('sea_distance_km')):.3f} km"
                )


            if nearest_land is not None:

                print(
                    "  Nearest non-sea segment:"
                )

                print(
                    "    "
                    f"{nearest_land['road_name']} "
                    f"[{nearest_land['road_type']}]"
                )

                print(
                    "    "
                    f"{nearest_land['distance_km']:.3f} km away"
                )


            if nearest_sea is not None:

                print(
                    "  Nearest sea lane:"
                )

                print(
                    "    "
                    f"{nearest_sea['road_name']} "
                    f"[{nearest_sea['road_type']}]"
                )

                print(
                    "    "
                    f"{nearest_sea['distance_km']:.3f} km away"
                )


    print(
        "\n=== WHAT TO LOOK FOR ==="
    )

    print(
        "A place with a very small land distance "
        "and sea distance but no Graph V3 transfer "
        "is a strong false-negative candidate."
    )

    print(
        "If it is absent from the candidate table, "
        "the likely cause is the Pleiades routing-type "
        "filter rather than the distance threshold."
    )


if __name__ == "__main__":
    main()
