# Week 1 Data Analysis

## Itiner-e / Pleiades Integration

Initial inspection was performed on the Itiner-e Roman transportation
dataset and the Pleiades ancient-place dataset.

Itiner-e contains:

- 16,554 road segments
- Geographic LineString geometry
- Segment length
- Road classification
- Construction chronology
- Historical certainty
- Bibliographic/source information
- Directional passability
- References to associated Pleiades places

Pleiades contains:

- 42,314 places
- 34,739 places with representative coordinates
- Place classifications
- Historical names
- Chronological information
- Descriptions and provenance
- Connections between places

### Dataset ID Compatibility

A comparison was made between the Pleiades IDs embedded within
Itiner-e road segments and the IDs contained in the downloaded
Pleiades places dataset.

Results:

- Itiner-e road segments: 16,554
- Segments with at least one Pleiades reference: 13,118
- Percentage with Pleiades references: 79.24%
- Unique Pleiades IDs referenced by Itiner-e: 11,875
- IDs found in Pleiades places.csv: 11,875
- Missing IDs: 0
- Exact ID match rate: 100%

This indicates that Itiner-e and Pleiades can largely be integrated
using stable Pleiades identifiers rather than fuzzy matching place
names.

The `pleiadesPlaces` field should not, however, be interpreted as
representing only the endpoints of a road segment. Some Itiner-e
segments contain many associated Pleiades places, so the routing
graph itself must be constructed from the road geometry rather than
from these place associations.

---

## Routing Place Types

Pleiades contains many types of geographic and archaeological
features that are not useful as routing destinations. For the
initial prototype, the following types were selected:

- settlement
- station
- port
- harbor
- anchorage
- fortified-settlement
- fort
- fort-2
- fortlet
- castellum

These categories are intended to represent settlements,
transportation locations, military sites, and maritime locations
that could reasonably function as route origins or destinations.

The complete Pleiades vocabulary is much broader and includes
features such as roads, bridges, temples, cemeteries, city walls,
houses, and geographic regions, so these should not automatically
become user-selectable routing nodes.

---

## Regional Development Subset

A smaller geographic subset was created so that graph construction
and routing can be tested before processing the entire Roman world.

The current development bounding box is:

Longitude:
6° E to 19° E

Latitude:
36° N to 47.5° N

Results:

- Routing-relevant Pleiades places: 3,009
- Itiner-e transportation segments: 2,527

The resulting files are:

- `italy_routing_places.geojson`
- `italy_itinere_roads.geojson`
- `italy_place_road_proximity.csv`

Both GeoJSON outputs use geographic coordinates compatible with
standard GIS/web-map workflows.

### Geographic Caveat

The current development bounding box is referred to as the "Italy"
subset for convenience, but it is a rectangular geographic region
rather than the political boundary of Italy.

Because of this, the subset also includes portions of:

- Corsica
- Slovenia
- Croatia
- Bosnia and Herzegovina
- surrounding Adriatic areas
- portions of North Africa near the northern edge of the bounding box

This is acceptable for early routing and topology experiments, but
the subset should either be renamed to an "Italy-region development
subset" or replaced later with a proper geographic polygon filter.

---

## Settlement-to-Road Proximity Analysis

Each routing-relevant Pleiades place in the development subset was
compared with the nearest Itiner-e road segment.

Distance statistics:

- Number of places measured: 3,009
- Mean distance to nearest road: 2.979 km
- Median distance to nearest road: 0.926 km
- 25th percentile: 0.188 km
- 75th percentile: 3.571 km
- Maximum observed distance: 55.732 km

### Distance Thresholds

| Maximum Distance | Places | Percentage |
|---|---:|---:|
| 0.25 km | 878 | 29.18% |
| 0.50 km | 1,218 | 40.48% |
| 1 km | 1,542 | 51.25% |
| 2 km | 1,877 | 62.38% |
| 5 km | 2,453 | 81.52% |
| 10 km | 2,802 | 93.12% |
| 20 km | 2,952 | 98.11% |

The median routing-relevant place is less than one kilometer from
an Itiner-e road. More than 81% are within five kilometers, and
over 93% are within ten kilometers.

Several Pleiades places have a calculated distance of exactly zero
from an Itiner-e segment, indicating that their representative
coordinate lies directly on the road geometry. Examples include
stations and settlements associated with named Itiner-e routes.

### Outliers

Some locations are considerably farther from the nearest modeled
road.

The most distant place in the current subset is Saone at
approximately 55.73 km from the nearest Itiner-e segment.

Other large-distance examples include:

- Palania: ~53.01 km
- Alouka: ~52.70 km
- Rhopikon: ~49.72 km
- Ourkinion: ~49.55 km
- Agiation: ~45.69 km

Many of the largest outliers occur outside mainland Italy,
particularly in Corsica or other regions that were included because
of the rectangular development bounding box.

---

## Initial Interpretation

The results suggest that Pleiades settlements can feasibly be
attached to the Itiner-e road graph using spatial proximity.

A provisional attachment strategy for development may be:

- 0–2 km: candidate for automatic attachment
- 2–5 km: attach with caution or flag for review
- greater than 5 km: do not automatically attach without additional
  validation

These thresholds are not yet final. They will be reconsidered after
road topology has been inspected and major settlements such as Roma,
Capua, Neapolis, Beneventum, and Brundisium have been manually
checked.

The important result is that the majority of relevant locations are
close enough to the road network that attaching Pleiades places to
routing nodes appears practical.

---

## Architecture Implication

The current data supports separating the project into two related
structures:

### Physical Transportation Graph

Itiner-e LineStrings
→ road endpoints/intersections
→ graph nodes
→ weighted graph edges
→ Dijkstra routing

### Historical Place Layer

Pleiades places
→ settlement/port/station filtering
→ nearest transportation-network location
→ attached routing node

This prevents Pleiades locations from incorrectly defining the road
network itself. Instead, the actual road geometry defines the graph,
while Pleiades supplies named historical locations and metadata.

---

## Next Investigation

The next step is road topology analysis.

The Itiner-e road geometry will be examined to determine:

1. Whether neighboring road segments share exactly identical
   endpoint coordinates.
2. Whether some apparently connected segments are separated by
   small coordinate differences.
3. What spatial snapping tolerance, if any, is needed.
4. How many connected components exist after graph construction.
5. Whether important Italian routes form a sufficiently connected
   network for Dijkstra's algorithm.

After topology analysis, the next major milestone will be constructing
the first NetworkX graph from real Itiner-e geometry and calculating
a real route between two Pleiades settlements.


## Road Topology Analysis

The 2,527 Itiner-e transportation segments in the regional
development subset were inspected to determine whether adjacent
segments share common endpoint coordinates.

Results:

- Road segments: 2,527
- Total endpoints: 5,054
- Unique exact endpoint coordinates: 1,716
- Coordinates shared by multiple road segments: 1,529
- Endpoints participating in exact matches: 4,867
- Exact endpoint connectivity: 96.30%

### Coordinate Precision Test

| Matching Method | Endpoints in Shared Coordinates | Percentage |
|---|---:|---:|
| Exact coordinates | 4,867 | 96.30% |
| Rounded to 6 decimals | 4,867 | 96.30% |
| Rounded to 5 decimals | 4,882 | 96.60% |
| Rounded to 4 decimals | 4,888 | 96.72% |
| Rounded to 3 decimals | 4,892 | 96.79% |

Rounding coordinates produced only a very small increase in
connectivity. This indicates that minor coordinate precision
differences are not a major source of disconnected road segments.

Because 96.3% of endpoints already participate in exact coordinate
matches, the first graph implementation will use exact road endpoint
coordinates as graph nodes rather than applying aggressive spatial
snapping.

The remaining unmatched endpoints will be investigated after graph
construction. Some may represent legitimate termini, boundaries of
the development subset, coastal endpoints, or incomplete historical
data rather than topology errors.

## Graph Construction

The regional Itiner-e subset was converted into a NetworkX
MultiDiGraph using exact road segment endpoints as graph nodes.

Results:

- Input road segments: 2,527
- Road segments successfully loaded: 2,527
- Road segments skipped: 0
- Graph nodes: 1,716
- Directed graph edges: 5,054

Each bidirectional Itiner-e segment is represented as two directed
edges, allowing future routing logic to support directional
passability while retaining the original road metadata.

The graph preserves attributes including road name, road type,
distance, historical certainty, chronology, bibliography, and
original geometry.

Generated outputs:

- `italy_graph.pkl`
- `italy_graph_nodes.geojson`
- `italy_graph_edges.geojson`

---

## Graph Validation

The resulting transportation graph was analyzed before implementing
routing.

Results:

- Nodes: 1,716
- Directed edges: 5,054
- Weakly connected components: 11
- Largest component: 1,226 nodes
- Largest component percentage: 71.45%

Largest component sizes:

1. 1,226 nodes
2. 326 nodes
3. 87 nodes
4. 37 nodes
5. 26 nodes
6. 4 nodes
7. 2 nodes
8. 2 nodes
9. 2 nodes
10. 2 nodes

Degree statistics:

- Minimum degree: 1
- Maximum degree: 25
- Average degree: 2.95
- Degree-1 nodes: 187

The 187 degree-1 nodes correspond closely with the 187 endpoints
previously found not to participate in exact endpoint matches. This
suggests that graph construction is consistent with the raw
Itiner-e topology.

The largest connected component contains more than 71% of all graph
nodes, which is sufficient to proceed with prototype routing.

The smaller connected components will be investigated later. They
may represent geographically separated networks, legitimate road
termini, boundaries of the development subset, islands, incomplete
historical data, or road intersections that occur within LineStrings
rather than at segment endpoints.

## Historical Place Attachment

Routing-relevant Pleiades locations were attached to the nearest
existing transportation graph node.

Results:

- Places processed: 3,009
- Automatic attachments (<= 2 km): 669
- Review attachments (2-5 km): 448
- Far attachments (> 5 km): 1,892
- Places attached to largest graph component: 1,786 (59.36%)

Graph-node attachment distances:

- Mean: 9.996 km
- Median: 7.529 km
- 25th percentile: 2.537 km
- 75th percentile: 14.413 km
- Maximum: 74.454 km

These distances are substantially larger than the earlier
place-to-road-geometry distances because the prototype currently
attaches settlements to existing road endpoints rather than to the
nearest position along a road segment.

This is a known prototype limitation. A later version will project
settlements onto the nearest road geometry and insert routing nodes
at those positions.

Important test locations were successfully attached to the largest
connected component:

- Roma: node 101, 0.472 km
- Capua: node 1160, 0.558 km
- Parthenope/Neapolis: node 95, 0.450 km
- Beneventum/Maleventum: node 86, 0.314 km
- Brundisium/Brentesion: node 75, 0.201 km

These locations provide suitable test cases for the initial
Dijkstra routing implementation.


## Initial Historical Route

The custom Dijkstra implementation was successfully used to
calculate a route between Roma and Capua using the graph constructed
from real Itiner-e transportation data.

Results:

- Origin: Roma
- Origin graph node: 101
- Destination: Capua
- Destination graph node: 1160
- Connected component: 0
- Network distance: 197.67 km
- Graph nodes traversed: 22
- Road edges traversed: 21

The calculated route used a sequence of historically identified
Itiner-e segments including:

- Rome-Ad Bivium
- Ad Bivium-Ferentinum
- Fregellanum-Ferentinum
- Aquinum-Fregellanum
- Aquinum-Ad Flexum
- Ad Flexum-Teanum Sidicinum
- Teanum Sidicinum-Capua

The resulting route was exported as:

`data/processed/first_real_route.geojson`

This represents the first end-to-end demonstration of the project's
core routing pipeline:

Itiner-e geometry
→ graph construction
→ Pleiades place attachment
→ custom Dijkstra algorithm
→ calculated historical route
→ GeoJSON visualization.