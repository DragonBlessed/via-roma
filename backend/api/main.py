from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from backend.routing.service import (
    RoutingService,
)

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
    compresslevel=5,
)


# Load Graph v2 and its place mapping once when the
# application starts.
router = RoutingService()
router.network_geojson()


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

@app.get("/network")
def network():

    return router.network_geojson()

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

@app.get("/places/suggestions")
def suggested_places(
    limit: int = Query(
        8,
        ge=1,
        le=20,
    ),
):

    results = router.suggested_places(
        limit=limit,
    )

    return {
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
        
    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(
                exc
            ),
        ) from exc


    return result