from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="Geospatial File Measurement API",
    description=(
        "Upload Shapefile ZIP archives or KML files and retrieve feature-level "
        "geometry information and CRS-safe measurements."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
