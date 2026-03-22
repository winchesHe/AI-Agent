"""Inbound pairing and security policy (US5).

Default policy: unpaired sources cannot trigger sensitive plugins.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from pydantic import BaseModel

from core.runtime.config import SecurityConfig


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class InboundSource(BaseModel):
    """Composite key identifying an inbound message origin."""

    channel: str  # e.g. "cli", "telegram", "webhook"
    sender_id: str


class PairingRecord(BaseModel):
    """Persisted trust record for a paired source."""

    channel: str
    sender_id: str
    paired_at: str  # ISO datetime
    trust_level: str  # "full" / "limited"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AccessDeniedError(Exception):
    """Raised when an inbound source lacks permission for a plugin."""

    def __init__(self, source: InboundSource, plugin_id: str) -> None:
        self.source = source
        self.plugin_id = plugin_id
        super().__init__(
            f"Access denied for {source.channel}:{source.sender_id} "
            f"on plugin '{plugin_id}'"
        )


# ---------------------------------------------------------------------------
# Pairing store
# ---------------------------------------------------------------------------

class PairingStore:
    """JSON-backed store of pairing records."""

    def __init__(self, store_path: str | None) -> None:
        self._store_path = store_path
        self._records: Dict[Tuple[str, str], PairingRecord] = {}
        if store_path:
            self._load()

    # -- public API ---------------------------------------------------------

    def is_paired(self, source: InboundSource) -> bool:
        return (source.channel, source.sender_id) in self._records

    def add_pairing(
        self, source: InboundSource, trust_level: str = "full"
    ) -> None:
        record = PairingRecord(
            channel=source.channel,
            sender_id=source.sender_id,
            paired_at=datetime.now(timezone.utc).isoformat(),
            trust_level=trust_level,
        )
        self._records[(source.channel, source.sender_id)] = record
        self._save()

    def remove_pairing(self, source: InboundSource) -> None:
        self._records.pop((source.channel, source.sender_id), None)
        self._save()

    def list_pairings(self) -> List[PairingRecord]:
        """Return all pairing records (order not guaranteed)."""
        return list(self._records.values())

    # -- persistence --------------------------------------------------------

    def _save(self) -> None:
        if not self._store_path:
            return
        data: List[dict] = [r.model_dump() for r in self._records.values()]
        os.makedirs(os.path.dirname(self._store_path) or ".", exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _load(self) -> None:
        if not self._store_path or not os.path.exists(self._store_path):
            return
        with open(self._store_path, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data:
            rec = PairingRecord(**item)
            self._records[(rec.channel, rec.sender_id)] = rec


# ---------------------------------------------------------------------------
# Inbound gate
# ---------------------------------------------------------------------------

class InboundGate:
    """Enforce inbound access policy against a pairing store."""

    def __init__(
        self, security_config: SecurityConfig, pairing_store: PairingStore
    ) -> None:
        self._config = security_config
        self._store = pairing_store

    def check_access(self, source: InboundSource, plugin_id: str) -> bool:
        if self._config.inbound_default_policy == "allow":
            return True
        if plugin_id in self._config.sensitive_plugin_ids:
            return self._store.is_paired(source)
        return True

    def enforce(self, source: InboundSource, plugin_id: str) -> None:
        if not self.check_access(source, plugin_id):
            raise AccessDeniedError(source, plugin_id)
