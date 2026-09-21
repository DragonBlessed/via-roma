import pickle
from pathlib import Path

import pandas as pd

from backend.routing.dijkstra import (
    dijkstra_shortest_path,
)


# ---------------------------------------------------------
# Default project paths
# ---------------------------------------------------------

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DEFAULT_GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph_v2.pkl"
)

DEFAULT_PLACE_NODES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "italy_graph_v2_place_nodes.csv"
)


# ---------------------------------------------------------
# Routing service
# ---------------------------------------------------------

class RoutingService:

    def __init__(
        self,
        graph_path=DEFAULT_GRAPH_PATH,
        place_nodes_path=DEFAULT_PLACE_NODES_PATH,
    ):

        self.graph_path = Path(
            graph_path
        )

        self.place_nodes_path = Path(
            place_nodes_path
        )


        # -------------------------------------------------
        # Load Graph v2 once
        # -------------------------------------------------

        with open(
            self.graph_path,
            "rb",
        ) as f:

            self.graph = pickle.load(f)


        # -------------------------------------------------
        # Load Pleiades -> graph-node mapping once
        # -------------------------------------------------

        self.places = pd.read_csv(
            self.place_nodes_path
        )


        # Pleiades IDs should uniquely identify the routing
        # place represented by each mapping record.
        duplicate_ids = (
            self.places[
                "pleiades_id"
            ]
            .duplicated()
            .sum()
        )


        if duplicate_ids:

            raise RuntimeError(
                f"Found {duplicate_ids} duplicate "
                f"Pleiades IDs in the Graph-v2 "
                f"place mapping."
            )


        self._places_by_id = {
            int(row["pleiades_id"]): row
            for _, row
            in self.places.iterrows()
        }


    # -----------------------------------------------------
    # Basic statistics
    # -----------------------------------------------------

    def stats(
        self,
    ):

        return {
            "graph_nodes": (
                self.graph.number_of_nodes()
            ),
            "graph_edges": (
                self.graph.number_of_edges()
            ),
            "mapped_places": (
                len(
                    self.places
                )
            ),
            "unique_place_nodes": int(
                self.places[
                    "graph_node_id"
                ]
                .nunique()
            ),
        }


    # -----------------------------------------------------
    # Convert mapping row to API-friendly dictionary
    # -----------------------------------------------------

    def _place_from_row(
        self,
        row,
    ):

        return {
            "pleiades_id": int(
                row[
                    "pleiades_id"
                ]
            ),
            "name": str(
                row[
                    "title"
                ]
            ),
            "graph_node_id": int(
                row[
                    "graph_node_id"
                ]
            ),
            "itinere_id": int(
                row[
                    "itinere_id"
                ]
            ),
            "road_name": (
                None
                if pd.isna(
                    row[
                        "road_name"
                    ]
                )
                else str(
                    row[
                        "road_name"
                    ]
                )
            ),
            "road_type": (
                None
                if pd.isna(
                    row[
                        "road_type"
                    ]
                )
                else str(
                    row[
                        "road_type"
                    ]
                )
            ),
            "transport_mode": (
                None
                if pd.isna(
                    row[
                        "transport_mode"
                    ]
                )
                else str(
                    row[
                        "transport_mode"
                    ]
                )
            ),
            "distance_to_network_km": float(
                row[
                    "distance_to_network_km"
                ]
            ),
            "longitude": float(
                row[
                    "node_longitude"
                ]
            ),
            "latitude": float(
                row[
                    "node_latitude"
                ]
            ),
        }


    # -----------------------------------------------------
    # Exact Pleiades lookup
    # -----------------------------------------------------

    def get_place(
        self,
        pleiades_id,
    ):

        pleiades_id = int(
            pleiades_id
        )


        row = self._places_by_id.get(
            pleiades_id
        )


        if row is None:

            raise KeyError(
                f"Pleiades place "
                f"{pleiades_id} "
                f"is not mapped to Graph v2."
            )


        return self._place_from_row(
            row
        )


    # -----------------------------------------------------
    # Name search
    #
    # This will later support a FastAPI /places endpoint
    # and frontend autocomplete.
    # -----------------------------------------------------

    def search_places(
        self,
        query,
        limit=20,
    ):

        query = str(
            query
        ).strip()


        if not query:

            return []


        limit = max(
            1,
            int(
                limit
            ),
        )


        titles = (
            self.places[
                "title"
            ]
            .fillna("")
            .astype(str)
        )


        matches = self.places[
            titles.str.contains(
                query,
                case=False,
                regex=False,
            )
        ].copy()


        # Prefer exact name matches before partial matches.
        matches[
            "_exact_match"
        ] = (
            matches[
                "title"
            ]
            .fillna("")
            .astype(str)
            .str.casefold()
            == query.casefold()
        )


        matches = (
            matches
            .sort_values(
                by=[
                    "_exact_match",
                    "title",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .head(
                limit
            )
        )


        return [
            self._place_from_row(
                row
            )
            for _, row
            in matches.iterrows()
        ]


    # -----------------------------------------------------
    # Convert one Dijkstra edge into API-friendly data
    # -----------------------------------------------------

    def _edge_to_segment(
        self,
        source,
        target,
        key,
        route_order,
    ):

        attrs = self.graph.edges[
            source,
            target,
            key,
        ]


        coordinates = (
            attrs.get(
                "coordinates"
            )
            or []
        )


        clean_coordinates = [
            [
                float(
                    coordinate[0]
                ),
                float(
                    coordinate[1]
                ),
            ]
            for coordinate
            in coordinates
        ]


        return {
            "route_order": int(
                route_order
            ),
            "source_node": int(
                source
            ),
            "target_node": int(
                target
            ),
            "edge_key": int(
                key
            ),
            "itinere_id": (
                int(
                    attrs[
                        "itinere_id"
                    ]
                )
                if attrs.get(
                    "itinere_id"
                )
                is not None
                else None
            ),
            "road_name": (
                attrs.get(
                    "road_name"
                )
            ),
            "road_type": (
                attrs.get(
                    "road_type"
                )
            ),
            "transport_mode": (
                attrs.get(
                    "transport_mode"
                )
            ),
            "distance_km": float(
                attrs[
                    "distance_km"
                ]
            ),
            "certainty": (
                attrs.get(
                    "certainty"
                )
            ),
            "lower_date": (
                attrs.get(
                    "lower_date"
                )
            ),
            "upper_date": (
                attrs.get(
                    "upper_date"
                )
            ),
            "construction_period": (
                attrs.get(
                    "construction_period"
                )
            ),
            "coordinates": (
                clean_coordinates
            ),
        }


    # -----------------------------------------------------
    # Join route segments into one GeoJSON LineString
    # -----------------------------------------------------

    def _route_geometry(
        self,
        segments,
    ):

        route_coordinates = []


        for segment in segments:

            coordinates = segment[
                "coordinates"
            ]


            if not coordinates:

                continue


            if not route_coordinates:

                route_coordinates.extend(
                    coordinates
                )

                continue


            # Graph-v2 edge coordinates are oriented in
            # traversal direction. Adjacent edges should
            # therefore share the same boundary coordinate.
            if (
                route_coordinates[-1]
                == coordinates[0]
            ):

                route_coordinates.extend(
                    coordinates[1:]
                )

            else:

                # Keep the geometry rather than silently
                # deleting data if a future graph version
                # contains a small discontinuity.
                route_coordinates.extend(
                    coordinates
                )


        return {
            "type": "LineString",
            "coordinates": (
                route_coordinates
            ),
        }


    # -----------------------------------------------------
    # Main application routing function
    # -----------------------------------------------------

    def route(
        self,
        origin_pleiades_id,
        destination_pleiades_id,
    ):

        origin = self.get_place(
            origin_pleiades_id
        )

        destination = self.get_place(
            destination_pleiades_id
        )


        source_node = origin[
            "graph_node_id"
        ]

        target_node = destination[
            "graph_node_id"
        ]


        result = (
            dijkstra_shortest_path(
                self.graph,
                source_node,
                target_node,
                weight="distance_km",
            )
        )


        segments = []


        for route_order, (
            source,
            target,
            key,
        ) in enumerate(
            result[
                "edges"
            ],
            start=1,
        ):

            segment = (
                self._edge_to_segment(
                    source,
                    target,
                    key,
                    route_order,
                )
            )

            segments.append(
                segment
            )


        # -------------------------------------------------
        # Independent sum from returned route edges
        # -------------------------------------------------

        segment_distance_km = sum(
            segment[
                "distance_km"
            ]
            for segment
            in segments
        )


        # -------------------------------------------------
        # Distance by transportation mode
        # -------------------------------------------------

        distance_by_mode = {}


        for segment in segments:

            mode = (
                segment[
                    "transport_mode"
                ]
                or "unknown"
            )


            distance_by_mode[
                mode
            ] = (
                distance_by_mode.get(
                    mode,
                    0.0,
                )
                + segment[
                    "distance_km"
                ]
            )


        distance_by_mode = {
            mode: float(
                distance
            )
            for mode, distance
            in distance_by_mode.items()
        }


        geometry = (
            self._route_geometry(
                segments
            )
        )


        return {
            "origin": origin,
            "destination": (
                destination
            ),
            "distance_km": float(
                result[
                    "distance"
                ]
            ),
            "segment_distance_km": float(
                segment_distance_km
            ),
            "node_count": len(
                result[
                    "nodes"
                ]
            ),
            "edge_count": len(
                result[
                    "edges"
                ]
            ),
            "node_ids": [
                int(
                    node_id
                )
                for node_id
                in result[
                    "nodes"
                ]
            ],
            "distance_by_mode_km": (
                distance_by_mode
            ),
            "geometry": geometry,
            "segments": segments,
        }