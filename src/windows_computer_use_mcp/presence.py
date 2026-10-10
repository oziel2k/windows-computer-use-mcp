"""Human-presence state machine for notebook scenarios (BUG-adjacent feature).

Coffee vs going-home semantics: a short absence (within grace) is harmless and
does nothing; a long absence (past lock timeout) recommends locking, and locks
the workstation only when the operator explicitly enabled auto-lock.

- armed: master switch. Disarmed ticks report `disarmed`, never lock.
- grace_s: seconds of absence tolerated silently (default 300 = coffee run).
- lock_timeout_s: seconds of absence before `away-long` (default 900).
- auto_lock: when True AND status newly becomes away-long, lock the
  workstation via LockWorkStation. Default False. Never silent: the tick
  always reports what it did.

State persists to data/presence_state.json (same data dir convention as
known_faces) so arming survives server restarts.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ENV_PRESENCE_ARMED = "windows_computer_use_mcp_PRESENCE_ARMED"
ENV_PRESENCE_GRACE_S = "windows_computer_use_mcp_PRESENCE_GRACE_S"
ENV_PRESENCE_LOCK_TIMEOUT_S = "windows_computer_use_mcp_PRESENCE_LOCK_TIMEOUT_S"
ENV_PRESENCE_AUTO_LOCK = "windows_computer_use_mcp_PRESENCE_AUTO_LOCK"

DEFAULT_GRACE_S = 300.0
DEFAULT_LOCK_TIMEOUT_S = 900.0
DEFAULT_STATE_FILE = Path("data/presence_state.json")


def _truthy(val: str | None) -> bool:
    return (val or "").lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


@dataclass
class PresenceState:
    armed: bool = False
    grace_s: float = DEFAULT_GRACE_S
    lock_timeout_s: float = DEFAULT_LOCK_TIMEOUT_S
    auto_lock: bool = False
    last_seen: float | None = None
    last_status: str = "unknown"
    last_names: list[str] = field(default_factory=list)
    last_tick: float | None = None
    lock_acted_at: float | None = None


class PresenceMonitor:
    """Presence state machine with JSON persistence."""

    def __init__(self, state_file: Path = DEFAULT_STATE_FILE) -> None:
        self.state_file = Path(state_file)
        self.state = PresenceState(
            armed=_truthy(os.getenv(ENV_PRESENCE_ARMED)),
            grace_s=_env_float(ENV_PRESENCE_GRACE_S, DEFAULT_GRACE_S),
            lock_timeout_s=_env_float(ENV_PRESENCE_LOCK_TIMEOUT_S, DEFAULT_LOCK_TIMEOUT_S),
            auto_lock=_truthy(os.getenv(ENV_PRESENCE_AUTO_LOCK)),
        )
        self._load()

    def _load(self) -> None:
        try:
            if self.state_file.is_file():
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                for key in (
                    "armed",
                    "grace_s",
                    "lock_timeout_s",
                    "auto_lock",
                    "last_seen",
                    "last_status",
                    "last_names",
                    "last_tick",
                    "lock_acted_at",
                ):
                    if key in data:
                        setattr(self.state, key, data[key])
        except Exception as e:
            logger.warning("presence state load failed: %s", e)

    def _save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("presence state save failed: %s", e)

    def arm(self) -> dict[str, Any]:
        self.state.armed = True
        if self.state.last_seen is None:
            self.state.last_seen = time.time()
        self._save()
        return self.status()

    def disarm(self) -> dict[str, Any]:
        self.state.armed = False
        self._save()
        return self.status()

    def set_timeouts(
        self, grace_s: float | None = None, lock_timeout_s: float | None = None, auto_lock: bool | None = None
    ) -> dict[str, Any]:
        if grace_s is not None:
            self.state.grace_s = max(0.0, float(grace_s))
        if lock_timeout_s is not None:
            self.state.lock_timeout_s = max(0.0, float(lock_timeout_s))
        if auto_lock is not None:
            self.state.auto_lock = bool(auto_lock)
        if self.state.lock_timeout_s < self.state.grace_s:
            self.state.lock_timeout_s = self.state.grace_s
        self._save()
        return self.status()

    def status(self) -> dict[str, Any]:
        s = self.state
        now = time.time()
        away_for = None
        if s.last_seen is not None:
            away_for = max(0.0, now - s.last_seen)
        return {
            "armed": s.armed,
            "status": s.last_status if s.armed else "disarmed",
            "grace_s": s.grace_s,
            "lock_timeout_s": s.lock_timeout_s,
            "auto_lock": s.auto_lock,
            "last_seen": s.last_seen,
            "away_for_s": round(away_for, 1) if away_for is not None else None,
            "last_names": s.last_names,
            "last_tick": s.last_tick,
            "lock_acted_at": s.lock_acted_at,
        }

    def tick(
        self, matches: list[dict[str, Any]], *, allow_lock: bool = True, now: float | None = None
    ) -> dict[str, Any]:
        """Fold one recognition result into state. Pure logic except the
        optional workstation lock (only when newly away-long + auto_lock)."""
        s = self.state
        now = time.time() if now is None else now
        s.last_tick = now
        names = [m.get("name", "Unknown") for m in (matches or [])]
        known = [n for n in names if n and n != "Unknown"]
        s.last_names = names
        acted = None
        if not s.armed:
            s.last_status = "disarmed"
            self._save()
            return {**self.status(), "acted": acted}

        if known:
            s.last_seen = now
            s.last_status = "present"
            self._save()
            return {**self.status(), "acted": acted}

        base = s.last_seen if s.last_seen is not None else now
        away_for = max(0.0, now - base)
        if away_for >= s.lock_timeout_s:
            new_status = "away-long"
            if s.last_status != "away-long" and s.auto_lock and allow_lock and _lock_workstation():
                s.lock_acted_at = now
                acted = "lock"
        elif away_for >= s.grace_s:
            new_status = "away-short"
        else:
            new_status = "present"
        s.last_status = new_status
        self._save()
        out = self.status()
        out["acted"] = acted
        out["recommendation"] = (
            "lock workstation"
            if new_status == "away-long"
            else ("no action (within grace)" if new_status in ("present", "away-short") else "n/a")
        )
        return out


def _lock_workstation() -> bool:
    """Lock the Windows workstation. Best effort, never raises."""
    try:
        import ctypes

        return bool(ctypes.windll.user32.LockWorkStation())
    except Exception as e:
        logger.warning("LockWorkStation failed: %s", e)
        return False


_monitor: PresenceMonitor | None = None


def get_monitor(state_file: Path = DEFAULT_STATE_FILE) -> PresenceMonitor:
    """Process-wide singleton (tests pass their own file)."""
    global _monitor
    if _monitor is None:
        _monitor = PresenceMonitor(state_file=state_file)
    return _monitor
