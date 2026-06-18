#!/usr/bin/env bash
set -euo pipefail

# Run multiple KubeEdge pod failure test runs.
#
# Usage:
#   ./experiments/kubeedge/scripts/run_pod_failure_scenario_async.sh
#
# Optional environment variables:
#   RUNS=10
#   START_RUN=1
#   PRE_SECONDS=60
#   POST_SECONDS=120
#   SLEEP_BETWEEN_RUNS=30
#   URL=http://10.10.20.131:30080

RUNS="${RUNS:-10}"
START_RUN="${START_RUN:-1}"
SLEEP_BETWEEN_RUNS="${SLEEP_BETWEEN_RUNS:-30}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SINGLE_RUN_SCRIPT="${SCRIPT_DIR}/run_pod_failure_test_async.sh"

BASE_DIR="${REPO_ROOT}/experiments/kubeedge/pod-failure"

mkdir -p "${BASE_DIR}"

echo "KubeEdge pod failure scenario"
echo "Base directory: ${BASE_DIR}"
echo "Runs: ${RUNS}"
echo "Start run: ${START_RUN}"
echo "Sleep between runs: ${SLEEP_BETWEEN_RUNS}s"
echo

for i in $(seq "${START_RUN}" $((START_RUN + RUNS - 1))); do
  RUN_NAME="$(printf "run-%02d" "${i}")"
  RUN_DIR="${BASE_DIR}/${RUN_NAME}"

  if [[ -e "${RUN_DIR}" ]]; then
    echo "ERROR: ${RUN_DIR} already exists."
    echo "Refusing to overwrite existing run data."
    exit 1
  fi

  echo "========================================"
  echo "Starting ${RUN_NAME}"
  echo "========================================"

  "${SINGLE_RUN_SCRIPT}" "${RUN_DIR}"

  echo "Finished ${RUN_NAME}"
  echo

  if [[ "${i}" -lt $((START_RUN + RUNS - 1)) ]]; then
    echo "Waiting ${SLEEP_BETWEEN_RUNS}s before next run..."
    sleep "${SLEEP_BETWEEN_RUNS}"
  fi
done

echo "All pod failure runs finished."
