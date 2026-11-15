# agent/: induced-seismicity anomaly agent for PoroTomo DAS

This agent looks for anomalies in the PoroTomo vertical-DAS (DASV) records from
Brady Hot Springs (March 2016) that could signal injection-induced seismicity.
It then estimates the probability of an earthquake like the 2017 Pohang event
(Mw 5.5) with the seismogenic-index model of Shapiro, Kim & Ree (2021). Results
are written up in [wiki/agent_induced_seismicity.md](../wiki/agent_induced_seismicity.md).

## Layout

| Path | Role |
|---|---|
| `manifest.py` | lists `DAS/H5/DASV/<day>/` on the public bucket and keeps every Nth 30 s record |
| `detect.py` | per-record detector (numpy and h5py): common-mode removal, 10-150 Hz FFT band-pass, median-over-channels STA/LTA (0.05 s / 2 s, threshold 3), event list and record features |
| `hazard.py` | merges the shards; robust-z anomaly flags; event catalogue; pumping volumes from GDR 917; seismogenic index from the LBNL catalogue (GDR 859); exceedance probabilities; figures |
| `pbs/submit.sh` | builds the manifest and submits `pbs/detect.pbs` (Aurora, `IOWarp` project, `debug` queue) |
| `pbs/detect.pbs`, `pbs/worker.sh` | `mpiexec` launches N nodes x PPN ranks; rank r downloads lines r, r+N, ... to node-local scratch through the ALCF proxy, runs `detect.py`, deletes the file; `hazard.py` runs at the end |
| `pbs/hazard.pbs` | standalone aggregation job for queues that allow dependent jobs |
| `interpret.sh` | clio-coder (headless `run`, ALCF Metis `gpt-oss-120b`) writes `interpretation.md` from `summary.json` |
| `clio-agent/porotomo-induced-seismicity/` | clio-agent blueprint: orchestrator plus `hdf5` and `seismicity` experts that drive the scripts above |
| `sources/` | the external inputs: GDR 917 pumping CSV, GDR 859 LBNL/NCEDC catalogue PDF and text |
| `results/run_*/` | one directory per run: manifest, per-rank JSONL, `summary.json`, CSVs, figures, logs, interpretation |
| `results/llm/` | clio-coder code review of `detect.py` and `hazard.py` |

## Running

```bash
agent/pbs/submit.sh 20 2 24      # stride 20 (one record per 10 min), 2 nodes, 24 ranks/node
qstat -u $USER
agent/interpret.sh agent/results/run_<stamp>_s20
```

Python is the clio-agent venv (`~/.local/share/clio/clio-agent/.venv/bin/python`,
which has h5py 3.16 and numpy 2.5). Override it with `CLIO_AGENT_PY`.

## clio-agent

To use the blueprint, link it into clio-agent:

```bash
ln -s ~/poro/agent/clio-agent/porotomo-induced-seismicity ~/.config/clio-agent/agent-blueprints/
```

Model: **Mistral Large 4 on the ALCF inference gateway.** ALCF lists it on Minerva
(`mistral-large-4-nvfp4`, always hot) and Tara (`mistral-large-4`); the change
went in with argonne-lcf/user-guides PR #1401, merged 2026-11-02. clio-agent has
no Minerva or Tara preset, so `clio-agent/start-alcf-mistral.sh` reuses the
`argonne_metis` preset, which has the same Globus auth, and overrides
`CLIO_LM_API_BASE` and `CLIO_LM_MODEL`.

One-time login, run interactively in your own terminal. `globus-sdk` 4.9.1 is
already in the clio-agent venv.

```bash
~/.local/share/clio/clio-agent/.venv/bin/python -m clio_agent.providers.argonne_auth authenticate
agent/clio-agent/start-alcf-mistral.sh minerva "List the datasets in ~/cae_test_data/porotomo/dasv_native_PoroTomo_iDAS025_160318160317.h5"
```
