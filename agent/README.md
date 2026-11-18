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
| `report.py` | prints the headline numbers of a run in about 1 KB (for LLM agents; also the `porotomo_report` tool of the 0.9.7.x agent) |
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

**Default (since 2026-11-18): clio-agent 0.9.7.1 with the plugin agent
`poro/porotomo-is`.** 0.9.7.x has no blueprints. `clio-agent/marketplace/` ports
the tuned blueprint to a plugin agent (see its README). clio-agent 0.9.7.1 is
installed from tag v0.9.7.1 (commit f8ef50d) in its own venv, with its own home,
next to the old 0.9.4.24 install:

```bash
uv venv --python ~/.local/share/clio/clio-agent/.venv/bin/python ~/.local/share/clio/clio-agent-097/.venv
uv pip install --python ~/.local/share/clio/clio-agent-097/.venv/bin/python \
    "clio-agent @ git+https://github.com/iowarp/clio-agent@v0.9.7.1"
```

Model: **Mistral Large 4 on the ALCF inference gateway.** ALCF lists it on Minerva
(`mistral-large-4-nvfp4`, always hot) and Tara (`mistral-large-4`); the change
went in with argonne-lcf/user-guides PR #1401, merged 2026-11-02. clio-agent has
no Minerva or Tara preset, so the start scripts reuse the `argonne_metis`
preset, which has the same Globus auth, and override `CLIO_LM_API_BASE` and
`CLIO_LM_MODEL`.

One-time login, run interactively in your own terminal. Both venvs read the same token.

```bash
~/.local/share/clio/clio-agent-097/.venv/bin/python -m clio_agent.providers.argonne_auth authenticate
agent/clio-agent/start-alcf-mistral.sh minerva &        # server on :8100, poro/porotomo-is
~/.local/share/clio/clio-agent-097/.venv/bin/python agent/clio-agent/run_query.py \
    "List the datasets in ~/cae_test_data/porotomo/dasv_native_PoroTomo_iDAS025_160318160317.h5 with shape and dtype." \
    --out agent/results/llm/answer.json
```

`start-alcf-mistral.sh` runs `clio-agent/start-0971.sh`, which:
- installs or updates and trusts the marketplace in `~/.local/share/clio/clio-agent-097/home`;
- stops any server on :8100;
- starts the server from the empty folder `~/.local/share/clio/clio-agent-097/cwd`. Started from `~/poro`, 0.9.7.1 adopts `~/poro/.clio/agent` and resumes old sessions ([clio-agent #2375](https://github.com/iowarp/clio-agent/issues/2375));
- makes `poro/porotomo-is` the session default.

The output cap (`CLIO_LM_MAX_TOKENS=8192`, [#2371](https://github.com/iowarp/clio-agent/issues/2371)) and the data roots are set as before.
Use `run_query.py`, not `clio-agent --query`. It pins a new session to `--agent`
(default `poro/porotomo-is`) and approves only the `hdf5_*` and `porotomo_*` tools;
shell stays denied unless you pass `--allow-shell` (needed only for PBS jobs). Run
results come from the plugin's read-only `porotomo_report` tool, which returns the
`report.py` digest of a run. The agent answered 60/60 benchmark questions with no DSPy
patch; with `porotomo_report` the medians are 4.0 s for run results and 4.8 s for
the HDF5 listing (round 12 in `wiki/agent_clio_performance.md`).
`clio-agent/bench_0971.py --agent poro/porotomo-is --tasks results,hdf5 --out <dir>` runs the benchmark.

**The old 0.9.4.24 setup** (`~/.local/share/clio/clio-agent/.venv`, with the
`porotomo-is-tuned` blueprint) still works. Start it with
`CLIO_AGENT_SERIES=0.9.4 agent/clio-agent/start-alcf-mistral.sh minerva`, and run
`run_query.py` and `bench.py` with that venv's python. Link the blueprints into it:

```bash
ln -s ~/poro/agent/clio-agent/variants/porotomo-is-tuned ~/.config/clio-agent/agent-blueprints/
ln -s ~/poro/agent/clio-agent/porotomo-induced-seismicity ~/.config/clio-agent/agent-blueprints/
```

On 0.9.4.24, a turn occasionally stalls right after a tool call: the model's
next reasoning step streams without end, and the turn fails only at the ~900 s
turn wall ([#2371](https://github.com/iowarp/clio-agent/issues/2371),
[#2372](https://github.com/iowarp/clio-agent/issues/2372); not seen with the cap).
Truncated answers (clio-agent #2369, closed as not applying to 0.9.7.x) come from
DSPy's `json_repair` call mangling the model's slightly malformed tool-call JSON.
A local patch fixes them; apply it after every 0.9.4 install or upgrade, then
restart the server:

```bash
~/.local/share/clio/clio-agent/.venv/bin/python agent/clio-agent/patches/apply_dspy_patch.py   # --revert to undo
```

The clio-kit HDF5 server keeps an index under `<server cwd>/data/` (ignored by git).

## Tuned default and benchmarks

`clio-agent/variants/porotomo-is-tuned/` (the 0.9.4.24 default from 2026-11-17; ported as `poro/porotomo-is`) is a
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

