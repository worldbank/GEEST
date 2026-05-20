# -*- coding: utf-8 -*-
"""Global in-process gate for S2S downloader tasks."""

import time
import uuid
from typing import Optional


__copyright__ = "Copyright 2024, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"


class S2STaskGate:
    """Simple global mutex-like gate for S2S task execution."""

    MAX_STALE_SECONDS = 60 * 60 * 2

    _active_token: Optional[str] = None
    _active_label: str = ""
    _active_started_at: float = 0.0

    @classmethod
    def acquire(cls, label: str) -> Optional[str]:
        """Acquire the global gate and return a token, or None if busy."""
        cls._clear_stale_lock()
        if cls._active_token:
            return None

        cls._active_token = uuid.uuid4().hex
        cls._active_label = str(label or "").strip()
        cls._active_started_at = time.monotonic()
        return cls._active_token

    @classmethod
    def release(cls, token: Optional[str]) -> None:
        """Release the gate if token matches the current active token."""
        if token and token == cls._active_token:
            cls._active_token = None
            cls._active_label = ""
            cls._active_started_at = 0.0

    @classmethod
    def active_label(cls) -> str:
        """Return human-readable label for the active owner."""
        return cls._active_label

    @classmethod
    def _clear_stale_lock(cls) -> None:
        """Clear stale lock state if it has been held unusually long."""
        if not cls._active_token or cls._active_started_at <= 0:
            return

        elapsed = time.monotonic() - cls._active_started_at
        if elapsed > cls.MAX_STALE_SECONDS:
            cls._active_token = None
            cls._active_label = ""
            cls._active_started_at = 0.0
