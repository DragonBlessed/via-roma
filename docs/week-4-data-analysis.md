## Day 1 - Regional Pipeline Generalization and Italy Regression

Week 4 began by converting the Italy-specific preprocessing and graph
construction workflow into a reusable regional pipeline.

The existing Italy scripts were generalized so the same processing steps could
be run against named geographic scopes without changing the core graph logic.

The regional workflow now supports:

- configurable geographic bounding boxes
- reusable Pleiades routing-place extraction
- reusable Itiner-e transportation extraction
- regional place-to-network projection
- regional Graph-v2 construction
- separate candidate outputs so the stable Italy MVP is not overwritten

The Italy scope was rerun through the generalized scripts as a regression test.

### Italy Regression Validation

The generalized pipeline reproduced the previous Italy results:

- Routing-relevant Pleiades places: 3,009
- Itiner-e transportation segments: 2,527
- Automatic projections: 1,877
- Review projections: 576
- Far projections: 556
- Graph nodes: 3,466
- New internal split nodes: 1,750
- Physical subsegments: 4,277
- Directed edges: 8,554
- Mapped places: 1,840
- Weakly connected components: 11
- Largest component: 2,381 nodes
- Largest component share: 68.70%

The Roma-to-Capua route also remained unchanged:

- Distance: 197.564324 km
- Route nodes: 35
- Route edges: 34

### Result

The geographic processing pipeline is no longer tied to Italy.

The existing Italy MVP behavior was preserved exactly, establishing a stable
baseline before expanding to the wider Mediterranean.


## Day 2 - Mediterranean Data Extraction and Place Projection

The generalized preprocessing pipeline was used to create the first
Mediterranean-scale Via Roma dataset.

The Mediterranean development extent was configured as:

`(-10, 28, 42, 48)`

This produced a substantially larger historical transportation dataset.

### Mediterranean Regional Subset

The regional extraction produced:

- Routing-relevant Pleiades places: 12,324
- Itiner-e transportation segments: 12,460

Routing-place type assignments included:

- settlements: 9,836
- stations: 1,216
- forts: 1,111
- fort-2: 274
- ports: 231
- fortified settlements: 113
- harbors: 17
- anchorages: 2
- castellum: 1

A single place may contribute more than one routing type, so these counts
represent type assignments rather than unique places.

### Place-to-Network Distance Analysis

Nearest-network distances were measured using EPSG:3035.

Results:

- Mean distance: 6.085660 km
- Median distance: 1.128137 km
- 25th percentile: 0.233348 km
- 75th percentile: 4.439335 km
- Maximum distance: 361.498115 km

Threshold counts:

- <= 0.25 km: 3,195 places
- <= 0.50 km: 4,545 places
- <= 1 km: 5,915 places
- <= 2 km: 7,364 places
- <= 5 km: 9,541 places
- <= 10 km: 10,980 places
- <= 20 km: 11,769 places

The place-projection stage classified:

- Automatic projections: 7,364
- Review projections: 2,177
- Far projections: 2,783

### Result

Via Roma now has a Mediterranean-scale Pleiades and Itiner-e input dataset.

The same 2 km automatic-projection threshold used for the Italy MVP remains
usable at the larger scale, while review and far categories preserve uncertain
matches for later inspection.


## Day 3 - Mediterranean Graph-v2 Construction

The projected Mediterranean places were integrated into a regional Graph-v2
candidate using the existing split-segment topology model.

Projected places were inserted into Itiner-e geometry while preserving the
original physical transportation distance.

### Graph-v2 Results

The Mediterranean Graph-v2 candidate contained:

- Original transportation segments: 12,460
- Graph nodes: 15,199
- New internal split nodes: 6,722
- Physical subsegments: 19,182
- Directed graph edges: 38,354
- Mapped Pleiades places: 7,191
- Weakly connected components: 25
- Largest component: 14,386 nodes
- Largest component share: 94.65%

Distance conservation remained exact:

- Original physical network distance: 496,152.761713 km
- Graph-v2 physical network distance: 496,152.761713 km
- Absolute difference: 0.000000000000 km
- Zero-length intervals skipped: 0

### Route Validation

Several long-distance routes were tested.

Roma to Capua remained unchanged:

- Distance: 197.564324 km
- Nodes: 35
- Edges: 34

Additional routes included:

- Roma to Constantinopolis: approximately 2,336.92 km
- Roma to Alexandria: approximately 4,546.35 km
- Roma to Gades: approximately 2,439.94 km

Roma to Kourion remained disconnected.

### Result

The Graph-v2 topology scaled successfully from Italy to the Mediterranean
without breaking the existing terrestrial routing regression.

The larger graph also revealed an important modeling limitation: sea lanes and
terrestrial transportation existed geometrically but were not reliably joined
at historical ports.


## Day 4 - Maritime Transfer Diagnosis and Routing-Type Bug Fix

A dedicated maritime-transfer diagnostic was created to inspect where
Pleiades ports, harbors, and anchorages could connect terrestrial
transportation to sea lanes.

During this analysis, a parsing bug was discovered in the handling of
`routing_types`.

GeoPandas could load list-valued GeoJSON properties as NumPy arrays. Some CSV
serializations therefore appeared in forms such as:

`['port' 'settlement']`

The previous parser expected standard Python list syntax with commas and could
misclassify mixed-type maritime places.

The parser was updated to support:

- Python lists
- tuples and sets
- NumPy-array values
- standard list strings
- NumPy-style quoted strings without commas

### Corrected Maritime Diagnostic

After the parser fix, the Mediterranean dataset contained:

- Maritime Pleiades places: 247
- Non-sea transportation segments: 11,972
- Sea-lane segments: 488

Candidate classifications:

- Strong candidates: 48
- Review candidates: 38
- Already in the same component: 3
- Far candidates: 158

Current mapping modes among maritime places:

- road: 155
- not mapped: 78
- sea: 9
- river: 5

Of the 247 maritime places, 244 had nearest terrestrial and sea segments in
different graph components.

### Result

The maritime diagnostic exposed the main reason the Mediterranean Graph-v2
could not use sea travel effectively.

It also identified a conservative set of 48 strong port-transfer candidates
whose nearest terrestrial and sea connections both fall within the automatic
acceptance threshold.


## Day 5 - Multimodal Graph-v3 Maritime Transfers

An experimental Graph-v3 builder was created to add explicit maritime
connections without directly welding arbitrary road and sea nodes together.

Each accepted transfer uses the following structure:

terrestrial segment

→ projected terrestrial node

→ Pleiades maritime place node

→ projected sea-lane node

→ sea network

When required, the original Itiner-e segment is split at the exact projected
location while preserving its original physical distance.

Synthetic transfer edges are stored separately from historical Itiner-e
geometry using:

- `transport_mode = transfer`
- `road_type = Maritime Transfer`
- `certainty = inferred_from_strong_candidate`

Only the 48 strong maritime-transfer candidates were used.

### Graph-v3 Results

Graph-v3 changed the network from:

- Nodes: 15,199 → 15,278
- Directed edges: 38,354 → 38,608
- Weak components: 25 → 22
- Largest component: 14,386 → 14,928 nodes
- Largest component share: 94.65% → 97.71%
- Mapped places: 7,191 → 7,193

New transfer construction included:

- Transportation split nodes created: 31
- Maritime place nodes created: 48
- Synthetic transfer connectors: 96 physical
- Synthetic directed transfer edges: 192
- Total synthetic transfer distance: 54.111522 km

### Result

Via Roma now contains a working multimodal transportation graph.

Road, river, sea, and inferred transfer edges can participate in the same
shortest-path calculation while remaining distinguishable in the graph
metadata.


## Day 6 - Graph-v3 Validation, Performance, and Backend Integration

Graph-v3 was validated against NetworkX while continuing to use Via Roma's
custom Dijkstra implementation for production routing.

### Route Validation

The following routes matched NetworkX exactly and also matched the independent
sum of their returned route edges.

Roma to Capua:

- Distance: 197.564324 km
- Road: 197.564324 km
- Nodes: 35
- Edges: 34

Roma to Constantinopolis:

- Distance: 1,727.762272 km
- Road: 1,477.728484 km
- Sea: 247.705315 km
- Transfer: 2.328473 km
- Nodes: 188
- Edges: 187

Roma to Alexandria:

- Distance: 2,124.976665 km
- Road: 549.266158 km
- Sea: 1,572.379681 km
- Transfer: 3.330826 km
- Nodes: 78
- Edges: 77

Roma to Kourion:

- Distance: 2,706.720601 km
- Road: 254.873848 km
- Sea: 2,451.599047 km
- Transfer: 0.247706 km
- Nodes: 48
- Edges: 47

Roma to Gades:

- Distance: 2,260.424236 km
- Road: 1,284.088133 km
- Sea: 974.975514 km
- Transfer: 1.360590 km
- Nodes: 107
- Edges: 106

The Roma-to-Capua regression remained exactly unchanged from Graph-v2.

### Performance

The Mediterranean Graph-v3 backend was benchmarked locally.

Results:

- RoutingService load time: approximately 1.701 seconds
- Initial network GeoJSON generation: approximately 1.572 seconds
- Network GeoJSON features: 19,309
- Cached network access: approximately 0.000011 seconds
- Roma-to-Alexandria route calculation: approximately 0.111 seconds
- Graph pickle size: approximately 28.26 MB
- Place-node mapping size: approximately 1.05 MB

### Backend Integration

Graph-v3 was promoted into the live FastAPI application.

`GET /health` reported:

- Graph nodes: 15,278
- Directed edges: 38,608
- Mapped places: 7,193
- Unique place nodes: 7,106

The live `/route` endpoint successfully returned the validated multimodal
Roma-to-Alexandria result.

### Result

The Mediterranean Graph-v3 is both correct and fast enough for the current
interactive prototype.

The backend now serves the expanded multimodal graph rather than the earlier
Italy-only graph.


## Day 7 - Frontend Multimodal UX and Week 4 Freeze

The frontend was updated to reflect the larger geographic scope and make
historical-place selection easier for users who may not already know Roman
place names.

### Place Discovery

The origin and destination controls were improved so users can browse
suggested historical places immediately when focusing a route field.

A dedicated suggested-places workflow was added rather than requiring users to
know a valid Roman place name before using the application.

The autocomplete interaction was also corrected so selecting a search result
does not immediately reopen the same dropdown and require a second click.

### Multimodal Visualization

The calculated-route visualization was updated so transportation modes can be
distinguished directly on the map.

The current visualization distinguishes:

- road travel
- river travel
- sea travel
- inferred maritime transfer connections

The initial MapLibre view was also widened from the earlier Italy-centered
development view to better represent Mediterranean-scale coverage.

### Week 4 Validation

The complete Week 4 system now supports:

- reusable regional preprocessing
- Mediterranean-scale Pleiades extraction
- Mediterranean-scale Itiner-e extraction
- place-to-network projection
- Graph-v2 regional topology construction
- maritime connectivity diagnostics
- explicit Graph-v3 port-transfer nodes
- road, river, sea, and transfer routing
- custom Dijkstra shortest paths
- NetworkX validation
- Mediterranean-scale FastAPI service
- cached 19,309-feature network export
- interactive MapLibre visualization
- suggested historical-place discovery
- corrected single-click autocomplete selection

### Week 4 Result

Week 4 concludes with Via Roma operating as a Mediterranean-scale multimodal
routing prototype.

The core development progression is now:

Italy Graph-v2

→ generalized regional pipeline

→ Mediterranean Graph-v2

→ maritime connectivity diagnosis

→ corrected maritime-place classification

→ Graph-v3 transfer model

→ multimodal shortest-path routing

→ NetworkX validation

→ live FastAPI integration

→ Mediterranean MapLibre interface

The largest connected component now contains 97.71% of Graph-v3 nodes, and
previously disconnected routes such as Roma to Kourion are now routable
through historically relevant maritime connections.

The Week 4 prototype is considered sufficiently stable to serve as the
baseline for the next development stage, including temporal filtering,
historical map context, weighted routing, and later database integration.
