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

        self._network_geojson_cache = None
        

        # -------------------------------------------------
        # Load Graph v2 once
        # -------------------------------------------------

        with open(
            self.graph_path,
            "rb",
        ) as f:

            self.graph = pickle.load(f)


        self._component_by_node = (
            self._component_index()
        )


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

    def _component_index(self) -> dict:
        """
        Assign every graph node to a weakly connected
        transportation component.
        """

        component_by_node = {}
        component_id = 0

        for start_node in self.graph.nodes:

            if start_node in component_by_node:
                continue

            stack = [start_node]

            component_by_node[
                start_node
            ] = component_id

            while stack:

                node = stack.pop()

                neighbors = set(
                    self.graph.successors(
                        node
                    )
                )

                neighbors.update(
                    self.graph.predecessors(
                        node
                    )
                )

                for neighbor in neighbors:

                    if (
                        neighbor
                        in component_by_node
                    ):
                        continue

                    component_by_node[
                        neighbor
                    ] = component_id

                    stack.append(
                        neighbor
                    )

            component_id += 1

        return component_by_node

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
    
    def network_geojson(self) -> dict:
        """
        Return Graph v2's physical transportation network as GeoJSON.

        Graph v2 represents most physical subsegments using two directed
        edges. Reverse-direction duplicates are removed before returning
        the network to the frontend.
        """

        if self._network_geojson_cache is not None:
            return self._network_geojson_cache

        features = []
        seen_physical_edges = set()

        for source, target, key, data in self.graph.edges(
            keys=True,
            data=True,
        ):
            coordinates = data.get("coordinates")

            if not coordinates or len(coordinates) < 2:
                continue

            itinere_id = data.get("itinere_id")
            subsegment_index = data.get(
                "subsegment_index"
            )

            # Forward and backward versions of the same physical
            # subsegment use opposite source/target nodes.
            endpoint_pair = tuple(
                sorted(
                    (
                        int(source),
                        int(target),
                    )
                )
            )

            physical_key = (
                itinere_id,
                subsegment_index,
                endpoint_pair,
            )

            if physical_key in seen_physical_edges:
                continue

            seen_physical_edges.add(
                physical_key
            )

            feature = {
                "type": "Feature",
                "properties": {
                    "itinere_id": (
                        int(itinere_id)
                        if itinere_id is not None
                        else None
                    ),
                    "road_name": data.get(
                        "road_name"
                    ),
                    "road_type": data.get(
                        "road_type"
                    ),
                    "transport_mode": data.get(
                        "transport_mode"
                    ),
                    "distance_km": float(
                        data.get(
                            "distance_km",
                            0.0,
                        )
                    ),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [
                            float(coordinate[0]),
                            float(coordinate[1]),
                        ]
                        for coordinate
                        in coordinates
                    ],
                },
            }

            features.append(
                feature
            )

        result = {
            "type": "FeatureCollection",
            "feature_count": len(features),
            "features": features,
        }

        self._network_geojson_cache = result

        return result


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
        
        origin_component = (
            self._component_by_node[
                source_node
            ]
        )

        destination_component = (
            self._component_by_node[
                target_node
            ]
        )

        if (
            origin_component
            != destination_component
        ):
            raise ValueError(
                "No route currently exists between "
                f"{origin['name']} and "
                f"{destination['name']} because "
                "they belong to disconnected "
                "transportation networks."
            )


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
    
    def _place_from_row(
        self,
        row,
    ) -> dict:

        def optional_string(value):
            if pd.isna(value):
                return None

            return str(value)

        def optional_int(value):
            if pd.isna(value):
                return None

            return int(value)

        return {
            "pleiades_id": int(
                row["pleiades_id"]
            ),
            "name": str(
                row["title"]
            ),
            "graph_node_id": int(
                row["graph_node_id"]
            ),
            "itinere_id": optional_int(
                row["itinere_id"]
            ),
            "road_name": optional_string(
                row["road_name"]
            ),
            "road_type": optional_string(
                row["road_type"]
            ),
            "transport_mode": optional_string(
                row["transport_mode"]
            ),
            "distance_to_network_km": float(
                row[
                    "distance_to_network_km"
                ]
            ),
            "longitude": float(
                row["node_longitude"]
            ),
            "latitude": float(
                row["node_latitude"]
            ),
        }