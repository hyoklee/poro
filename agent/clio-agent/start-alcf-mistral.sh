#!/bin/bash
# Start clio-agent on Mistral Large 4 served by the ALCF inference gateway.
# ALCF lists it (docs.alcf.anl.gov/services/inference-endpoints/models/, user-guides PR #1401,
# merged 2026-11-02) as:
#   Minerva (B200):  mistral-large-4-nvfp4   always hot, 1,048,576 ctx   <- default
#   Tara    (GH200): mistral-large-4         loaded on demand
# clio-agent has no Minerva/Tara preset, so this reuses the argonne_metis preset
# (same Globus auth) with the API base overridden.
#
# One-time login (interactive; run it yourself in a terminal):
#   ~/.local/share/clio/clio-agent/.venv/bin/python -m clio_agent.providers.argonne_auth authenticate
#
# Usage: agent/clio-agent/start-alcf-mistral.sh [minerva|tara] ["one-shot question"]
set -eu
CLUSTER=${1:-minerva}; shift || true
VENV=$HOME/.local/share/clio/clio-agent/.venv/bin
case "$CLUSTER" in
  minerva) MODEL=mistral-large-4-nvfp4 ;;
  tara)    MODEL=mistral-large-4 ;;
  *) echo "cluster must be minerva or tara"; exit 2 ;;
esac
"$VENV/python" -m clio_agent.providers.argonne_auth status >/dev/null 2>&1 || {
  echo "no valid ALCF Globus token; run the login command in the header first"; exit 1; }

export CLIO_LM_PROVIDER=argonne_metis
export CLIO_LM_API_BASE=https://inference-api.alcf.anl.gov/resource_server/$CLUSTER/api/v1
export CLIO_LM_MODEL=${CLIO_LM_MODEL:-$MODEL}
# Our blueprint (hdf5 + seismicity experts) instead of the generic default agent.
export CLIO_DEFAULT_AGENT_BLUEPRINT_ID=${CLIO_DEFAULT_AGENT_BLUEPRINT_ID:-porotomo-induced-seismicity}
# File tools may read the repo, the HDF5 cache and /tmp (default is cwd + temp only).
export CLIO_ALLOWED_ROOTS=${CLIO_ALLOWED_ROOTS:-$HOME/poro:$HOME/cae_test_data:/tmp}

# A running server keeps its old model; restart it so it inherits this env.
pkill -u "$USER" -f "clio-agent-gact --host 127.0.0.1 --port 8100" 2>/dev/null && sleep 3 || true
pkill -u "$USER" -f "iowarp_core/bin/clio_run start" 2>/dev/null || true

if [ $# -gt 0 ]; then
  "$VENV/clio-agent" --json --query "$1" >/dev/null 2>&1 || true   # spawns the server
  for i in $(seq 1 18); do
    sleep 10
    out=$("$VENV/clio-agent" --json --query "$1" 2>&1) || true
    case "$out" in *"still starting"*) continue ;; esac
    echo "$out"; exit 0
  done
  echo "agent did not become ready; see ~/.local/share/clio-agent/gact-server-8100.log"; exit 1
else
  exec "$VENV/clio-agent" serve --host 127.0.0.1 --port 8100
fi
