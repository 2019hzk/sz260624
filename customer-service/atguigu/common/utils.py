import uuid
from datetime import datetime, UTC


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def get_utcnow() -> datetime:
    return datetime.now(tz=UTC)

