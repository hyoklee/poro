#!/usr/bin/env python3
"""Compare HDF5 file layouts over an S3-compatible endpoint, for ROS3 and CLIO.

    run_layouts.py --delay-ms 10 --mbps 28 --reps 3 [--clio] --out results/layouts_<stamp>

Starts s3_mock.py over files/ (one bucket, every <record>_<variant>.h5), then
for each record x variant:
  * ROS3: ros3_bench for meta/full/window/channel, `reps` fresh opens each;
    the mock's request log gives the GET/HEAD count and bytes per open.
  * CLIO (--clio): run_clio.sh stages the object through CAE S3 -> CTE once,
    then reads it back and runs the four patterns (1 warm rep).
Writes ros3.csv, clio.csv and requests.csv to --out.
"""
import argparse
import csv
import json
import os
import re
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
VARIANTS = ["orig", "paged1m", "paged", "paged_fit", "paged_bal", "paged_bal_gz"]
PATTERNS = ["meta", "full", "window", "channel"]
BUCKET = "porobench"


def read_log(path, start):
    with open(path) as f:
        lines = f.readlines()
    return [json.loads(x) for x in lines[start:]], len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay-ms", type=float, default=10)
    ap.add_argument("--mbps", type=float, default=28)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", type=int, default=9123)
    ap.add_argument("--clio", action="store_true")
    ap.add_argument("--records", default="160318160317,160321120917,160324003917")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    log = out / "mock_requests.jsonl"; log.write_text("")
    (out / "params.json").write_text(json.dumps(vars(a), indent=2))
    mock = subprocess.Popen([PY, str(HERE / "s3_mock.py"), "--root", str(HERE / "files"),
                             "--bucket", BUCKET, "--port", str(a.port), "--delay-ms", str(a.delay_ms),
                             "--mbps", str(a.mbps), "--log", str(log)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    env = dict(os.environ, LD_LIBRARY_PATH=str(Path.home() / "miniconda3/envs/iowarp/lib"),
               AWS_EC2_METADATA_DISABLED="true", ROS3_ENDPOINT=f"http://127.0.0.1:{a.port}",
               HDF5_ROS3_VFD_FORCE_PATH_STYLE="1")
    pos = 0
    ros3_rows, req_rows, clio_rows = [], [], []
    try:
        for rec in a.records.split(","):
            for v in VARIANTS:
                key = f"{rec}_{v}.h5"
                size = (HERE / "files" / key).stat().st_size
                for p in PATTERNS:
                    r = subprocess.run([str(HERE / "build/ros3_bench"), f"s3://{BUCKET}/{key}", p, str(a.reps)],
                                       env=env, capture_output=True, text=True, timeout=600)
                    reqs, pos = read_log(log, pos)
                    for line in r.stdout.split():
                        pass
                    for ln in r.stdout.strip().splitlines():
                        pat, rep, o, rd, tot, nb = ln.split()
                        ros3_rows.append(dict(record=rec, variant=v, file_bytes=size, pattern=pat, rep=int(rep),
                                              open_ms=float(o), read_ms=float(rd), total_ms=float(tot)))
                    n_get = sum(1 for q in reqs if q["method"] == "GET")
                    req_rows.append(dict(record=rec, variant=v, pattern=p, opens=a.reps,
                                         gets_per_open=n_get / a.reps,
                                         heads_per_open=sum(q["method"] == "HEAD" for q in reqs) / a.reps,
                                         mb_per_open=round(sum(q["bytes"] for q in reqs) / a.reps / 1e6, 3),
                                         ok=r.returncode == 0))
                    print(f"ros3 {key} {p}: rc={r.returncode} gets/open={n_get / a.reps:g} "
                          f"MB/open={req_rows[-1]['mb_per_open']} total_ms="
                          f"{[x['total_ms'] for x in ros3_rows[-a.reps:]]}", flush=True)
                if a.clio:
                    cenv = dict(os.environ, S3_ENDPOINT=f"http://127.0.0.1:{a.port}")
                    r = subprocess.run([str(HERE / "run_clio.sh"), BUCKET, key, "us-west-2", "1"],
                                       env=cenv, capture_output=True, text=True, timeout=900)
                    _, pos = read_log(log, pos)
                    vals = {}
                    for ln in r.stdout.splitlines():
                        m = re.match(r"^(stage|read|meta|full|window|channel) (.*)$", ln)
                        if m:
                            vals[m.group(1)] = m.group(2).split()
                    if "stage" in vals:
                        row = dict(record=rec, variant=v, file_bytes=size, stage_ms=float(vals["stage"][0]),
                                   read_ms=float(vals["read"][1]) if "read" in vals else None)
                        for p in PATTERNS:
                            if p in vals:
                                row[f"{p}_open_ms"], row[f"{p}_read_ms"] = float(vals[p][1]), float(vals[p][2])
                        clio_rows.append(row)
                    print(f"clio {key}: rc={r.returncode} {vals.get('stage')}", flush=True)
    finally:
        mock.terminate()
    for name, rows in (("ros3.csv", ros3_rows), ("requests.csv", req_rows), ("clio.csv", clio_rows)):
        if rows:
            with open(out / name, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)
    print(out)


if __name__ == "__main__":
    main()
