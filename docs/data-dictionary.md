# Data Dictionary

## Itiner-e Road Segments

| Field | Meaning | Useful? | Notes |
|---|---|---|---|
| `name` | Name or endpoints of the road segment | Yes | Useful for display and debugging |
| `type` | Road classification | Yes | Example: Main Road |
| `lowerDate` | Earliest estimated construction date | Yes | Useful for historical-period modeling |
| `lowerDateError` | Uncertainty around lower date | Yes | Important for representing chronological uncertainty |
| `upperDate` | Latest estimated construction date | Yes | Useful for historical-period modeling |
| `upperDateError` | Uncertainty around upper date | Yes | Important for representing chronological uncertainty |
| `constructionPeriod` | Named historical construction period | Yes | Example: Ptolemaic |
| `segmentCertainty` | Confidence in reconstruction | Yes | Example: Conjectured |
| `description` | Additional road description | Maybe | Useful where populated |
| `itinerary` | Ancient itinerary/source association | Maybe | Could support source display |
| `author` | Scholar or project responsible for record | Yes | Useful for provenance |
| `bibliography` | Supporting scholarly source | Yes | Important for historical source attribution |
| `_lengthInKm` | Length of segment in kilometers | Yes | Can be used directly as Dijkstra edge weight |
| `_id` | Internal road segment identifier | Yes | Useful primary key |
| `passability.backward` | Whether edge can be traversed backward | Yes | Useful for directed graph construction |
| `passability.forward` | Whether edge can be traversed forward | Yes | Useful for directed graph construction |
| `lengthGeo` | Additional geometric length field | Probably no | Appears NULL in sample; `_lengthInKm` is more immediately useful |
| `geometry` | Geographic LineString | Yes | Core road geometry for map + graph construction |

## Pleiades Places

| Field | Meaning | Useful? | Notes |
|---|---|---|---|
| `id` | Pleiades place identifier | Yes | Best stable identifier for places |
| `title` | Place name/title | Yes | Main city/place display name |
| `uri` | Pleiades page URL | Yes | Can link users to original scholarly record |
| `representative_latitude` | Representative latitude | Yes | Used to place settlement on map |
| `representative_longitude` | Representative longitude | Yes | Used to place settlement on map |
| `location_precision` | Precision of geographic location | Yes | Useful for uncertainty handling |
| `bounding_box_wkt` | Geographic bounding box | Maybe | Could be useful for regions or uncertain locations |
| `description` | Description of ancient place | Yes | Good for map information panel |
| `details` | Additional details | Maybe | Contains HTML in some records; may need cleaning |
| `provenance` | Origin of the data/record | Yes | Useful for source attribution |
| `created` | Date Pleiades record was created | No | Database metadata, not historical chronology |

## Initial Observations

- Pleiades contains 42,314 place records.
- Itiner-e contains 16,554 route segment records in the downloaded dataset.
- Itiner-e provides segment length, chronology, certainty, bibliography, and directional passability.
- Pleiades provides stable place IDs, names, representative coordinates, location precision, descriptions, and provenance.
- Itiner-e road construction dates should not yet be treated as road abandonment dates.