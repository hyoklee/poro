#!/bin/bash
# Start clio-agent 0.9.7.x with the ported PoroTomo agent (poro/porotomo-is, the
# default since 2026-11-18) on Mistral Large 4 served by the ALCF inference
# gateway. start-alcf-mistral.sh calls this script; CLIO_AGENT_SERIES=0.9.4 there
# runs the old 0.9.4.24 blueprint instead. Both use port 8100, so starting one
# stops the other.
#
# 0.9.7.x has no blueprints: the agent is a plugin marketplace in ./marketplace,
# installed into this server's own home (a snapshot, so the script re-installs it
# on every start). The server runs from an empty folder, because 0.9.7.1 adopts a
# 0.9.4 session store it finds in <cwd>/.clio/agent and resumes its sessions
# (clio-agent #2375).
#
# One-time setup (0.9.7.x in its own venv):
#   uv venv ~/.local/share/clio/clio-agent-097/.venv
#   uv pip install --python ~/.local/share/clio/clio-agent-097/.venv/bin/python clio-agent==0.9.7.1
#
# Usage: agent/clio-agent/start-0971.sh [minerva|tara]
set -eu
CLUSTER=${1:-minerva}
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=${CLIO097_VENV:-$HOME/.local/share/clio/clio-agent-097/.venv}/bin
export CLIO_AGENT_HOME=${CLIO097_HOME:-$HOME/.local/share/clio/clio-agent-097/home}
export CLIO_RUNTIME_STATE_DIR=${CLIO097_RUNTIME:-$HOME/.local/share/clio/clio-agent-097/runtime-state}
WORKDIR=${CLIO097_CWD:-$HOME/.local/share/clio/clio-agent-097/cwd}
PORT=${CLIO097_PORT:-8100}
AGENT=poro/porotomo-is

case "$CLUSTER" in
  minerva) MODEL=mistral-large-4-nvfp4 ;;
  tara)    MODEL=mistral-large-4 ;;
  *) echo "cluster must be minerva or tara"; exit 2 ;;
esac
[ -x "$VENV/clio-agent" ] || { echo "no clio-agent 0.9.7.x in $VENV (see the setup lines in this script)"; exit 1; }
"$VENV/python" -m clio_agent.providers.argonne_auth status >/dev/null 2>&1 || {
  echo "no valid ALCF Globus token; run: $VENV/python -m clio_agent.providers.argonne_auth authenticate"; exit 1; }

mkdir -p "$CLIO_AGENT_HOME" "$CLIO_RUNTIME_STATE_DIR" "$WORKDIR"
[ -e "$WORKDIR/.clio" ] && { echo "$WORKDIR/.clio exists; 0.9.7.1 would adopt it (clio-agent #2375)"; exit 1; }
cd "$WORKDIR"

export CLIO_LM_PROVIDER=argonne_metis
export CLIO_LM_API_BASE=https://inference-api.alcf.anl.gov/resource_server/$CLUSTER/api/v1
export CLIO_LM_MODEL=${CLIO_LM_MODEL:-$MODEL}
# No default output cap upstream (clio-agent #2371). Normal steps use < 2k tokens;
# this bounds a runaway reasoning stream to about 23 s at ~360 tokens/s.
export CLIO_LM_MAX_TOKENS=${CLIO_LM_MAX_TOKENS:-8192}
export CLIO_ALLOWED_ROOTS=${CLIO_ALLOWED_ROOTS:-$HOME/poro:$HOME/cae_test_data:/tmp}

# Install (first time) or refresh (later) the marketplace, then trust it. An
# update whose Python parts changed (agents/, the porotomo_report tool) is held
# until it is trusted again, so trust after every update: it is this repo's code.
"$VENV/clio-agent" plugin check "$HERE/marketplace" >/dev/null
if "$VENV/clio-agent" plugin list 2>/dev/null | grep -q '^poro '; then
  "$VENV/clio-agent" plugin update poro
else
  "$VENV/clio-agent" plugin install "$HERE/marketplace" --name poro
fi
"$VENV/clio-agent" plugin trust poro

# Stop any clio-agent server (0.9.4 or 0.9.7) and clio-core runtime left on this port.
pkill -u "$USER" -f "clio-agent(-gact| serve) --host 127.0.0.1 --port $PORT" 2>/dev/null && sleep 3 || true
pkill -u "$USER" -f "iowarp_core/bin/clio_run start" 2>/dev/null || true

"$VENV/clio-agent" serve --host 127.0.0.1 --port "$PORT" &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' INT TERM
# New sessions run the PoroTomo agent unless they name another one. /v1/health
# answers before the task runtime is up, so retry until the server accepts it
# (503 task_runtime_starting until then).
ok=
for _ in $(seq 1 90); do
  if curl -sf -m 5 -X PATCH "http://127.0.0.1:$PORT/v1/session-defaults" \
       -H 'content-type: application/json' -d "{\"agent_ref\": \"$AGENT\"}" >/dev/null; then
    ok=1; break
  fi
  kill -0 $SERVER 2>/dev/null || { echo "server exited"; exit 1; }
  sleep 2
done
[ -n "$ok" ] && echo "clio-agent 0.9.7.x on port $PORT, default agent $AGENT" \
  || echo "warning: could not set the default agent; pass metadata.agent_ref=$AGENT per session"
wait $SERVER
