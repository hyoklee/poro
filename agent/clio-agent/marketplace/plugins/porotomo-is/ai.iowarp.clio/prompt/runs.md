---
id: porotomo-is.runs
section: domain
---
Results of a run: call `porotomo_report` (`run` = the run name, or empty for
the latest). It returns every headline number (records, anomalies, detections,
pumping, Sigma and probabilities per b, the DAS upper bound) from the run's
`summary.json`; it is authoritative, so answer from it directly. Open
`summary.json` or the CSVs only for a value it lacks.
New runs: `~/poro/agent/pbs/submit.sh <stride> <nodes> <ppn>` with `shell_bash`
(one job at a time in the `debug` queue); check with `qstat -u $USER`. Run
`shell_bash` with `cwd` set to `/home/hyoklee/poro`.
