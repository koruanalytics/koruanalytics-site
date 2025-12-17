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


def read_expected(sha_path: Path) -> str:
    # formato: "<hash>  <filename>"
    line = sha_path.read_text(encoding="utf-8").strip().splitlines()[0]
    return line.split()[0].strip()


def validate_one(path: Path) -> None:
    sha_path = path.with_suffix(path.suffix + ".sha256")
    if not sha_path.exists():
        raise SystemExit(f"[GEO] ERROR: missing checksum file: {sha_path.as_posix()}")

    expected = read_expected(sha_path)
    actual = sha256_file(path)

    if actual != expected:
        raise SystemExit(
            f"[GEO] ERROR: checksum mismatch for {path.name}\n"
            f"expected={expected}\n"
            f"actual  ={actual}\n"
            "Si has actualizado el gazetteer a propósito, vuelve a ejecutar:\n"
            "  python scripts/write_gazetteer_checksums.py"
        )

    logger.success(f"[GEO] OK checksum: {path.name}")


def main() -> None:
    cfg = load_config()
    csv_path = Path(cfg["geo"]["gazetteer_path"])
    if not csv_path.exists():
        raise SystemExit(f"[GEO] ERROR: missing gazetteer CSV: {csv_path.as_posix()}")

    validate_one(csv_path)

    parquet_path = csv_path.with_suffix(".parquet")
    if parquet_path.exists():
        validate_one(parquet_path)
    else:
        logger.info("[GEO] Parquet not present; skipped.")


if __name__ == "__main__":
    main()
