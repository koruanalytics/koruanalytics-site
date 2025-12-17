# scripts/run_block_h_job.py
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def py() -> str:
    # Respeta tu patrón de ejecución: .\.venv\Scripts\python.exe
    # Aquí usamos python "actual" por simplicidad; en PowerShell llamarás al exe correcto.
    return "python"


def run(cmd: list[str]) -> None:
    logger.info(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stdout:
        logger.info(r.stdout.strip())
    if r.stderr:
        logger.warning(r.stderr.strip())
    if r.returncode != 0:
        raise RuntimeError(f"Command failed ({r.returncode}): {' '.join(cmd)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    try:
        run([py(), "scripts/create_curation_schema.py"])
        run([py(), "scripts/run_location_candidates.py", "--run-id", args.run_id])
        run([py(), "scripts/run_geo_resolve_incidents.py", "--run-id", args.run_id])

        # tu pipeline actual
        run([py(), "scripts/build_fct_incidents.py", "--run-id", args.run_id])

        # nuevos artefactos
        run([py(), "scripts/build_fct_incident_places.py", "--run-id", args.run_id])
        run([py(), "scripts/build_fct_incidents_curated.py", "--run-id", args.run_id])

        # checks
        run([py(), "scripts/check_incidents_run.py", "--run-id", args.run_id])
        run([py(), "scripts/check_curation_run.py", "--run-id", args.run_id])

        logger.success("Block H job OK. EXIT_CODE=0")
        return 0
    except Exception as e:
        logger.error(str(e))
        logger.error("Block H job FAILED. EXIT_CODE=2")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
    
