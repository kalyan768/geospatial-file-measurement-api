# Geospatial File Measurement API

A production-oriented FastAPI backend that accepts **KML** files or **ZIP archives containing a Shapefile**, extracts geospatial features, handles CRS safely, and calculates measurements.

## Features

- FastAPI REST API
- Upload `.kml` or `.zip` Shapefile archives
- Feature-level geometry and attribute extraction
- Supports Point, LineString, Polygon and common Multi* geometries
- Polygon area calculation in square metres (`m²`)
- LineString length calculation in metres (`m`)
- Points return no measurement
- Geographic CRS such as EPSG:4326 is transformed to a suitable UTM projected CRS before measurement
- Projected CRS using metres is retained when appropriate
- Graceful handling of unsupported geometries
- ZIP path traversal protection
- 50 MB upload limit
- Persistent JSON result storage for simple local deployment
- Automated tests
- Swagger/OpenAPI documentation

## Requirements

- Python 3.11+ recommended
- GDAL/GeoPandas-compatible environment for Shapefile processing
- pip

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_PUBLIC_GITHUB_URL>
cd geospatial-measurement-api
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API

### Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

### Upload and process a file

`POST /api/files/`

Form field:

- `file`: `.kml` or `.zip` containing exactly one `.shp` file

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "file=@sample.kml"
```

Example response:

```json
{
  "id": "abc123...",
  "filename": "sample.kml",
  "stored_path": ".../data/uploads/abc123.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error": null,
  "created_at": "2026-10-07T00:00:00+00:00"
}
```

### File information

`GET /api/files/{id}/`

Example:

```json
{
  "id": "abc123...",
  "filename": "survey.kml",
  "feature_count": 120,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error": null,
  "created_at": "2026-10-07T00:00:00+00:00"
}
```

### Measurements

`GET /api/files/{id}/measurements/`

Example:

```json
{
  "file_id": "abc123...",
  "filename": "survey.kml",
  "crs": "EPSG:4326",
  "feature_count": 3,
  "measurements": [
    {
      "feature_id": 0,
      "geometry_type": "Point",
      "geometry": {"type": "Point", "coordinates": [78.0, 17.0]},
      "crs": "EPSG:4326",
      "properties": {"name": "Point A"},
      "measurement": null,
      "measurement_unit": null,
      "measurement_crs": null,
      "measurement_supported": false
    },
    {
      "feature_id": 1,
      "geometry_type": "LineString",
      "geometry": {"type": "LineString", "coordinates": [[78.0,17.0],[78.01,17.0]]},
      "crs": "EPSG:4326",
      "properties": {"name": "Road"},
      "measurement": 1073.2,
      "measurement_unit": "m",
      "measurement_crs": "EPSG:32644",
      "measurement_supported": true
    }
  ]
}
```

The exact measurement values depend on the source geometry and the automatically selected projected CRS.

## Architecture

```text
app/
├── main.py          FastAPI application setup
├── routes.py        HTTP endpoints and validation
├── processor.py     Upload validation, ZIP extraction and processing orchestration
├── geospatial.py    GeoPandas/Shapely/pyproj processing and measurement logic
├── kml_parser.py    Lightweight KML parser for Placemark geometries/attributes
├── models.py        File record model
├── storage.py       Local JSON persistence
└── config.py        Runtime directories and limits
```

### File-processing flow

1. Client sends KML or zipped Shapefile using multipart/form-data.
2. API validates extension and maximum upload size.
3. Uploaded bytes are stored under `data/uploads`.
4. ZIP archives are checked for unsafe paths and exactly one `.shp` file.
5. GeoPandas reads the Shapefile; the built-in XML parser reads KML.
6. Features are normalized into a common internal representation.
7. Measurements are calculated.
8. File metadata and measurements are persisted as JSON under `data/results`.
9. API returns the file ID and processing status.

### Measurement flow

```text
Input geometry
     |
     v
Identify geometry type
     |
     +---- Point ----------> no measurement
     |
     +---- LineString -----> project to metric CRS -> length (m)
     |
     +---- Polygon ---------> project to metric CRS -> area (m²)
     |
     +---- unsupported ----> measurement = null, API continues
```

## CRS handling

Calculating distance or area directly from latitude/longitude degrees is incorrect for normal metric measurements. The service therefore transforms geometries before calculating measurements.

- KML is interpreted as EPSG:4326 because KML coordinates are longitude/latitude.
- If the source CRS is geographic, the service selects a UTM zone from the feature's representative longitude and hemisphere.
- If the source CRS is already projected and its axes use metres, the service keeps that CRS.
- If a projected CRS uses non-metric units, the service transforms to an appropriate UTM CRS.
- If a Shapefile has no CRS, the service returns no measurement rather than silently assuming a CRS.

This is a practical local-measurement strategy. For very large geometries crossing UTM zones, a production version could use a custom equal-area/equidistant CRS or geodesic calculations depending on the business requirement.

## Design decisions

### Why FastAPI?

FastAPI provides typed request handling, automatic OpenAPI documentation, clean dependency injection options, and good performance for file-processing APIs.

### Why GeoPandas/Shapely/pyproj?

- **GeoPandas**: Shapefile reading and tabular feature handling.
- **Shapely**: geometry representation and measurement operations.
- **pyproj**: CRS definitions and coordinate transformations.

### Why a lightweight KML parser?

KML support varies between GDAL installations. Parsing the core KML Placemark geometry elements directly makes the KML path predictable and avoids depending on a system-specific KML driver. The parser supports Point, LineString, Polygon and common MultiGeometry combinations.

### Why JSON persistence?

The challenge focuses on backend API and geospatial processing rather than database design. JSON persistence keeps the project easy to run locally with no database setup. A production deployment could replace `storage.py` with PostgreSQL/PostGIS or another durable database.

### Error handling

Invalid files, invalid ZIP archives, unsafe ZIP paths, unsupported extensions, oversized uploads and processing failures are handled through HTTP errors. Unsupported measurement geometry does not crash processing; its measurement is returned as `null`.

## Testing

Run:

```bash
pytest -q
```

The test suite covers:

- health endpoint
- KML parsing
- KML properties
- Point handling
- LineString length
- Polygon area
- EPSG:4326 to UTM transformation
- file upload endpoint
- file information endpoint
- measurement endpoint
- missing file handling

## GitHub submission

After testing locally:

```bash
git init
git add .
git commit -m "Build geospatial file measurement API"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/geospatial-measurement-api.git
git push -u origin main
```

Make the GitHub repository **Public**, then submit the public repository URL.

## Learning

This project demonstrates practical experience with FastAPI, multipart file uploads, geospatial file formats, GeoPandas, Shapely, pyproj, CRS transformations, REST API design, validation, error handling, automated testing, and production-oriented project structure.

## Future scope

- PostgreSQL/PostGIS persistence
- Background processing for very large files using Celery/RQ
- Authentication and API keys
- Streaming uploads and object storage such as S3
- More geospatial formats such as GeoJSON and GeoPackage
- Advanced CRS selection for large/cross-zone geometries
- Pagination for very large feature collections
- Structured logging, metrics and tracing
- Docker and CI/CD deployment
