from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FileRecord:
    id: str
    filename: str
    stored_path: str
    feature_count: int = 0
    crs: str | None = None
    status: str = "PROCESSING"
    error: str | None = None
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
