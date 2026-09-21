from backend.routing.service import (
    RoutingService,
)


ROMA_ID = 423025

CAPUA_ID = 432754

EXPECTED_ROMA_CAPUA_KM = (
    197.564324
)

DISTANCE_TOLERANCE_KM = (
    1e-6
)


print(
    "\n=== VIA ROMA ROUTING SERVICE VALIDATION ==="
)


# ---------------------------------------------------------
# Load service
# ---------------------------------------------------------

router = RoutingService()


stats = router.stats()


print(
    "\n=== SERVICE DATA ==="
)

print(
    f"Graph nodes: "
    f"{stats['graph_nodes']:,}"
)

print(
    f"Graph edges: "
    f"{stats['graph_edges']:,}"
)

print(
    f"Mapped places: "
    f"{stats['mapped_places']:,}"
)

print(
    f"Unique place nodes: "
    f"{stats['unique_place_nodes']:,}"
)


# ---------------------------------------------------------
# Place lookup
# ---------------------------------------------------------

print(
    "\n=== PLACE LOOKUP ==="
)


roma = router.get_place(
    ROMA_ID
)

capua = router.get_place(
    CAPUA_ID
)


print(
    f"Roma: "
    f"{roma}"
)

print(
    f"Capua: "
    f"{capua}"
)


lookup_ok = (
    roma[
        "pleiades_id"
    ]
    == ROMA_ID
    and capua[
        "pleiades_id"
    ]
    == CAPUA_ID
)


# ---------------------------------------------------------
# Place search
# ---------------------------------------------------------

print(
    "\n=== PLACE SEARCH ==="
)


search_results = (
    router.search_places(
        "Roma",
        limit=10,
    )
)


for index, place in enumerate(
    search_results,
    start=1,
):

    print(
        f"{index:02d}. "
        f"{place['name']} "
        f"[{place['pleiades_id']}]"
    )


search_ok = any(
    place[
        "pleiades_id"
    ]
    == ROMA_ID
    for place
    in search_results
)


# ---------------------------------------------------------
# Route
# ---------------------------------------------------------

print(
    "\n=== ROMA -> CAPUA SERVICE ROUTE ==="
)


route = router.route(
    ROMA_ID,
    CAPUA_ID,
)


print(
    f"Origin: "
    f"{route['origin']['name']}"
)

print(
    f"Destination: "
    f"{route['destination']['name']}"
)

print(
    f"Distance: "
    f"{route['distance_km']:.6f} km"
)

print(
    f"Independent segment sum: "
    f"{route['segment_distance_km']:.6f} km"
)

print(
    f"Nodes: "
    f"{route['node_count']:,}"
)

print(
    f"Edges: "
    f"{route['edge_count']:,}"
)

print(
    f"GeoJSON coordinate count: "
    f"{len(route['geometry']['coordinates']):,}"
)

print(
    f"Distance by mode: "
    f"{route['distance_by_mode_km']}"
)


# ---------------------------------------------------------
# Route validation
# ---------------------------------------------------------

reference_difference = abs(
    route[
        "distance_km"
    ]
    - EXPECTED_ROMA_CAPUA_KM
)


segment_difference = abs(
    route[
        "distance_km"
    ]
    - route[
        "segment_distance_km"
    ]
)


distance_ok = (
    reference_difference
    <= DISTANCE_TOLERANCE_KM
)


segments_ok = (
    segment_difference
    <= DISTANCE_TOLERANCE_KM
)


structure_ok = (
    route[
        "node_count"
    ]
    == 35
    and route[
        "edge_count"
    ]
    == 34
)


geometry_ok = (
    route[
        "geometry"
    ][
        "type"
    ]
    == "LineString"
    and len(
        route[
            "geometry"
        ][
            "coordinates"
        ]
    )
    >= 2
)


print(
    "\nRoute segments:"
)


for segment in route[
    "segments"
]:

    print(
        f"{segment['route_order']:02d}. "
        f"{segment['road_name']} "
        f"[{segment['transport_mode']}] "
        f"({segment['distance_km']:.2f} km)"
    )


# ---------------------------------------------------------
# Validation summary
# ---------------------------------------------------------

print(
    "\n=== VALIDATION SUMMARY ==="
)


print(
    f"Exact place lookup: "
    f"{'PASS' if lookup_ok else 'FAIL'}"
)

print(
    f"Place-name search: "
    f"{'PASS' if search_ok else 'FAIL'}"
)

print(
    f"Reference route distance: "
    f"{'PASS' if distance_ok else 'FAIL'}"
)

print(
    f"Segment reconstruction: "
    f"{'PASS' if segments_ok else 'FAIL'}"
)

print(
    f"Route structure: "
    f"{'PASS' if structure_ok else 'FAIL'}"
)

print(
    f"GeoJSON geometry: "
    f"{'PASS' if geometry_ok else 'FAIL'}"
)


overall_ok = (
    lookup_ok
    and search_ok
    and distance_ok
    and segments_ok
    and structure_ok
    and geometry_ok
)


print()

print(
    "OVERALL: "
    + (
        "PASS"
        if overall_ok
        else "INVESTIGATE"
    )
)