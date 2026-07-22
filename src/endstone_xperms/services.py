from __future__ import annotations

import re
from time import time

_DURATION = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def parse_duration(value: str | int | float) -> float:
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    if not isinstance(value, str):
        raise ValueError("duration must be seconds or [Nd][Nh][Nm][Ns]")
    match = _DURATION.fullmatch(value.strip().lower())
    if not match or not any(match.groups()):
        raise ValueError("duration must be seconds or [Nd][Nh][Nm][Ns]")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return float(days * 86400 + hours * 3600 + minutes * 60 + seconds)


def expiration(duration: str | int | float, now: float | None = None) -> float:
    return (time() if now is None else now) + parse_duration(duration)
