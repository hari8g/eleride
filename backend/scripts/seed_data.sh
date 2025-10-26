#!/usr/bin/env bash
set -euo pipefail

# Seed DB by running full ETL on provided input (default to /data/sample_jobs.csv)
INPUT="${1:-${ETL_INPUT_PATH:-/data/sample_jobs.csv}}"
K=${2:-12}
python - <<PY
from app.services.etl import run_full_etl
print(run_full_etl("${INPUT}", cleaned_csv_out="data/jobs_clean.csv", k_clusters=int(${K}), train_model=True))
PY


