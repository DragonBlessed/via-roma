# Week 2 Development Log

## Goal

Improve the Week 1 routing prototype so historical places connect
more accurately to the Itiner-e transportation network and prepare
the graph structure for application development.

The main Week 1 limitation is that Pleiades places currently attach
to the nearest existing graph endpoint rather than the nearest point
along a transportation segment.

Week 2 will focus on:

1. Investigating disconnected graph components.
2. Projecting historical places onto transportation geometry.
3. Splitting graph edges at appropriate attachment points.
4. Rebuilding and validating the improved graph.
5. Re-running historical routes using the improved topology.

## Day 1 - Connected Component Analysis

Week 1 graph:

- Graph nodes: 1,716
- Directed edges: 5,054
- Weakly connected components: 11
- Largest component: 1,226 nodes
- Largest component percentage: 71.45%

A geographic component analysis will be used to determine whether
smaller connected components represent legitimate geographic
separation or topology problems in the current road graph.

### Results

The Week 1 transportation graph contains 11 weakly connected
components. Geographic inspection showed that most disconnected
components represent legitimate geographic or transportation-mode
separation rather than errors in graph construction.

The major components were identified as:

- Component 0: primary continental road and river network
  (1,226 nodes, 1,745 Itiner-e segments)
- Component 1: North African road network centered around the
  Carthage/Tunisia region (326 nodes, 504 segments)
- Component 2: Mediterranean sea-lane network
  (87 nodes, 185 segments)
- Component 3: Sicily road network
  (37 nodes, 46 segments)
- Component 4: Sardinia road network
  (26 nodes, 39 segments)
- Component 5: Corsica road network
  (4 nodes, 3 segments)

Components 6 through 10 contain only one physical transportation
segment each.

### Interpretation

The graph is not primarily disconnected because of coordinate
precision or graph-construction errors.

Several major components are naturally separated by geography.
For example, Sicily, Sardinia, Corsica, and the North African road
network do not share land-road endpoints with the continental
network.

The Mediterranean sea-lane data also forms its own component because
sea routes are not yet connected to terrestrial road networks through
port-transfer nodes.

This suggests that the final application should model the network as
multimodal rather than attempting to artificially merge all
components.

Future routing can connect:

road network
→ port
→ sea lane
→ port
→ road network

Component 10, consisting of the isolated Colle S. Andrea segment near
Rome, may warrant additional topology inspection because it exists
inside the geographic area covered by the large continental
component.

No graph topology was modified during this analysis.

## Day 2 - Project Historical Places onto Transportation Geometry

The Week 1 prototype attached each Pleiades place to the nearest
existing graph endpoint. This produced relatively large attachment
distances because settlements located near the middle of long road
segments could be several kilometers from either endpoint.

A new spatial projection step was implemented to project each
routing-relevant Pleiades place onto the nearest point along the
actual Itiner-e transportation geometry.

Results:

- Pleiades places processed: 3,009
- Itiner-e transportation segments: 2,527
- Mean distance to network: 2.979 km
- Median distance to network: 0.926 km
- 25th percentile: 0.188 km
- 75th percentile: 3.571 km
- Maximum distance: 55.732 km

Projection classifications:

- Automatic (<= 2 km): 1,877
- Review (2-5 km): 576
- Far (> 5 km): 556

Distance thresholds:

- Within 0.25 km: 878 (29.18%)
- Within 0.5 km: 1,218 (40.48%)
- Within 1 km: 1,542 (51.25%)
- Within 2 km: 1,877 (62.38%)
- Within 5 km: 2,453 (81.52%)
- Within 10 km: 2,802 (93.12%)
- Within 20 km: 2,952 (98.11%)

Important test places projected very closely to the transportation
network:

- Roma: 0.038 km
- Capua: 0.312 km
- Parthenope/Neapolis: 0.360 km
- Beneventum/Maleventum: 0.019 km
- Brundisium/Brentesion: 0.103 km

The projection output stores both the closest point on the
transportation segment and the position of that point along the
segment using a normalized segment fraction.

This provides the information needed to split transportation edges
at settlement attachment points when constructing Graph v2.

## Day 3 - Construct Graph v2 with Projected Place Nodes

Graph v2 was constructed by inserting accepted Pleiades place
projections into their corresponding Itiner-e transportation
segments.

Only places classified as automatic projections (within 2 km of
the network) were considered for automatic insertion.

A maritime safeguard was also applied. Places projected onto a
Sea Lane were only accepted when their routing types included
port, harbor, or anchorage.

### Projection Results

- Automatic projections considered: 1,877
- Non-maritime Sea Lane projections excluded: 37
- Accepted Graph-v2 projections: 1,840
- Itiner-e segments receiving projected places: 996

Projected locations occurring within 10 meters along the same
Itiner-e segment were allowed to share a graph node. Projections
within 10 meters of an original segment endpoint reused the
existing endpoint.

Internal projection nodes from different Itiner-e segments were
not automatically merged. This avoids creating unsupported
intersections when geometries happen to cross.

### Graph v2 Results

- Original Itiner-e segments loaded: 2,527
- Graph nodes: 3,466
- New internal split nodes: 1,750
- Physical subsegments: 4,277
- Directed graph edges: 8,554
- Pleiades places mapped to Graph-v2 nodes: 1,840
- Weakly connected components: 11
- Largest component: 2,381 nodes (68.70%)

Graph v2 preserved the same 11 weakly connected components found
in the Week 1 graph, indicating that splitting transportation
segments did not artificially connect or disconnect portions of
the network.

### Distance Conservation

Original physical network distance:

162,360.748705 km

Graph-v2 physical network distance:

162,360.748705 km

Absolute difference:

0.000000000058 km

Zero-length intervals skipped:

0

The effectively zero distance difference confirms that splitting
the original transportation geometries changed the graph topology
without changing the physical length of the network.

The increase in physical subsegments also exactly matches the
number of newly inserted internal nodes:

4,277 - 2,527 = 1,750

Likewise, the directed-edge increase was:

8,554 - 5,054 = 3,500

which equals two directed edges for each of the 1,750 inserted
split nodes.

Graph v2 therefore passed the initial structural and distance
conservation checks.

## Day 4 - Graph v2 Validation

Graph v2 was validated against the original Week 1 graph to ensure
that inserting projected settlement nodes did not alter the existing
transportation topology or shortest-path costs.

### Endpoint Preservation

All original graph endpoints were successfully preserved:

- Week 1 endpoints: 1,716
- Matched in Graph v2: 1,716
- Missing endpoints: 0

### Component Preservation

Both graphs contain 11 weakly connected components.

Each Week 1 component mapped entirely to exactly one Graph v2
component.

- Component splits detected: False
- Component merges detected: False

Component numeric IDs changed in several cases because components
are numbered after sorting them by size. The underlying connectivity
was not changed.

### Shortest-Path Regression Testing

Twenty deterministic source/destination pairs from the largest
component were tested using NetworkX.

For every pair, the Week 1 and Graph v2 shortest-path distances
matched exactly within floating-point precision.

- Validation pairs: 20
- Maximum distance difference: 0.000000000000 km

The tested routes ranged from approximately 29 km to over 1,350 km.

This provides strong evidence that splitting original transportation
segments introduced additional routing nodes without changing the
costs of travel between original endpoints.

### Place-Node Validation

Graph v2 contains 1,840 place-to-node mappings.

- Mappings referencing missing graph nodes: 0

Important test locations:

- Roma: node 2818, Rome-Tusculum, 0.038 km from network
- Capua: node 2210, Capua-Minturnae, 0.312 km
- Parthenope/Neapolis: node 106, Neapolis-Capua, 0.360 km
- Beneventum/Maleventum: node 2196, Beneventum-Aeclanum, 0.019 km
- Brundisium/Brentesion: node 86, Brundisium-Uria, 0.103 km

All five places belong to the primary continental component.

### Roma to Capua Reference Route

A Graph v2 shortest route from Roma to Capua was calculated using
NetworkX as an independent reference implementation.

- Roma graph node: 2818
- Capua graph node: 2210
- Route nodes: 35
- Route edges: 34
- Route distance: 197.564324 km

The independently summed route-edge distances also totaled
197.564324 km, producing a difference of 0.000000000000 km.

The route was exported to GeoJSON and visually inspected in QGIS.
It follows the Graph v2 transportation geometry as expected.

### Validation Result

- Endpoint preservation: PASS
- Component preservation: PASS
- Old shortest-path preservation: PASS
- Place-node references: PASS
- Overall validation: PASS

Graph v2 is now considered sufficiently stable to serve as the
routing graph for the first Via Roma application prototype.

## Day 5 - Custom Dijkstra Integration with Graph v2

The custom Dijkstra implementation developed during Week 1 was
integrated with Graph v2 and validated against NetworkX.

Unlike the Day 4 shortest-path regression tests, which used NetworkX
as an independent reference implementation, Day 5 tested Via Roma's
own Dijkstra implementation directly on the improved Graph-v2
topology.

### Historical Place Route Validation

Twenty deterministic source/destination pairs were selected from
Pleiades places mapped to the largest connected component of Graph v2.

For every route, the custom Dijkstra result was compared against
NetworkX's weighted shortest-path implementation.

Results:

- Validation routes tested: 20
- Custom Dijkstra vs NetworkX matches: 20/20
- Maximum distance difference: 0.000000000000 km
- Maximum reconstructed edge-sum difference: 0.000000000000 km

The validation routes included both short and long-distance paths
across the transportation network.

Examples included:

- Interocrium -> Careiae: 124.180262 km
- Lucera Castle -> Rostrata Villa: 345.137244 km
- Campobasso -> Ad Rota(s): 678.653781 km
- Salvium -> Pietra Papa: 1,065.959010 km
- Temesa/Tempsa -> Forum Fulvii Valentinum: 1,122.854435 km

For every test, the sum of the individual Graph-v2 edge distances
returned by the custom algorithm also matched the reported shortest
path distance exactly.

This confirms that the custom implementation correctly preserves
MultiDiGraph edge keys as well as shortest-path costs.

### Roma to Capua Custom Route

The Roma-to-Capua reference route was recalculated using the custom
Dijkstra implementation.

Results:

- Roma graph node: 2818
- Capua graph node: 2210
- Route nodes: 35
- Route edges: 34
- Custom Dijkstra distance: 197.564324 km
- NetworkX reference distance: 197.564324 km
- Independent edge sum: 197.564324 km
- Custom vs NetworkX difference: 0.000000000000 km
- Custom vs edge-sum difference: 0.000000000000 km

The custom route was exported to GeoJSON as:

`first_real_route_v2_custom.geojson`

### Validation Result

- 20 validation pairs: PASS
- Custom Dijkstra vs NetworkX: PASS
- Custom edge reconstruction: PASS
- Roma -> Capua: PASS
- Overall: PASS

The custom Dijkstra implementation is now considered validated for
distance-based routing on Graph v2.

NetworkX will remain useful as a development and regression-testing
reference, but it is not required for Via Roma's production routing
algorithm.

## Day 6 - Routing Service Layer

A reusable application routing service was created around Graph v2
and the validated custom Dijkstra implementation.

The new `RoutingService` loads Graph v2 and the Pleiades-to-node
mapping once and provides application-level operations for:

- exact Pleiades place lookup
- place-name search
- custom Dijkstra routing
- route segment reconstruction
- transportation-mode distance summaries
- GeoJSON-compatible route geometry

### Service Data

- Graph nodes: 3,466
- Directed graph edges: 8,554
- Mapped Pleiades places: 1,840
- Unique place graph nodes: 1,817

The difference between mapped places and unique graph nodes is
expected because some nearby Pleiades records intentionally share
the same Graph-v2 node.

### Place Lookup and Search

Exact Pleiades lookup correctly resolved:

- Roma: Pleiades 423025, Graph node 2818
- Capua: Pleiades 432754, Graph node 2210

Case-insensitive partial-name search was also validated. Searching
for `Roma` returned Roma as the highest-priority exact match followed
by partial matches.

### Roma to Capua Service Route

The application routing service calculated the Roma-to-Capua route
using the custom Dijkstra implementation.

Results:

- Distance: 197.564324 km
- Independent segment sum: 197.564324 km
- Route nodes: 35
- Route edges: 34
- GeoJSON route coordinates: 623
- Distance by mode: 197.564324 km road

The service reconstructed all 34 Graph-v2 route segments and produced
a GeoJSON-compatible LineString suitable for an API response or web
map.

### Validation Result

- Exact place lookup: PASS
- Place-name search: PASS
- Reference route distance: PASS
- Segment reconstruction: PASS
- Route structure: PASS
- GeoJSON geometry: PASS
- Overall: PASS

Via Roma now has a reusable routing-service layer separating the
routing implementation and Graph-v2 data structures from the future
FastAPI application.


## Day 7 - FastAPI Backend Prototype

A FastAPI application was created around the validated Via Roma
routing service.

The API loads Graph v2 and the historical place mapping once at
startup and exposes application-level endpoints without requiring
the API layer to directly manage NetworkX graph structures or
routing implementation details.

### API Endpoints

The initial backend provides:

- `GET /` - application information
- `GET /health` - graph and backend status
- `GET /places` - historical place-name search
- `GET /places/{pleiades_id}` - exact Pleiades place lookup
- `GET /route` - calculate a route between two mapped Pleiades places

The interactive FastAPI Swagger interface is available locally at:

`http://127.0.0.1:8000/docs`

### Place Search

The `/places` endpoint was successfully tested using historical
place-name queries such as Roma.

The endpoint performs case-insensitive partial matching while
prioritizing exact matches.

### Route API

The `/route` endpoint was successfully tested using:

- Origin: Roma, Pleiades 423025
- Destination: Capua, Pleiades 432754

The request passes the two historical places through the reusable
routing service and Via Roma's custom Dijkstra implementation.

The API returns:

- origin and destination metadata
- total route distance
- route node and edge counts
- distance grouped by transportation mode
- individual historical transportation segments
- GeoJSON-compatible route geometry

The Roma-to-Capua API result remained consistent with the validated
Graph-v2 reference route of approximately 197.564324 km.

### Result

Via Roma now has a functioning backend API capable of searching
historical places and calculating routes through Graph v2 using the
project's custom Dijkstra implementation.

This backend can now serve as the interface between the transportation
network and the future React/MapLibre frontend.