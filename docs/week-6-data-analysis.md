## Day 7 - Regression Validation, Application Integration, and Week 6 Freeze

Week 6 concluded with regression validation of the transportation graph,
chronology analysis, API, routing behavior, and frontend production build.

### Graph-v3.1 Validation

The stable Mediterranean graph remained unchanged:

- Nodes: 15,281
- Directed edges: 38,618
- Mapped Pleiades places: 7,193
- Physical transportation features: 19,314

The `/network` endpoint also retained all chronology metadata required by the
frontend:

- itinere ID
- road name
- road type
- transport mode
- distance
- certainty
- lower date
- upper date
- construction period

### Chronology Regression

The temporal metadata audit continued to reproduce the Week 6 results:

- Processed regional segments: 12,460
- Raw regional records recovered: 12,460
- Regional IDs missing from raw source: 0
- Both usable lower and upper dates: 13
- Lower date only: 283
- Upper date only: 7
- Neither usable date: 12,157
- Construction period present: 2,833
- Records with normalized lowerDate greater than upperDate: 0

Live graph chronology validation:

- Unique Itiner-e IDs represented: 12,460
- Inconsistent chronology across split graph edges: 0
- Source-to-graph chronology mismatches: 0
- Regional Itiner-e IDs absent from graph: 0
- Synthetic transfer edges unexpectedly carrying chronology: 0

The chronology-evidence analysis also reproduced the expected classifications:

- No chronology: 9,512
- Construction attribution only: 2,645
- Construction attribution and one boundary: 183
- One boundary only: 107
- Explicit range only: 8
- Construction attribution and explicit range: 5

Construction-period parsing remained:

- Parsed ranges: 1,556
- Parsed single dates: 1,247
- Unparsed: 30

### Route Regression

The following previously validated routes remained unchanged:

- Roma -> Capua: 197.564324 km
- Roma -> Constantinopolis: 1,727.762033 km
- Roma -> Alexandria: 2,124.975053 km
- Roma -> Kourion: 2,706.720601 km
- Roma -> Gades: 2,260.424236 km
- Roma -> Salona: 650.542066 km

All six route regression checks passed within the configured numerical
tolerance.

Roma to Capua therefore remains unchanged as the primary road-network
regression.

Roma to Salona also remains unchanged after the Week 5 maritime corrections and
continues to serve as the primary multimodal regression.

### Automated Test Suite

`pytest`:

- Tests collected: 1
- Tests passed: 1
- Tests failed: 0
- Overall: PASS
- Test time: 0.22 seconds

### Frontend Production Build

The Vite production build completed successfully:

- Vite version: 8.3.1
- Modules transformed: 21
- Build result: PASS
- Build time: 477 ms

Generated assets included:

- index.html: 0.42 kB
- MapLibre worker: 509.70 kB
- CSS bundle: 85.29 kB
- JavaScript bundle: 1,272.82 kB

The JavaScript bundle remains relatively large, but this did not prevent the
production build from succeeding and remains a later optimization opportunity.

### API Regression

The live FastAPI application returned the expected stable values:

- Graph nodes: PASS
- Directed graph edges: PASS
- Mapped places: PASS
- Physical network features: PASS
- Chronology metadata in `/network`: PASS

All six route requests also returned their expected distances.

### Manual Frontend Validation

Week 6 manual frontend validation includes:

- suggested historical places remain visible
- suggested-place circles remain black
- origin markers appear immediately after selection
- destination markers appear immediately after selection
- historical segment certainty is displayed
- construction attribution is displayed when available
- raw chronology value 0 is displayed as unknown
- 312 BCE -> 0 is displayed as an unknown end date
- 0 -> 0 is displayed as unavailable chronology
- chronology-evidence coloring affects the background transportation network
- calculated routes retain their transportation-mode coloring
- disabling chronology-evidence mode restores the normal network colors

### Week 6 Result

Week 6 established and validated a defensible temporal-data model for Via Roma.

The work demonstrated that the transportation graph correctly preserves the
chronology information contained in Itiner-e, while also showing that usable
explicit lower and upper dates are too sparse for automatic Empire-wide
year-specific network reconstruction.

Via Roma now distinguishes between:

- transportation-network topology
- source chronology evidence
- construction or formalization attribution
- chronology uncertainty
- claims about historical operational availability

The frontend can now expose and visualize chronology evidence without implying
that sparse date fields represent complete road lifespans.

The existing routing graph and all major route regressions remained unchanged
throughout the chronology work.

Potential future work includes:

- historical-period context overlays
- construction-attribution filters
- century-based evidence visualization
- curated historical network snapshots
- political and provincial boundary changes by historical period
- uncertainty-aware temporal presentation
- estimated travel-time routing
- Roman army movement models