#!/bin/bash
# Start a single-node CLIO runtime (CTE + CAE built with CAE_ENABLE_S3), run
# clio_s3_bench against one public S3 object, and stop the runtime.
# Usage: run_clio.sh <bucket> <key> <region> [warm_reps]
HERE=$(cd "$(dirname "$0")" && pwd)
PREFIX=${CLIO_PREFIX:-$HOME/clio-core.dev.wrk/install_s3}
export LD_LIBRARY_PATH=$PREFIX/lib:$HOME/miniconda3/envs/iowarp/lib:$LD_LIBRARY_PATH
export CLIO_SERVER_CONF=$HERE/clio_s3bench_config.yaml CLIO_BIND_ADDR=127.0.0.1 CLIO_PORT=10700
export AWS_NO_SIGN_REQUEST=1 AWS_EC2_METADATA_DISABLED=true   # public bucket, read by the runtime
LOG=${TMPDIR:-/tmp}/clio_s3bench_runtime.out
"$PREFIX/bin/clio_run" stop --force >/dev/null 2>&1
nohup "$PREFIX/bin/clio_run" start > "$LOG" 2>&1 &
RPID=$!
for i in $(seq 1 60); do
  sleep 1
  "$PREFIX/bin/clio_run" status >/dev/null 2>&1 && break
  kill -0 $RPID 2>/dev/null || { echo "runtime died"; tail -20 "$LOG"; exit 1; }
done
sleep 2
"$HERE/build/clio_s3_bench" "$@"
RC=$?
"$PREFIX/bin/clio_run" stop >/dev/null 2>&1
wait $RPID 2>/dev/null
exit $RC
