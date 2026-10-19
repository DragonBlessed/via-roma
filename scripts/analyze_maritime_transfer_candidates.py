import argparse
import ast
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

MARITIME_PLACE_TYPES = {
    "port",
    "harbor",
    "anchorage",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose candidate transfers between non-sea transportation "
            "and sea-lane components at maritime Pleiades places. "
            "This script does not modify the graph."
        )
    )

    parser.add_argument(
        "--scope",
        default="mediterranean",
        help="Regional file prefix, e.g. mediterranean or italy.",
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=None,
        help=(
            "Optional graph pickle path. Defaults to "
            "data/processed/<scope>_graph_v2_candidate.pkl."
        ),
    )

    parser.add_argument(
        "--place-nodes",
        type=Path,
        default=None,
        help=(
            "Optional place-node mapping CSV. Defaults to "
            "data/processed/<scope>_graph_v2_candidate_place_nodes.csv."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--automatic-km",
        type=float,
        default=2.0,
        help="Distance threshold for a strong candidate on each side.",
    )

    parser.add_argument(
        "--review-km",
        type=float,
        default=5.0,
        help="Distance threshold for a review candidate on each side.",
    )

    return parser.parse_args()


def parse_routing_types(value):
    """
    Normalize routing_types values from GeoJSON/CSV.

    Handles ordinary Python lists, GeoPandas NumPy-array values,
    valid list strings such as "['port', 'settlement']", and
    NumPy-style CSV strings such as "['port' 'settlement']".
    """

    if value is None:
        return set()

    if isinstance(value, float) and pd.isna(value):
        return set()

    # GeoPandas may return list-valued GeoJSON properties as NumPy arrays.
    if (
        not isinstance(value, (str, bytes))
        and hasattr(value, "tolist")
    ):
        converted = value.tolist()

        if isinstance(converted, (list, tuple, set)):
            return {
                str(item).strip()
                for item in converted
                if str(item).strip()
            }

    if isinstance(value, (list, tuple, set)):
        return {
            str(item).strip()
            for item in value
            if str(item).strip()
        }

    text = str(value).strip()

    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, (list, tuple, set)):
            return {
                str(item).strip()
                for item in parsed
                if str(item).strip()
            }

        if isinstance(parsed, str):
            return {parsed.strip()}

    except (ValueError, SyntaxError):
        pass

    # pandas can serialize a NumPy array without commas:
    #     ['port' 'settlement']
    import re

    quoted = re.findall(
        r"""['"]([^'"]+)['"]""",
        text,
    )

    if quoted:
        return {
            item.strip()
            for item in quoted
            if item.strip()
        }

    return {text} if text else set()


def mode_from_road_type(road_type):
    if road_type == "Sea Lane":
        return "sea"
    if road_type == "River":
        return "river"
    return "road"


def component_index(graph):
    result = {}

    for component_id, component_nodes in enumerate(
        sorted(
            nx.weakly_connected_components(graph),
            key=len,
            reverse=True,
        )
    ):
        for node_id in component_nodes:
            result[node_id] = component_id

    return result


def itinere_component_index(graph, component_by_node):
    """
    Map each Itiner-e segment to the weak component(s) containing
    its Graph-v2 edges.
    """
    components_by_itinere = {}

    for source, target, key, attrs in graph.edges(
        keys=True,
        data=True,
    ):
        itinere_id = attrs.get("itinere_id")

        if itinere_id is None:
            continue

        itinere_id = int(itinere_id)
        component_id = component_by_node.get(source)

        if component_id is None:
            continue

        components_by_itinere.setdefault(
            itinere_id,
            set(),
        ).add(component_id)

    return components_by_itinere


def one_component(component_set):
    if not component_set:
        return None

    if len(component_set) == 1:
        return next(iter(component_set))

    # This should be unusual: one original Itiner-e segment should
    # normally remain inside a single weak component after splitting.
    return ",".join(str(value) for value in sorted(component_set))


def nearest_segments(places_metric, segments_metric, prefix):
    """
    Return one nearest transportation segment for every maritime place.
    """
    if len(segments_metric) == 0:
        raise RuntimeError(f"No {prefix} transportation segments found.")

    selected = segments_metric[
        [
            "itinere_id",
            "road_name",
            "road_type",
            "transport_mode",
            "geometry",
        ]
    ].copy()

    joined = gpd.sjoin_nearest(
        places_metric,
        selected,
        how="left",
        distance_col=f"{prefix}_distance_m",
        lsuffix="place",
        rsuffix=prefix,
    )

    joined = (
        joined
        .sort_values(f"{prefix}_distance_m")
        .drop_duplicates(subset="id")
        .copy()
    )

    # sjoin_nearest suffixes right-hand columns when names collide.
    # Normalize the relevant names so downstream code is stable.
    rename_candidates = {
        f"itinere_id_{prefix}": f"{prefix}_itinere_id",
        f"road_name_{prefix}": f"{prefix}_road_name",
        f"road_type_{prefix}": f"{prefix}_road_type",
        f"transport_mode_{prefix}": f"{prefix}_transport_mode",
        "itinere_id": f"{prefix}_itinere_id",
        "road_name": f"{prefix}_road_name",
        "road_type": f"{prefix}_road_type",
        "transport_mode": f"{prefix}_transport_mode",
    }

    # Avoid renaming left-side columns if geopandas used explicit
    # left/right suffixes for a collision.
    actual_renames = {}
    for old, new in rename_candidates.items():
        if old in joined.columns and new not in joined.columns:
            actual_renames[old] = new

    joined = joined.rename(columns=actual_renames)

    joined[f"{prefix}_distance_km"] = (
        joined[f"{prefix}_distance_m"] / 1000.0
    )

    keep = [
        "id",
        f"{prefix}_itinere_id",
        f"{prefix}_road_name",
        f"{prefix}_road_type",
        f"{prefix}_transport_mode",
        f"{prefix}_distance_km",
    ]

    missing = [column for column in keep if column not in joined.columns]
    if missing:
        raise RuntimeError(
            f"Missing expected columns after nearest-{prefix} join: {missing}. "
            f"Available columns: {list(joined.columns)}"
        )

    return joined[keep]


def candidate_status(row, automatic_km, review_km):
    land_component = row.get("land_component")
    sea_component = row.get("sea_component")

    if pd.isna(row.get("land_distance_km")) or pd.isna(
        row.get("sea_distance_km")
    ):
        return "missing_side"

    if (
        land_component is not None
        and sea_component is not None
        and str(land_component) == str(sea_component)
    ):
        return "already_same_component"

    worst_distance = max(
        float(row["land_distance_km"]),
        float(row["sea_distance_km"]),
    )

    if worst_distance <= automatic_km:
        return "strong_candidate"

    if worst_distance <= review_km:
        return "review_candidate"

    return "far"


def main():
    args = parse_args()

    scope = (
        args.scope.strip()
        .lower()
        .replace(" ", "_")
    )

    processed = PROJECT_ROOT / "data" / "processed"

    places_path = processed / f"{scope}_routing_places.geojson"
    roads_path = processed / f"{scope}_itinere_roads.geojson"

    graph_path = args.graph or (
        processed / f"{scope}_graph_v2_candidate.pkl"
    )

    place_nodes_path = args.place_nodes or (
        processed / f"{scope}_graph_v2_candidate_place_nodes.csv"
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_output = output_dir / f"{scope}_maritime_transfer_candidates.csv"
    geojson_output = output_dir / f"{scope}_maritime_transfer_candidates.geojson"

    required = [
        places_path,
        roads_path,
        graph_path,
        place_nodes_path,
    ]

    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required files:\n"
            + "\n".join(str(path) for path in missing)
        )

    print("\n=== MARITIME TRANSFER DIAGNOSTIC ===")
    print(f"Scope: {scope}")
    print(f"Places: {places_path}")
    print(f"Transportation: {roads_path}")
    print(f"Graph: {graph_path}")
    print(f"Place mapping: {place_nodes_path}")

    places = gpd.read_file(places_path)
    roads = gpd.read_file(roads_path)

    roads["itinere_id"] = roads["itinere_id"].astype(int)
    roads["transport_mode"] = roads["road_type"].apply(mode_from_road_type)

    places["routing_type_set"] = places["routing_types"].apply(
        parse_routing_types
    )

    maritime_places = places[
        places["routing_type_set"].apply(
            lambda values: bool(values & MARITIME_PLACE_TYPES)
        )
    ].copy()

    maritime_places["maritime_types"] = maritime_places[
        "routing_type_set"
    ].apply(
        lambda values: ",".join(
            sorted(values & MARITIME_PLACE_TYPES)
        )
    )

    land_segments = roads[
        roads["transport_mode"] != "sea"
    ].copy()

    sea_segments = roads[
        roads["transport_mode"] == "sea"
    ].copy()

    print(f"\nMaritime Pleiades places: {len(maritime_places):,}")
    print(f"Non-sea segments: {len(land_segments):,}")
    print(f"Sea-lane segments: {len(sea_segments):,}")

    if len(maritime_places) == 0:
        raise RuntimeError("No maritime Pleiades places found in this scope.")

    maritime_metric = maritime_places.to_crs("EPSG:3035")
    land_metric = land_segments.to_crs("EPSG:3035")
    sea_metric = sea_segments.to_crs("EPSG:3035")

    nearest_land = nearest_segments(
        maritime_metric,
        land_metric,
        "land",
    )

    nearest_sea = nearest_segments(
        maritime_metric,
        sea_metric,
        "sea",
    )

    with open(graph_path, "rb") as f:
        graph = pickle.load(f)

    component_by_node = component_index(graph)
    components_by_itinere = itinere_component_index(
        graph,
        component_by_node,
    )

    place_nodes = pd.read_csv(place_nodes_path)
    place_nodes["pleiades_id"] = place_nodes["pleiades_id"].astype(int)

    current_mapping = place_nodes[
        [
            "pleiades_id",
            "graph_node_id",
            "transport_mode",
            "distance_to_network_km",
        ]
    ].copy()

    current_mapping = current_mapping.rename(
        columns={
            "graph_node_id": "current_graph_node_id",
            "transport_mode": "current_transport_mode",
            "distance_to_network_km": "current_mapping_distance_km",
        }
    )

    current_mapping["current_component"] = current_mapping[
        "current_graph_node_id"
    ].map(component_by_node)

    base = maritime_places[
        [
            "id",
            "title",
            "routing_types",
            "maritime_types",
            "geometry",
        ]
    ].copy()

    base["longitude"] = base.geometry.x
    base["latitude"] = base.geometry.y

    candidates = (
        base
        .merge(nearest_land, on="id", how="left")
        .merge(nearest_sea, on="id", how="left")
        .merge(
            current_mapping,
            left_on="id",
            right_on="pleiades_id",
            how="left",
        )
    )

    candidates["land_component"] = candidates[
        "land_itinere_id"
    ].apply(
        lambda value: (
            one_component(
                components_by_itinere.get(int(value), set())
            )
            if pd.notna(value)
            else None
        )
    )

    candidates["sea_component"] = candidates[
        "sea_itinere_id"
    ].apply(
        lambda value: (
            one_component(
                components_by_itinere.get(int(value), set())
            )
            if pd.notna(value)
            else None
        )
    )

    candidates["would_merge_components"] = candidates.apply(
        lambda row: (
            pd.notna(row["land_component"])
            and pd.notna(row["sea_component"])
            and str(row["land_component"])
            != str(row["sea_component"])
        ),
        axis=1,
    )

    candidates["candidate_status"] = candidates.apply(
        lambda row: candidate_status(
            row,
            args.automatic_km,
            args.review_km,
        ),
        axis=1,
    )

    candidates["max_transfer_distance_km"] = candidates[
        [
            "land_distance_km",
            "sea_distance_km",
        ]
    ].max(axis=1)

    candidates = candidates.sort_values(
        by=[
            "candidate_status",
            "max_transfer_distance_km",
            "title",
        ]
    ).reset_index(drop=True)

    print("\n=== CANDIDATE STATUS ===")
    print(candidates["candidate_status"].value_counts())

    print("\n=== CURRENT MAPPING MODE ===")
    print(
        candidates["current_transport_mode"]
        .fillna("not_mapped")
        .value_counts()
    )

    print("\n=== DISTANCE SUMMARY (KM) ===")
    print(
        candidates[
            [
                "land_distance_km",
                "sea_distance_km",
                "max_transfer_distance_km",
            ]
        ].describe()
    )

    merge_count = int(candidates["would_merge_components"].sum())
    print(
        "\nCandidates whose nearest land and sea segments are "
        f"currently in different components: {merge_count:,}"
    )

    print("\n=== 30 STRONGEST COMPONENT-MERGING CANDIDATES ===")

    preview = candidates[
        candidates["would_merge_components"]
    ].sort_values(
        "max_transfer_distance_km"
    ).head(30)

    preview_columns = [
        "id",
        "title",
        "maritime_types",
        "land_transport_mode",
        "land_distance_km",
        "land_component",
        "sea_distance_km",
        "sea_component",
        "candidate_status",
    ]

    if len(preview):
        print(preview[preview_columns].to_string(index=False))
    else:
        print("No component-merging candidates found.")

    # Save CSV without geometry.
    csv_df = pd.DataFrame(candidates.drop(columns="geometry"))
    csv_df.to_csv(csv_output, index=False)

    # Save the maritime place point layer for QGIS inspection.
    output_gdf = gpd.GeoDataFrame(
        candidates,
        geometry="geometry",
        crs="EPSG:4326",
    )
    output_gdf.to_file(
        geojson_output,
        driver="GeoJSON",
    )

    print("\n=== OUTPUT ===")
    print(csv_output)
    print(geojson_output)
    print(
        "\nDiagnostic complete. The graph was not modified."
    )


if __name__ == "__main__":
    main()
