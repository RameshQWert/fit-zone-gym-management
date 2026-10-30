"""Optional MongoDB event storage for analytics and future flexible content."""

import os
from datetime import datetime, timezone

from django.conf import settings

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # The relational app remains usable without the optional driver.
    MongoClient = None
    PyMongoError = Exception


def is_configured():
    return bool(getattr(settings, "MONGODB_URI", os.environ.get("MONGODB_URI", "")))


def record_event(event_name, *, user_id=None, path="", metadata=None):
    """Best-effort event storage; MongoDB outages must not break the website."""
    uri = getattr(settings, "MONGODB_URI", "")
    if not uri or MongoClient is None:
        return False
    client = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
        client[settings.MONGODB_DATABASE]["events"].insert_one({
            "event": event_name,
            "user_id": user_id,
            "path": path,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        })
        return True
    except PyMongoError:
        return False
    finally:
        if client is not None:
            client.close()
