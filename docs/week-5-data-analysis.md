# Week 5 Data Analysis

## Day 1 - Roma-to-Salona Route Anomaly Investigation

Week 5 began by investigating an implausible route from Roma to Salona.

The existing application returned:

- Total distance: 1,021.997820 km
- Road distance: 1,021.997820 km
- Sea distance: 0 km
- Transfer distance: 0 km
- Route nodes: 91
- Route edges: 90

A reusable route-diagnostic script was created to inspect route distance by mode,
contiguous transportation legs, transfer edges, destination candidate status,
and nearby maritime-transfer places.

The diagnostic showed that Salona was mapped only to the road network, had
routing types `['settlement']`, used no transfer edges, and was absent from the
maritime-transfer candidate table.

### Result

The Roma-to-Salona anomaly was isolated as a transportation-network
connectivity problem rather than a failure of the custom Dijkstra algorithm.


## Day 2 - Adriatic Maritime Access Audit

A dedicated Adriatic maritime-access audit was created for:

- Salona
- Ancon(a)
- Ravenna
- Classis
- Iader
- Brundisium/Brentesion
- Dyrr(h)achium/Epidamnos

### Salona

- Pleiades ID: 197488
- Routing types: `['settlement']`
- Graph-v3 mapping mode: road
- Existing maritime transfer: no
- Maritime candidate status: not present
- Nearest road distance: 0.058935 km
- Nearest sea-lane distance: 2.586673 km
- Nearest road: Salona-Siculi
- Nearest sea lane: Brundisium-Salona

Salona was close to both land and sea transportation but was never considered
because its Pleiades routing types did not include `port`, `harbor`, or
`anchorage`.

### Ancon(a)

- Pleiades ID: 413014
- Routing types: `['port', 'settlement']`
- Graph-v3 mapping mode: road
- Existing maritime transfer: no
- Maritime candidate status: review candidate
- Nearest road distance: 0.744521 km
- Nearest sea-lane distance: 2.012142 km

Ancon(a) was correctly recognized as maritime, but missed the 2 km automatic
threshold by approximately 0.012 km.

Ravenna, Classis, and Iader were not promoted because their nearest sea-lane
distances were much larger, indicating a different geometry/data issue.

### Result

The audit identified two false-negative mechanisms:

1. historically maritime places can be omitted when source metadata lacks a
   maritime type
2. legitimate ports can narrowly miss the conservative automatic threshold


## Day 3 - Curated Maritime Candidate Overrides

A curated override layer was added:

`data/curated/maritime_transfer_overrides.csv`

Initial reviewed places:

- Salona, Pleiades 197488
- Ancon(a), Pleiades 413014

The main `analyze_maritime_transfer_candidates.py` script was updated to:

- load curated overrides
- preserve the corrected routing-type parser
- include explicitly forced maritime candidates
- keep original Pleiades metadata separate from Via Roma's interpretation

### Updated Candidate Analysis

- Maritime places considered: 248
- Strong candidates: 48
- Review candidates: 39
- Already same component: 3
- Far candidates: 158
- Component-merging candidates: 245

Salona:

- Candidate status: review candidate
- Land distance: 0.058935 km
- Sea distance: 2.586673 km
- Would merge components: true

Ancon(a):

- Candidate status: review candidate
- Land distance: 0.744521 km
- Sea distance: 2.012142 km
- Would merge components: true


## Day 4 - Selective Review-Candidate Graph Integration

The Graph-v3 builder was changed so review candidates can be approved
individually instead of enabling all review candidates.

For this build:

- Curated approved review IDs: 197488 and 413014
- Strong transfers selected: 48
- Review transfers selected: 2
- Total transfer places selected: 50

Transfer certainty metadata was also differentiated so curated review
connections are not mislabeled as automatically inferred strong candidates.

### Result

Salona and Ancon(a) were incorporated without globally lowering the maritime
acceptance standard.


## Day 5 - Multimodal Graph-v3.1 Reconstruction

The Mediterranean multimodal graph was rebuilt with the two curated Adriatic
transfers.

### Graph-v3.1 Results

- Graph nodes: 15,199 -> 15,281
- Directed graph edges: 38,354 -> 38,618
- Transport split nodes created: 32
- Maritime place nodes created: 50
- Synthetic transfer connectors: 100 physical
- Synthetic directed transfer edges: 200
- Total synthetic transfer distance: 59.513793 km
- Mapped Pleiades places: 7,193
- Weak components: 25 -> 22
- Largest component: 14,931 nodes
- Largest component share: 97.71%

Ancon(a):

- Land transfer: 0.744521 km
- Sea transfer: 2.012142 km
- Total transfer distance: 2.756663 km

Salona:

- Land transfer: 0.058935 km
- Sea transfer: 2.586673 km
- Total transfer distance: 2.645608 km


## Day 6 - Roma-to-Salona Multimodal Validation

### Previous Route

- Total distance: 1,021.997820 km
- Road: 1,021.997820 km
- Sea: 0 km
- Transfer: 0 km
- Nodes: 91
- Edges: 90

### Corrected Route

- Total distance: 650.542066 km
- Road: 258.953595 km
- Sea: 386.245136 km
- Transfer: 5.343335 km
- Nodes: 33
- Edges: 32

The corrected path now follows:

Roma
-> road network
-> Ancon(a)
-> maritime transfer
-> Adriatic sea lanes
-> Salona maritime transfer
-> Salona

Sea-lane segments used:

- Ancona-Hadria
- Hadria-Salona
- Salona-Aquileia

Transfer edges used:

- Ancon(a) land transfer: 0.744521 km
- Ancon(a) sea transfer: 2.012142 km
- Salona sea transfer: 2.586673 km

### Result

The route anomaly was primarily caused by missing maritime interfaces rather
than the distance-based Dijkstra algorithm.

The corrected route is approximately 371.456 km shorter and now uses the
Adriatic maritime network.


## Day 7 - Regression Validation, Application Integration, and Week 5 Freeze

Graph-v3.1 validation results:

- Nodes: 15,281
- Directed edges: 38,618
- Weak components: 22
- Largest component: 14,931 nodes
- Largest component share: 97.71%
- Duplicate Pleiades IDs: 0

The following routes matched NetworkX exactly and also matched the independent
sum of returned edges:

- Roma -> Capua
- Roma -> Constantinopolis
- Roma -> Alexandria
- Roma -> Kourion
- Roma -> Gades
- Roma -> Salona

Roma to Capua remained unchanged:

- Distance: 197.564324 km
- Nodes: 35
- Edges: 34

Roma to Salona regression:

- Custom Dijkstra: 650.542066 km
- NetworkX: 650.542066 km
- Edge sum: 650.542066 km
- NetworkX match: true
- Edge-sum match: true

### Automated Test Suite

`pytest`:

- Tests collected: 1
- Tests passed: 1
- Tests failed: 0
- Overall: PASS

### Frontend Production Build

The Vite production build completed successfully:

- Modules transformed: 21
- Build result: PASS

Vite reported a non-failing warning that some generated JavaScript chunks
exceed 500 kB after minification. Code splitting remains a possible later
performance improvement and was not required for Week 5.

### Week 5 Result

Week 5 improved the correctness and interpretability of Via Roma's multimodal
transportation graph.

The work showed that route anomalies can result from incomplete transportation
interfaces rather than the shortest-path algorithm itself. Via Roma now
supports evidence-backed maritime exceptions while preserving original source
classifications and conservative automatic thresholds.

Potential future work includes:

- estimated travel-time routing
- Roman army movement models
- temporal network selection
- map labels and larger markers for suggested places
- immediate map markers for selected origin and destination places
