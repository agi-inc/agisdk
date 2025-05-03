#!/usr/bin/env bash

# llm_eval.sh: Wrapper for your REAL.harness evaluation script
# Usage: ./llm_eval.sh [-m model_name] [-H] [-A] [-S] [-t task] [-r results_dir] [-n num_workers] [-h]
uv pip install -e .

# Default values
MODEL=gpt-4o-mini
USE_HTML=false
USE_AXTREE=true
USE_SCREEN=true
TASK=
RESULTS_DIR=results
NUM_WORKERS=4

# Function to display usage
usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  -m MODEL_NAME     Model name (default: $MODEL)
  -H                Enable HTML observation (default: disabled)
  -A                Disable AxTree observation (default: enabled)
  -S                Disable Screenshot observation (default: enabled)
  -t TASK           Task identifier (e.g., webclones.omnizon-1)
  -r RESULTS_DIR    Directory for outputs (default: $RESULTS_DIR)
  -n NUM_WORKERS    Number of parallel workers (default: $NUM_WORKERS)
  -h                Show this help message
EOF
  exit 1
}

# Parse command-line options
while getopts ":m:HAS t:r:n:h" opt; do
  case $opt in
    m) MODEL="$OPTARG" ;;
    H) USE_HTML=true ;;
    A) USE_AXTREE=false ;;
    S) USE_SCREEN=false ;;
    t) TASK="$OPTARG" ;;
    r) RESULTS_DIR="$OPTARG" ;;
    n) NUM_WORKERS="$OPTARG" ;;
    h) usage ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
    :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
  esac
done

shift $((OPTIND -1))

# Build up flags for Python
PY_FLAGS="--model $MODEL"
$USE_HTML  && PY_FLAGS+=" --use_html"
! $USE_AXTREE && PY_FLAGS+=" --no_axtree"
! $USE_SCREEN && PY_FLAGS+=" --no_screenshot"
[[ -n "$TASK" ]]     && PY_FLAGS+=" --task $TASK"
PY_FLAGS+=" --results_dir $RESULTS_DIR"
PY_FLAGS+=" --num_workers $NUM_WORKERS"

# Execute the evaluation
python test.py $PY_FLAGS "$@"
