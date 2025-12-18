from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")

def run(cmd):
    print(f"[CMD] {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    run([PYTHON, "scripts/run_incident_extract_baseline.py", "--run-id", args.run_id])
    run([PYTHON, "scripts/run_geo_resolve_incidents.py", "--run-id", args.run_id])
    run([PYTHON, "scripts/build_fct_incidents.py", "--run-id", args.run_id])
    run([PYTHON, "scripts/check_incidents_run.py", "--run-id", args.run_id])

    print("EXIT_CODE=0")

if __name__ == "__main__":
    main()
