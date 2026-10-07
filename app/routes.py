from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from .config import MAX_UPLOAD_SIZE, UPLOAD_DIR
from .models import FileRecord
from .processor import ProcessingError, process_upload, validate_upload
from .storage import load_record, save_record

router = APIRouter(tags=["files"])


@router.post("/files/", status_code=status.HTTP_201_CREATED)
def upload_file(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    file_id = uuid.uuid4().hex
    suffix = Path(file.filename).suffix.lower()
    destination = UPLOAD_DIR / f"{file_id}{suffix}"

    try:
        with destination.open("wb") as output:
            size = 0
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise ProcessingError("File exceeds the 50 MB limit.")
                output.write(chunk)

        validate_upload(file.filename, size)
        record = FileRecord(
            id=file_id,
            filename=file.filename,
            stored_path=str(destination),
        )
        save_record(record)

        feature_count, crs, measurements = process_upload(destination, file.filename)
        record.feature_count = feature_count
        record.crs = crs
        record.status = "COMPLETED"
        save_record(record, measurements)
        return record.to_dict()
    except ProcessingError as exc:
        record = FileRecord(
            id=file_id,
            filename=file.filename,
            stored_path=str(destination),
            status="FAILED",
            error=str(exc),
        )
        save_record(record, [])
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        record = FileRecord(
            id=file_id,
            filename=file.filename,
            stored_path=str(destination),
            status="FAILED",
            error="Unable to process geospatial file.",
        )
        save_record(record, [])
        raise HTTPException(status_code=422, detail=f"Unable to process geospatial file: {exc}") from exc


@router.get("/files/{file_id}/")
def get_file(file_id: str) -> dict:
    record = load_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return {
        key: record[key]
        for key in (
            "id",
            "filename",
            "feature_count",
            "crs",
            "status",
            "error",
            "created_at",
        )
        if key in record
    }


@router.get("/files/{file_id}/measurements/")
def get_measurements(file_id: str) -> dict:
    record = load_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return {
        "file_id": file_id,
        "filename": record["filename"],
        "crs": record.get("crs"),
        "feature_count": record.get("feature_count", 0),
        "measurements": record.get("measurements", []),
    }
