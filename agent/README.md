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
| `clio-agent/variants/porotomo-is-tuned/` | **default** clio-agent blueprint: one expert with `shell_bash` and the read-only HDF5 tools that drives the scripts above |
| `clio-agent/porotomo-induced-seismicity/` | orchestrated clio-agent blueprint: `main` plus `hdf5` and `seismicity` experts (slower; kept for comparison) |
| `sources/` | the external inputs: GDR 917 pumping CSV, GDR 859 LBNL/NCEDC catalogue PDF and text |
| `results/run_*/` | one directory per run: manifest, per-rank JSONL, `summary.json`, CSVs, figures, logs, interpretation |
| `report.py` | prints the headline numbers of a run in about 1 KB (for LLM agents) |
| `results/llm/` | clio-coder code review, clio-agent test transcripts, benchmark rounds `bench_*` |

## Running

```bash
agent/pbs/submit.sh 20 2 24      # stride 20 (one record per 10 min), 2 nodes, 24 ranks/node
qstat -u $USER
agent/interpret.sh agent/results/run_<stamp>_s20
```

Python is the clio-agent venv (`~/.local/share/clio/clio-agent/.venv/bin/python`,
which has h5py 3.16 and numpy 2.5). Override it with `CLIO_AGENT_PY`.

## clio-agent

The default blueprint is `porotomo-is-tuned` (used by `start-alcf-mistral.sh`,
`run_query.py` and the server's default agent). Link it, and optionally the
orchestrated one, into clio-agent:

```bash
ln -s ~/poro/agent/clio-agent/variants/porotomo-is-tuned ~/.config/clio-agent/agent-blueprints/
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
agent/clio-agent/start-alcf-mistral.sh minerva &        # server on :8100 (Minerva, tuned blueprint, data roots)
~/.local/share/clio/clio-agent/.venv/bin/python agent/clio-agent/run_query.py \
    "List the datasets in ~/cae_test_data/porotomo/dasv_native_PoroTomo_iDAS025_160318160317.h5 with shape and dtype." \
    --out agent/results/llm/answer.json
```

Use `run_query.py`, not `clio-agent --query`. `--query` always runs the built-in
`main` agent and denies every tool. `run_query.py` activates the blueprint on a
fresh session (`POST /v1/sessions/{sid}/agent-blueprint`) and approves only
read-only `hdf5_*` tools. Shell stays denied unless you pass `--allow-shell`.
The clio-kit HDF5 server keeps an index under `<server cwd>/data/`, which is
ignored by git. A turn occasionally stalls right after a tool call (e.g.
`hdf5_open_file`): the model's next reasoning step streams without end and the
turn fails only at the ~900 s turn wall ([clio-agent #2371](https://github.com/iowarp/clio-agent/issues/2371), [#2372](https://github.com/iowarp/clio-agent/issues/2372)).
Retry the question; the tuned blueprint finishes in about 8 s when it works.

Truncated answers (clio-agent #2369) come from DSPy's `json_repair` call
mangling the model's slightly malformed tool-call JSON. A local patch fixes it;
apply it after every clio-agent install or upgrade, then restart the server:

```bash
~/.local/share/clio/clio-agent/.venv/bin/python agent/clio-agent/patches/apply_dspy_patch.py   # --revert to undo
```

## Tuned default and benchmarks

`clio-agent/variants/porotomo-is-tuned/` (the default since 2026-11-17) is a
single-expert version of the orchestrated blueprint: one expert holds `shell_bash` (it runs `report.py` for run results)
and the read-only HDF5 tools including `hdf5_analyze_dataset_structure`, with
the light prompt profile. On the benchmark questions it answered in 8.2–8.8 s
with 17–34k input tokens, against 51–66 s and 96–114k for the orchestrated
blueprint, with the same accuracy (see
[wiki/agent_clio_performance.md](../wiki/agent_clio_performance.md)). Questions about run results need
`--allow-shell`, because the expert reads them with `report.py`. Pass
`--blueprint porotomo-induced-seismicity` to `run_query.py` for the
orchestrated blueprint.

```bash
python3 agent/report.py agent/results/run_<stamp>_s20          # 1 KB digest of summary.json
~/.local/share/clio/clio-agent/.venv/bin/python agent/clio-agent/bench.py --reps 3 \
    --out agent/results/llm/bench_<stamp> \
    --configs results:porotomo-induced-seismicity,results:porotomo-is-tuned
```

