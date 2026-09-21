from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from backend.routing.service import (
    RoutingService,
)


# ---------------------------------------------------------
# Application setup
# ---------------------------------------------------------

app = FastAPI(
    title="Via Roma API",
    description=(
        "Backend API for the Via Roma "
        "Roman Transportation Network Explorer."
    ),
    version="0.1.0",
)


# Load Graph v2 and its place mapping once when the
# application starts.
router = RoutingService()


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "application": "Via Roma",
        "description": (
            "Roman Transportation Network Explorer"
        ),
        "api_version": "0.1.0",
    }


# ---------------------------------------------------------
# Health / graph status
# ---------------------------------------------------------

@app.get("/health")
def health():

    stats = router.stats()

    return {
        "status": "ok",
        "graph": {
            "nodes": (
                stats[
                    "graph_nodes"
                ]
            ),
            "edges": (
                stats[
                    "graph_edges"
                ]
            ),
            "mapped_places": (
                stats[
                    "mapped_places"
                ]
            ),
            "unique_place_nodes": (
                stats[
                    "unique_place_nodes"
                ]
            ),
        },
    }


# ---------------------------------------------------------
# Place search
# ---------------------------------------------------------

@app.get("/places")
def search_places(
    query: str = Query(
        ...,
        min_length=1,
        description=(
            "Case-insensitive historical "
            "place-name search."
        ),
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
):

    results = router.search_places(
        query,
        limit=limit,
    )

    return {
        "query": query,
        "count": len(
            results
        ),
        "results": results,
    }


# ---------------------------------------------------------
# Exact Pleiades place
# ---------------------------------------------------------

@app.get(
    "/places/{pleiades_id}"
)
def get_place(
    pleiades_id: int,
):

    try:

        return router.get_place(
            pleiades_id
        )

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc


# ---------------------------------------------------------
# Route
# ---------------------------------------------------------

@app.get("/route")
def route(
    origin: int = Query(
        ...,
        description=(
            "Origin Pleiades place ID."
        ),
    ),
    destination: int = Query(
        ...,
        description=(
            "Destination Pleiades place ID."
        ),
    ),
):

    try:

        result = router.route(
            origin,
            destination,
        )

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc


    return result