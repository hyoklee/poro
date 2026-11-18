---
id: porotomo-is.runs
section: domain
---
Results of a run: run `python3 ~/poro/agent/report.py <run>` with `shell_bash`, where
`<run>` is the full path `~/poro/agent/results/run_<stamp>`.
It prints every headline number (records, anomalies, detections, Sigma and
probabilities per b, the DAS upper bound) in about 1 KB, read from `<run>/summary.json`,
so it needs no cross-check; open that file or the CSVs only for a value it lacks.
New runs: `~/poro/agent/pbs/submit.sh <stride> <nodes> <ppn>` (one job at a time
in the `debug` queue); check with `qstat -u $USER`. Run every `shell_bash` command
with `cwd` set to `/home/hyoklee/poro`; other directories are outside the allowed roots.
