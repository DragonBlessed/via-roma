## Day 1 - React and MapLibre Frontend Foundation

The initial Via Roma frontend was created using React, TypeScript,
Vite, and MapLibre GL JS.

FastAPI CORS support was added so the local React development server
can communicate with the backend.

The frontend successfully connected to the `/health` endpoint and
displayed live Graph-v2 statistics:

- Graph nodes: 3,466
- Directed edges: 8,554
- Mapped Pleiades places: 1,840

A MapLibre map was successfully initialized and centered on the
Mediterranean/Italian region.

MapLibre v6 required explicit Vite worker configuration before the
basemap could render correctly.

### Result

The basic frontend-to-backend application path is now operational:

React
→ FastAPI
→ RoutingService
→ Graph v2

The frontend can now be extended with historical place search and
route visualization.

## Day 2 - Historical Place Search and Route Selection

The Via Roma frontend was connected to the FastAPI historical-place
search endpoint.

Two searchable route-planning fields were added:

- Origin
- Destination

Each field queries the `/places` API endpoint as the user types and
displays matching Pleiades locations.

A short debounce delay was added so the frontend does not send a new
API request for every individual keystroke.

Search results display both the historical place name and its Pleiades
identifier. Selecting a result stores the complete mapped place record,
including the Pleiades ID required by the routing API.

### Validation

The interface was successfully tested using:

- Origin: Roma
- Roma Pleiades ID: 423025
- Destination: Capua
- Capua Pleiades ID: 432754

After both places were selected, the frontend correctly displayed:

`Roma -> Capua`

and retained the corresponding Pleiades identifiers:

`423025 -> 432754`

### Result

Via Roma can now interactively search the backend's 1,840 mapped
historical places and select graph-compatible route origins and
destinations.

The next step is to pass those selected Pleiades IDs to the `/route`
endpoint and display the returned GeoJSON route on the MapLibre map.

## Day 3 - End-to-End Route Calculation and Map Visualization

The Via Roma frontend was connected to the FastAPI `/route` endpoint.

After selecting an origin and destination, the frontend now sends the
corresponding Pleiades IDs to the backend and requests a route through
Graph v2.

The resulting route is calculated using Via Roma's custom Dijkstra
implementation and returned to the frontend as GeoJSON-compatible
geometry.

### Route Visualization

MapLibre was extended to:

- draw the returned route as a line
- place markers at the origin and destination
- automatically fit the map to the calculated route
- display loading and route-error states
- display route statistics in the sidebar

The route visualization was successfully tested using:

- Origin: Roma
- Origin Pleiades ID: 423025
- Destination: Capua
- Destination Pleiades ID: 432754

Results:

- Distance: 197.56 km
- Route nodes: 35
- Transportation segments: 34
- Road distance: 197.56 km

The displayed route follows the Graph-v2 transportation geometry
between Roma and Capua.

### Result

Via Roma now has its first complete end-to-end application workflow:

historical place search
→ Pleiades place selection
→ FastAPI route request
→ RoutingService
→ custom Dijkstra algorithm
→ Graph v2
→ GeoJSON route
→ MapLibre visualization

This represents the first interactive browser-based demonstration of
Via Roma's core historical routing system.

## Day 4 - Transportation Network Visualization

Via Roma was extended to display the complete Graph-v2 transportation
network underneath calculated routes.

A new FastAPI `/network` endpoint exports Graph v2 as a GeoJSON
FeatureCollection for the frontend.

Because Graph v2 stores most physical transportation segments as two
directed edges, the network export removes reverse-direction duplicates
before sending the data to MapLibre.

### Network Export

Graph v2 contains:

- Directed edges: 8,554
- Physical transportation subsegments: 4,277

The `/network` endpoint was validated with:

- GeoJSON type: FeatureCollection
- Physical features returned: 4,277

Each transportation feature includes:

- Itiner-e ID
- road name
- road type
- transportation mode
- segment distance
- LineString geometry

### Frontend Visualization

MapLibre now loads the exported transportation network and displays it
beneath calculated routes.

Transportation modes are visually distinguished:

- roads
- rivers
- sea lanes

A visibility checkbox was added so the user can toggle the complete
transportation network without removing the currently calculated route.

### Route Validation

The visualization was tested using a route from:

- Roma
- Pleiades 423025

to:

- Brundisium/Brentesion
- Pleiades 442509

The calculated route returned:

- Distance: 549.27 km
- Nodes: 73
- Transportation segments: 72
- Road distance: 549.27 km

The calculated route was rendered as a prominent line over the
underlying Graph-v2 transportation network.

### Result

Via Roma can now visually show both the transportation graph used by
the routing algorithm and the shortest path selected through that graph.

This makes the application's routing behavior directly interpretable
on the map instead of displaying route geometry without network context.

## Day 5 - Interactive Transportation Segment Inspection

Via Roma's map was extended so the transportation network is not only
visible but can also be inspected interactively.

### Segment Interaction

Transportation-network and calculated-route segments can now be
selected directly from the MapLibre map.

Interactive behavior includes:

- pointer cursor when hovering over transportation geometry
- clicking a network or calculated-route segment
- visually highlighting the selected segment
- displaying metadata for the selected transportation segment
- clearing the previous highlight when the route selection changes

Calculated-route segments are prioritized when they overlap the
background transportation network so the user can inspect the actual
path selected by the routing algorithm.

### Route Geometry

Calculated routes were changed from one combined GeoJSON LineString
into a FeatureCollection containing the individual Graph-v2 route
segments.

The route still appears visually continuous, but each component now
retains its own transportation metadata and route position.

### Segment Metadata

The application can expose information including:

- Itiner-e ID
- transportation name
- road type
- transportation mode
- segment distance
- historical certainty
- construction-period information
- position within the calculated route

Historical chronology fields are preserved as source metadata and are
not interpreted as the complete operational lifespan of a road.

### Validation

Interactive inspection was tested with the Roma to
Brundisium/Brentesion route.

The route continued to calculate and render correctly:

- Origin: Roma
- Destination: Brundisium/Brentesion
- Distance: approximately 549.27 km
- Route nodes: 73
- Route segments: 72

The complete transportation network remained visible beneath the
calculated route.

### Result

Via Roma's map now functions as an exploratory GIS interface rather
than only a route display.

Users can:

1. view the reconstructed transportation network
2. calculate a shortest path
3. visually compare the route with surrounding transportation links
4. inspect individual historical transportation segments

## Day 6 - Demo Hardening and Network Performance

Via Roma was hardened for more reliable live demonstration and repeated
frontend use.

### Transportation Network Caching

The Graph-v2 transportation network export is now cached by the routing
service.

Instead of rebuilding the 4,277-feature GeoJSON transportation network
for every `/network` request, Via Roma now constructs the network once
per backend process and reuses the cached result.

The network cache is warmed when the FastAPI application starts so the
frontend does not need to trigger the initial Graph-v2 conversion during
normal use.

### Response Compression

FastAPI was configured with GZip middleware for larger API responses.

This is particularly useful for the `/network` endpoint because the
transportation network contains thousands of LineString coordinates.

### Network Loading Feedback

The frontend now explicitly reports transportation-network loading
status.

After successful initialization, the Route Planner displays:

`Network loaded: 4,277 segments`

This makes network availability visible during startup and provides
clearer feedback during demonstrations.

### Disconnected Network Handling

Graph-v2 connected-component membership is now indexed by the routing
service.

Before running Dijkstra, Via Roma checks whether the selected origin and
destination belong to the same transportation component.

Requests between disconnected transportation networks now return a
user-facing routing error instead of producing an internal server error.

This behavior reflects the current Graph-v2 topology, which intentionally
contains geographically separated transportation components.

### Route State Hardening

When a new route calculation begins, any previous route visualization
and selected-segment highlight are cleared.

This prevents a previously successful route from remaining visible when
a later routing request fails.

### Validation

The hardened prototype continued to route successfully from:

- Roma
- Pleiades 423025

to:

- Brundisium/Brentesion
- Pleiades 442509

Results remained:

- Distance: 549.27 km
- Route nodes: 73
- Route segments: 72
- Road distance: 549.27 km

The complete background transportation network also loaded successfully:

- Physical transportation features: 4,277

### Result

Via Roma is now more suitable for live demonstration.

The core frontend and backend workflow remains functional while network
loading, repeated API requests, disconnected-route handling, and stale
route state are handled more reliably.

## Day 7 - Prototype Validation and Week 3 Freeze

The Week 3 Via Roma prototype was validated from a fresh backend and
frontend startup before establishing a stable development checkpoint.

### Backend Regression Test

The existing automated routing test suite was executed with pytest.

Result:

- Tests passed: 1
- Tests failed: 0
- Overall: PASS

### FastAPI Validation

The backend was restarted from a clean process and all major prototype
endpoints were tested successfully.

`GET /health` returned:

- Status: ok
- Graph nodes: 3,466
- Directed graph edges: 8,554
- Mapped Pleiades places: 1,840
- Unique place nodes: 1,817

`GET /network` returned:

- Physical transportation features: 4,277

Historical place search was tested using Roma and successfully returned
Pleiades 423025 as the primary result.

### Route Validation

The Roma-to-Capua route was recalculated through the API.

Results:

- Origin: Roma
- Destination: Capua
- Distance: 197.564324 km
- Route nodes: 35
- Route segments: 34
- HTTP result: 200 OK

The frontend demonstration was also tested with:

- Roma to Brundisium/Brentesion
- Origin Pleiades ID: 423025
- Destination Pleiades ID: 442509
- HTTP result: 200 OK

Place autocomplete requests for Roma, Capua, and
Brundisium/Brentesion also returned successfully.

### Production Frontend Build

The React/TypeScript frontend was compiled using the Vite production
build.

Result:

- Modules transformed: 21
- Build completed successfully
- Build time: approximately 886 ms
- Production output generated in `frontend/dist`

Vite reported a bundle-size optimization warning for chunks larger than
500 kB. This does not prevent the prototype from building or running and
can be addressed later if deployment performance becomes a priority.

### Full Application Validation

The complete application stack was confirmed operational:

historical place search
→ Pleiades place selection
→ FastAPI request
→ RoutingService
→ custom Dijkstra algorithm
→ Graph v2
→ route segment reconstruction
→ GeoJSON
→ MapLibre visualization

The application also successfully loads the complete 4,277-segment
transportation network for comparison with calculated routes.

### Result

Week 3 concludes with a stable interactive Via Roma prototype.

The application now supports:

- React and MapLibre map visualization
- FastAPI backend integration
- Pleiades historical-place search
- interactive origin and destination selection
- custom Dijkstra shortest-path routing
- route distance and mode summaries
- complete Graph-v2 transportation-network visualization
- transportation-network visibility controls
- clickable transportation and route segments
- segment metadata inspection
- cached transportation-network export
- compressed large API responses
- network loading feedback
- user-facing handling of disconnected graph components
- successful production frontend compilation

The Week 3 prototype is considered sufficiently stable to serve as the
baseline for subsequent historical, temporal, and multimodal features.