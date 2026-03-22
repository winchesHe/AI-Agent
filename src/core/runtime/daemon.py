"""DaemonLoop — asyncio long-running daemon with periodic probes and backoff.

Runs an infinite async loop that periodically executes internal health probes.
Handles SIGTERM/SIGINT for graceful shutdown and applies exponential backoff
with jitter on consecutive probe failures.
"""

from __future__ import annotations

import asyncio
import logging
import random
import signal
import time
from typing import Any, Dict

from .config import ConfigurationProfile, DaemonConfig, DaemonRetryConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DaemonLoop
# ---------------------------------------------------------------------------


class DaemonLoop:
    """Async daemon that periodically runs health probes."""

    def __init__(self, profile: ConfigurationProfile) -> None:
        self._profile = profile
        self._daemon_cfg: DaemonConfig = profile.daemon or DaemonConfig()
        self._retry_cfg: DaemonRetryConfig = self._daemon_cfg.retry
        self._running = False
        self._start_time: float = 0.0
        self._consecutive_failures: int = 0

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Main async loop: probe at fixed intervals, backoff on failure."""
        self._running = True
        self._start_time = time.monotonic()
        logger.info("Daemon started")

        try:
            while self._running:
                try:
                    await self._probe()
                    self._consecutive_failures = 0
                except Exception:
                    self._consecutive_failures += 1
                    if self._consecutive_failures <= self._retry_cfg.max_retries:
                        delay = self._backoff_delay(self._consecutive_failures)
                        logger.warning(
                            "Probe failed (attempt %d/%d), retrying in %.2fs",
                            self._consecutive_failures,
                            self._retry_cfg.max_retries,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            "Probe failed %d consecutive times, resetting counter",
                            self._consecutive_failures,
                        )
                        self._consecutive_failures = 0

                await asyncio.sleep(self._daemon_cfg.probe_interval_seconds)
        finally:
            logger.info("Daemon shutting down")
            await asyncio.sleep(self._daemon_cfg.shutdown_grace_seconds)
            self._running = False

    async def _probe(self) -> Dict[str, Any]:
        """Internal health probe (placeholder).

        Returns a status dict indicating that the configuration is loaded
        and the daemon is operational.
        """
        config_ok = self._profile is not None
        uptime = time.monotonic() - self._start_time
        status: Dict[str, Any] = {
            "config_loaded": config_ok,
            "uptime_seconds": round(uptime, 2),
            "consecutive_failures": self._consecutive_failures,
        }
        logger.debug("Probe result: %s", status)
        return status

    def _shutdown(self) -> None:
        """Set the stop flag so the loop exits on next iteration."""
        self._running = False

    def is_running(self) -> bool:
        """Return whether the daemon loop is active."""
        return self._running

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _backoff_delay(self, attempt: int) -> float:
        """Compute exponential backoff delay with jitter.

        ``base_delay * multiplier^attempt``, capped at ``max_delay``.
        Jitter adds ``uniform(0, delay * 0.1)``.
        """
        delay = self._retry_cfg.base_delay_seconds * (
            self._retry_cfg.multiplier ** attempt
        )
        delay = min(delay, self._retry_cfg.max_delay_seconds)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


async def run_daemon(profile: ConfigurationProfile) -> None:
    """Create a :class:`DaemonLoop` and run it with signal handling."""
    loop = DaemonLoop(profile)

    aio_loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        aio_loop.add_signal_handler(sig, loop._shutdown)

    await loop.run()
