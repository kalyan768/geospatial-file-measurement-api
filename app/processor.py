from __future__ import annotations

import shutil
import uuid
import zipfile
from pathlib import Path

from .config import MAX_UPLOAD_SIZE, UPLOAD_DIR
from .geospatial import normalize_features, read_geospatial_file


class ProcessingError(ValueError):
    """Raised for invalid or unsupported geospatial uploads."""


def validate_upload(filename: str, size: int) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".zip", ".kml"}:
        raise ProcessingError("Only .kml files or .zip Shapefile archives are supported.")
    if size > MAX_UPLOAD_SIZE:
        raise ProcessingError(f"File exceeds the {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.")


def extract_shapefile_archive(zip_path: Path, destination: Path) -> Path:
    if not zipfile.is_zipfile(zip_path):
        raise ProcessingError("Uploaded .zip file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path) as archive:
        members = archive.namelist()
        if any(Path(member).is_absolute() or ".." in Path(member).parts for member in members):
            raise ProcessingError("ZIP archive contains unsafe paths.")
        shp_members = [member for member in members if member.lower().endswith(".shp")]
        if len(shp_members) != 1:
            raise ProcessingError("ZIP must contain exactly one .shp file.")
        archive.extractall(destination)

    shp_path = destination / shp_members[0]
    if not shp_path.exists():
        raise ProcessingError("Shapefile could not be extracted.")
    return shp_path


def process_upload(source_path: Path, original_filename: str) -> tuple[int, str | None, list[dict]]:
    work_dir = UPLOAD_DIR / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        if source_path.suffix.lower() == ".zip":
            data_path = extract_shapefile_archive(source_path, work_dir)
        else:
            data_path = work_dir / source_path.name
            shutil.copy2(source_path, data_path)

        features, crs = read_geospatial_file(str(data_path))
        measurements = normalize_features(features, crs)
        return len(measurements), crs.to_string() if crs else None, measurements
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
