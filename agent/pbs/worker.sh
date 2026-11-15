#!/bin/bash
# One rank of the distributed detection job. Rank r of N takes manifest lines
# r, r+N, r+2N, ... : download the record to node-local scratch, run
# detect.py, append the JSON line to its own output file, delete the record.
# Rank/size come from PALS (Aurora mpiexec) or PMI; fall back to 0/1.
set -u
MANIFEST=$1
OUTDIR=$2
RANK=${PALS_RANKID:-${PMI_RANK:-0}}
SIZE=${PALS_SIZE:-${PMI_SIZE:-1}}
[ "$SIZE" = 1 ] && [ -n "${NRANKS:-}" ] && SIZE=$NRANKS
AGENT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PY=${CLIO_AGENT_PY:-$HOME/.local/share/clio/clio-agent/.venv/bin/python}
B=https://nrel-pds-porotomo.s3.amazonaws.com
SCR=${TMPDIR:-/tmp}/poro_$$_$RANK
mkdir -p "$SCR" "$OUTDIR"
OUT=$OUTDIR/detect_rank$(printf %04d "$RANK").jsonl
n=0
awk -v r="$RANK" -v s="$SIZE" 'NF && (NR-1)%s==r' "$MANIFEST" | while read -r KEY; do
  F=$SCR/$(basename "$KEY")
  if curl -sSf --retry 5 --retry-all-errors -o "$F" "$B/$KEY"; then
    OMP_NUM_THREADS=1 "$PY" "$AGENT_DIR/detect.py" "$F" --key "$KEY" --out "$OUT"
  else
    echo "{\"key\": \"$KEY\", \"status\": \"download_failed\"}" >> "$OUT"
  fi
  rm -f "$F"
  n=$((n+1))
done
rmdir "$SCR" 2>/dev/null
echo "rank $RANK/$SIZE on $(hostname) done"
