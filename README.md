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
- a custom Dijkstra implementation
- React + TypeScript + Vite for the frontend
- MapLibre GL JS for map visualization

### Backend

From the project root:

```powershell
conda activate roman-capstone
uvicorn backend.api.main:app --reload

From the frontend directory:

```powershell
npm install
npm run dev