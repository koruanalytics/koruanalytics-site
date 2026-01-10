from __future__ import annotations

import hashlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from src.utils.config import load_config


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksum(path: Path) -> Path:
    digest = sha256_file(path)
    out = path.with_suffix(path.suffix + ".sha256")
    out.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return out


def main() -> None:
    cfg = load_config()
    csv_path = Path(cfg["geo"]["gazetteer_path"])
    if not csv_path.exists():
        raise SystemExit(f"[GEO] ERROR: missing gazetteer CSV: {csv_path.as_posix()}")

    csv_sha = write_checksum(csv_path)
    logger.success(f"[GEO] Wrote checksum: {csv_sha.as_posix()}")

    parquet_path = csv_path.with_suffix(".parquet")
    if parquet_path.exists():
        pq_sha = write_checksum(parquet_path)
        logger.success(f"[GEO] Wrote checksum: {pq_sha.as_posix()}")
    else:
        logger.info("[GEO] Parquet not found (optional). Only CSV checksum written.")


if __name__ == "__main__":
    main()
