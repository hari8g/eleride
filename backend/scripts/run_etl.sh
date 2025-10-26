#!/usr/bin/env bash
# run_etl.sh <input_xlsx_or_csv> [k_clusters]
INPUT=$1
K=${2:-12}
if [ -z "$INPUT" ]; then
  echo "Usage: run_etl.sh <input.xlsx|csv> [k_clusters]"
  exit 1
fi
python - <<PY
from app.services.etl import run_full_etl
print(run_full_etl("$INPUT", cleaned_csv_out="/data/jobs_clean.csv", k_clusters=int($K), train_model=True))
PY
