# Via Roma

**Roman Transportation Network Explorer**


A capstone project for exploring and analyzing reconstructed Roman

transportation networks across different time periods.



## Planned Features



- Interactive Roman transportation map

- Historical network periods

- Settlement and road metadata

- Shortest-path routing using Dijkstra's algorithm

- Historical source attribution

- Network analysis

- Potential multimodal road, river, and sea routing



## Planned Stack



- React

- TypeScript

- MapLibre GL JS

- Python

- FastAPI

- PostgreSQL

- PostGIS

- GeoPandas

- Shapely

## Run Instructions

Via Roma currently uses:

- Python / FastAPI for the backend
- Graph v2 for transportation routing
- a Dijkstra implementation
- React + TypeScript + Vite for the frontend
- MapLibre GL JS for map visualization

### Data

Large raw and generated GIS/network files are not intended
to be stored directly in the Git repository.

The processing pipeline generates the runtime graph from the
Pleiades and Itiner-e source datasets. Required generated
runtime artifacts must therefore be created locally before
starting the backend.

### Backend

From the project root:

```powershell
conda activate roman-capstone
uvicorn backend.api.main:app --reload

From the frontend directory:

```powershell
npm install
npm run dev