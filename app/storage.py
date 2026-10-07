import json
from pathlib import Path
from threading import Lock

from .config import RESULT_DIR
from .models import FileRecord

_LOCK = Lock()


def _record_path(file_id: str) -> Path:
    return RESULT_DIR / f"{file_id}.json"


def save_record(record: FileRecord, measurements: list[dict] | None = None) -> None:
    payload = record.to_dict()
    if measurements is not None:
        payload["measurements"] = measurements
    with _LOCK:
        _record_path(record.id).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def load_record(file_id: str) -> dict | None:
    path = _record_path(file_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
