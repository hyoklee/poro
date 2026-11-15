#!/bin/bash
# Build the manifest on the login node and submit poro_detect: N nodes,
# mpiexec, one rank per manifest shard, then hazard.py on the merged output.
# Usage: agent/pbs/submit.sh [stride] [nodes] [ppn]
set -eu
STRIDE=${1:-20}
NODES=${2:-2}
PPN=${3:-24}
AGENT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PY=${CLIO_AGENT_PY:-$HOME/.local/share/clio/clio-agent/.venv/bin/python}
RUN_DIR=$AGENT_DIR/results/run_$(date -u +%Y%m%dT%H%M%SZ)_s$STRIDE
mkdir -p "$RUN_DIR/detect"
"$PY" "$AGENT_DIR/manifest.py" --stride "$STRIDE" -o "$RUN_DIR/manifest.txt" | tee "$RUN_DIR/manifest.log"
V="AGENT_DIR=$AGENT_DIR,RUN_DIR=$RUN_DIR,MANIFEST=$RUN_DIR/manifest.txt,PPN=$PPN"
J1=$(qsub -l select="$NODES" -v "$V,STRIDE=$STRIDE" -o "$RUN_DIR/detect.log" "$AGENT_DIR/pbs/detect.pbs")
printf 'detect+hazard %s\n' "$J1" | tee "$RUN_DIR/jobs.txt"
echo "run dir: $RUN_DIR"
