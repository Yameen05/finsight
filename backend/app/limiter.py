"""Shared slowapi Limiter instance.

In-memory backend (per-process). Swap to `storage_uri="redis://..."` if you
horizontally scale.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
