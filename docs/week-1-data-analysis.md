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