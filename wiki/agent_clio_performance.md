# Agent run: clio-agent performance tuning on ALCF Minerva Mistral Large 4

Benchmarks of 2026-11-16 (four rounds, 01:30–03:50 UTC). Code: [`agent/clio-agent/bench.py`](../agent/clio-agent/bench.py), [`endpoint_bench.py`](../agent/clio-agent/endpoint_bench.py), variant blueprints in [`agent/clio-agent/variants/`](../agent/clio-agent/variants/). Raw results: `agent/results/llm/bench_20261116{,_r2,_r3,_r4}/` (`runs.jsonl`, one transcript per run, `summary.md`) and `bench_20261116/endpoints.jsonl`.

## Question

Which changes make the `porotomo-induced-seismicity` blueprint ([agent_induced_seismicity.md](agent_induced_seismicity.md)) faster and cheaper without losing accuracy?

## Method

- Server: clio-agent on the Aurora login node (`aurora-uan-0012`), model `mistral-large-4-nvfp4` on ALCF Minerva through the inference gateway; driver `run_query.ask()`.
- Two fixed questions:
  - `results`: report records, anomalous records, detections, Σ and P(Mw ≥ 5.5)/yr per b, and the DAS upper bound from `run_20261115T155359Z_s20` (read-only). Shell approved.
  - `hdf5`: list every dataset in the cached DASV record with shape and dtype. `hdf5_*` approved.
- Accuracy is scored automatically: the fraction of 13 expected values from `summary.json` (with the calibrated and upper-bound labels) found in the answer within 2 %, or for `hdf5` the fraction of the 8 datasets whose name, dtype and shape appear on one line, checked against h5py. Both scorers gave 1.0 on the earlier hand-verified answers.
- Tokens are clio-agent's per-session counts summed over the main and child sessions. The ALCF gateway reports no usage to clio-agent, so these are clio-agent's estimates (the server log says `usage_estimated`); compare them between runs only.
- Variants run interleaved within each round so gateway load affects all alike. Round 1 had heavy gateway load (the same baseline took 65–222 s); rounds 2–4 were quieter.

## What was tested

| Variant | Change |
|---|---|
| `porotomo-induced-seismicity` | baseline: `main` orchestrator delegates to `hdf5` or `seismicity`; `seismicity` reads `summary.json` with shell; heavy prompt profile |
| `porotomo-is-digest` | same tree, but `seismicity` runs the new `agent/report.py` (936 B digest instead of the 7,118 B `summary.json`) |
| `porotomo-is-single-heavy` / `-light` | one expert holding `shell_bash` and the `hdf5_*` tools, no delegation, `report.py`; heavy or light profile. From round 2 the prompt also says to run shell in `/home/hyoklee/poro` and never to call `spawn_agent_task` |
| `porotomo-is-tuned` | single-light plus `hdf5_analyze_dataset_structure` (all datasets with shape and dtype in one call) |
| reasoning effort `low` | `behavior.reasoning_effort: low` on the message (added to `ask()` as `effort=`) |

## Results

All rounds combined. "OK" means the turn completed and the score was 1.0.

| task | blueprint | effort | rounds | OK / runs | wall s, median (min–max) | input tokens, median | output tokens, median | tool calls, median |
|---|---|---|---|---|---|---|---|---|
| results | baseline | default | 1,2,4 | 8/9 | 50.7 (30.6–221.6) | 113,904 | 8,522 | 2 |
| results | digest | default | 1 | 2/3 | 149.0 (35.9–262.2) | 98,568 | 8,669 | 2 |
| results | single-heavy | default | 1,2 | 6/6 | 11.3 (8.7–85.9) | 26,498 | 2,152 | 2 |
| results | single-light | default | 1,2,3 | 8/9 | 8.9 (7.0–81.9) | 17,094 | 1,890 | 1 |
| results | **tuned** | default | 4 | **3/3** | **8.2 (7.7–9.0)** | **17,325** | **1,612** | 1 |
| hdf5 | baseline | default | 1,4 | 6/6 | 65.7 (33.2–296.4) | 95,658 | 6,344 | 2 |
| hdf5 | single-light | default | 1,3,4 | 8/9 | 23.6 (19.1–152.8) | 51,024 | 2,286 | 20 |
| hdf5 | **tuned** | default | 4 | **3/3** | **8.8 (7.0–88.1)** | **34,355** | **1,460** | 3 |
| results | baseline | low | 3 | 3/3 | 79.9 (43.4–127.1) | 245,699 | 19,785 | 4 |
| results | single-light | low | 3 | 2/3 | 9.3 (7.7–10.7) | 17,080 | 1,952 | 1 |
| hdf5 | baseline | low | 3 | 3/3 | 42.7 (31.4–81.8) | 97,192 | 5,342 | 2 |
| hdf5 | single-light | low | 3 | 3/3 | 19.6 (18.6–25.7) | 45,755 | 1,647 | 19 |

Round 2 alone (quiet gateway, same 3 rounds per variant): baseline 38.8 s and 114,625 input tokens, single-heavy 8.8 s and 17,633, single-light 7.8 s and 17,067; all 9 runs scored 1.0.

### Findings

1. **Delegation is the main cost.** The orchestrator re-sends a 15–17k-token context on each step and the child expert's grows to 21–27k (from `context_usage_by_scope`). A single expert stays near 9.6k. Dropping delegation cuts input tokens by 85 % (113,904 → 17,325) and wall time by 6x on `results` (50.7 → 8.2 s), with no loss of accuracy. Delegation also produced the worst failure: in digest round 1 `main` looped on `wait_agent_tasks`/`get_agent_task_output`/`observe_agent_tasks` until the 600 s timeout.
2. **Two prompt lines remove wasted calls.** Without them the single expert first tried `spawn_agent_task` (which it does not have) and ran shell outside the allowed roots; with them it needs 1 tool call. Input tokens fell from 35–44k (round 1) to about 17k.
3. **The digest alone barely helps** (child context 18.9–19.6k instead of 21–27k, total tokens about −10 %), because the per-step system prompt and tool schemas dominate, not the file.
4. **One HDF5 call instead of twenty.** `hdf5_analyze_dataset_structure` lists all 8 datasets in 10 ms. With it the HDF5 question needs 3 tool calls instead of 19–21, input tokens fall from 51,024 to 34,355 and the median time from 23.6 s to 8.8 s.
5. **Light vs heavy profile:** small effect (17,094 vs 26,498 tokens across rounds, 7.8 vs 8.8 s in round 2).
6. **Reasoning effort does not reach the model.** Direct requests to Minerva (`endpoint_bench.py`, temperature 0): the default is the same as `high` (1,471 completion tokens, 4.75 s); `reasoning_effort: low` gives 354 tokens in 1.3 s with the same numbers in the answer, and `none` is rejected. clio-agent stores the message's level (`behavior.reasoning_effort: low` in the message metadata) but sends nothing: it serves this model as `hosted_vllm`, has no thinking spec for it, and for the vLLM dialect an unknown spec maps to no request field (`lm/dialect_wire.py`, `_unknown_levels_wire`). So the round-3 `low` rows ran at the default level and their differences are noise. Passing `reasoning_effort` through would be worth up to about 3.5x fewer output tokens per step.
7. **Minerva is faster than Tara.** Same 456-token prompt, 400 output tokens, 3 runs each: Minerva time to first token 0.34–0.38 s and 362 tokens/s; Tara 0.72–4.41 s and 32–117 tokens/s. All output came in the `reasoning` delta field.
8. **The HDF5 MCP server starts in 2.1–2.3 s** when its uv environment is cached (3 timed starts), small next to model time. Pre-warming would save at most that much per first call.

### Failures seen (all variants)

- **Truncated answers (3 of 60 runs):** the stored `answer` part ended mid-sentence at 210, 250 and 514 characters (single-light round 1 run 2, single-light `low` round 3 run 2, baseline round 4 run 2). This is server side and affects both designs.
- **Stalls (2 runs):** digest round 1 (orchestrator wait loop, 600 s) and single-light `hdf5` round 4 run 3 (stuck after `hdf5_open_file`, 600 s, as in the first blueprint run of 2026-11-15).
- **Slow outliers:** tuned `hdf5` round 4 run 3 took 88.1 s but answered correctly.

## Recommendation

Use the tuned single-expert design for question answering: one expert with shell (running `report.py`) and the read-only HDF5 tools including `hdf5_analyze_dataset_structure`, light profile, the cwd and no-spawn lines. Keep the orchestrated blueprint only where delegation adds something (e.g. a long PBS workflow alongside file inspection). Upstream fixes worth filing: pass `reasoning_effort` for vLLM-served models with unknown thinking specs, and find the answer truncation.

## Related

- [agent_induced_seismicity.md](agent_induced_seismicity.md)
- [cae_hdf5_s3_vfd_vs_clio.md](cae_hdf5_s3_vfd_vs_clio.md)
