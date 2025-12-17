from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class DQResult:
    ok: bool
    checks: List[Dict[str, Any]]


def check_min_rows(count: int, min_rows: int = 1) -> Dict[str, Any]:
    ok = count >= min_rows
    return {"check": "min_rows", "min_rows": min_rows, "value": count, "ok": ok}


def check_max_rows(count: int, max_rows: int = 1000) -> Dict[str, Any]:
    ok = count <= max_rows
    return {"check": "max_rows", "max_rows": max_rows, "value": count, "ok": ok}


def summarize_results(checks: List[Dict[str, Any]]) -> DQResult:
    ok = all(c.get("ok", False) for c in checks)
    return DQResult(ok=ok, checks=checks)
