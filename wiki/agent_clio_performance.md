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

1. **Delegation is the main cost.** The orchestrator re-sends a 15–17k-token context on each step and the child expert's grows to 21–27k (from `context_usage_by_scope`). A single expert stays near 9.6k. Dropping delegation cuts input tokens by 85 % (113,904 → 17,325) and wall time by 6x on `results` (50.7 → 8.2 s), with no loss of accuracy. Delegation also makes a stall cost more: in digest round 1 the `seismicity` child's reasoning step never finished and `main` sat in one `wait_agent_tasks` call until the 600 s client timeout (see Failures).
2. **Two prompt lines remove wasted calls.** Without them the single expert first tried `spawn_agent_task` (which it does not have) and ran shell outside the allowed roots; with them it needs 1 tool call. Input tokens fell from 35–44k (round 1) to about 17k.
3. **The digest alone barely helps** (child context 18.9–19.6k instead of 21–27k, total tokens about −10 %), because the per-step system prompt and tool schemas dominate, not the file.
4. **One HDF5 call instead of twenty.** `hdf5_analyze_dataset_structure` lists all 8 datasets in 10 ms. With it the HDF5 question needs 3 tool calls instead of 19–21, input tokens fall from 51,024 to 34,355 and the median time from 23.6 s to 8.8 s.
5. **Light vs heavy profile:** small effect (17,094 vs 26,498 tokens across rounds, 7.8 vs 8.8 s in round 2).
6. **Reasoning effort does not reach the model.** Direct requests to Minerva (`endpoint_bench.py`, temperature 0): the default is the same as `high` (1,471 completion tokens, 4.75 s); `reasoning_effort: low` gives 354 tokens in 1.3 s with the same numbers in the answer, and `none` is rejected. clio-agent stores the message's level (`behavior.reasoning_effort: low` in the message metadata) but sends nothing: it serves this model as `hosted_vllm`, has no thinking spec for it, and for the vLLM dialect an unknown spec maps to no request field (`lm/dialect_wire.py`, `_unknown_levels_wire`). So the round-3 `low` rows ran at the default level and their differences are noise. Passing `reasoning_effort` through would be worth up to about 3.5x fewer output tokens per step. Filed as [clio-agent #2368](https://github.com/iowarp/clio-agent/issues/2368).
7. **Minerva is faster than Tara.** Same 456-token prompt, 400 output tokens, 3 runs each: Minerva time to first token 0.34–0.38 s and 362 tokens/s; Tara 0.72–4.41 s and 32–117 tokens/s. All output came in the `reasoning` delta field.
8. **The HDF5 MCP server starts in 2.1–2.3 s** when its uv environment is cached (3 timed starts), small next to model time. Pre-warming would save at most that much per first call.

### Why delegation costs more: experts share storage, not model context

One `results` question from round 5, from the stored sessions (`context_usage_by_scope`, per-session token totals):

| | orchestrated (`sess_46eb94d0d32e` + child `sess_994ddca7c0d9`) | tuned single expert (`sess_de528c31f800`) |
|---|---|---|
| model calls | about 3 (`main`) + about 4 (`seismicity` child) | about 2 |
| prompt size per call | `main` about 15.5k tokens, child about 23.3k | about 10.3k |
| input tokens re-sent in total | 40,010 + 88,076 = 128,086 | 19,871 |
| wall time | 42.0 s | 8.2 s |

1. **Each call re-sends the whole prompt.** The chat-completions API is stateless, so every step sends the expert's system prompt, tool schemas and conversation so far. The gateway reports `cache_read_tokens: 0` with `cache_tokens_measured: false`, so no prefix-cache reuse is visible.
2. **A child does not inherit the parent's context.** `main` writes a task brief, and the child builds its own context from scratch: its own system prompt and tools, the brief, and whatever it reads (`summary.json` alone is 7 KB). That is why the child's context grows to about 23k tokens.
3. **Results return as messages.** The child's answer comes back to `main` as a `wait_agent_tasks` tool result. When it is too long to inline (9,697 chars in one round-4 run), `main` makes another call, `get_agent_task_output`, which re-sends about 15k tokens.
4. **The steps run in series.** `main` decides and spawns → child calls a tool, reads the result, answers → `main` waits → `main` reads the result → `main` writes the answer. That is about 7 calls in a row against about 2. Each pays the model's fixed latency plus several hundred to about 1,500 reasoning tokens at about 360 tokens/s.

What clio-agent does share is storage: sessions and events persist in clio-core, the parent and child are linked by `parent_session_id`, and the parent can read the child's stored output. That saves bookkeeping, not model work, because every call is a new prompt.

Delegation pays off when children can run in parallel, or when a sub-task would otherwise swamp the main context (e.g. watching a long PBS job while inspecting files). For one short question it is overhead. What would narrow the gap without removing the extra serial calls: prefix caching on the serving side (vLLM supports it; the gateway reports none), a lighter child prompt (light profile, fewer tools), and returning a compact digest instead of the child's full output.

### Round 5: per-step output cap (2026-11-17)

`CLIO_LM_MAX_TOKENS=8192` (now the default in `start-alcf-mistral.sh`; clio-agent sends no cap when it is 0, its default). The value is far above a normal step (Minerva's largest direct completion here was 1,471 tokens) and bounds a runaway reasoning stream ([clio-agent #2371](https://github.com/iowarp/clio-agent/issues/2371)) to about 23 s at 362 tokens/s. Same 5 configurations x 3 reps as round 4, results in `agent/results/llm/bench_20261117_cap8k/`:

| task | blueprint | OK / runs | wall s, median (min–max) | input tokens, median | output tokens, median | round 4 (no cap): OK, wall s median (min–max) |
|---|---|---|---|---|---|---|
| results | baseline | 3/3 | 45.2 (42.0–48.6) | 128,086 | 9,755 | 2/3, 50.7 (30.6–58.1) |
| results | tuned | 3/3 | 8.8 (8.2–14.5) | 20,395 | 1,592 | 3/3, 8.2 (7.7–9.0) |
| hdf5 | baseline | 3/3 | 35.8 (34.6–61.1) | 86,930 | 5,133 | 3/3, 52.1 (46.2–79.2) |
| hdf5 | single-light | 3/3 | 22.7 (22.1–23.5) | 65,565 | 2,616 | 2/3, 21.0 (19.1–22.8) |
| hdf5 | tuned | 3/3 | 9.0 (7.9–9.0) | 39,516 | 1,373 | 3/3, 8.8 (7.0–88.1) |

- All 15 runs completed with accuracy 1.0: no truncated answer, no stall, and no `late_op rejected` line in the server log (round 4 had one truncation and one 600 s stall).
- The cap did not slow normal turns: the tuned medians are within 0.6 s of round 4. Baseline times are lower, which is within the gateway-load spread seen between rounds.
- The tuned input-token estimates are 15–18 % higher than in round 4 (20,395 vs 17,325; 39,516 vs 34,355) with the same tool calls; not explained, and these are clio-agent estimates, not gateway counts.
- What this does not show: stalls hit 3 of about 63 earlier turns (about 5 %), so 0 of 15 is expected about half the time even without a fix. Nothing hit the cap, so its behaviour on a runaway step (error, retry or truncated answer) is still untested. The cap is confirmed in the server's environment and in the code path (`lm/factory.py` passes `config.max_tokens` to the LM), not by capturing a request.

### Round 6: 60-question stall test, tuned blueprint with the cap (2026-11-17)

`porotomo-is-tuned`, `CLIO_LM_MAX_TOKENS=8192`, 30 `results` + 30 `hdf5` questions interleaved; results in `agent/results/llm/bench_20261117_stall60/`.

| task | completed | correct | wall s, median (p90, max) | input tokens, median | output tokens, median |
|---|---|---|---|---|---|
| results | 30/30 | 21/30 | 8.2 (9.8, 14.9) | 19,888 | 1,605 |
| hdf5 | 30/30 | 29/30 | 7.6 (8.9, 9.1) | 34,534 | 1,228 |

- **No stall in 60 questions** (slowest 14.9 s) and no `late_op rejected` line in the server log. Before the cap, stalls hit 3 of about 63 questions; at that rate, 0 of 60 would happen about 5 % of the time, so the cap very likely helps. No step reached the cap, so the stalls may also have been rare by chance; the cap's behaviour on a runaway step is still untested.
- **10 truncated answers (9 `results`, 1 `hdf5`), all traced to one cause** in clio-agent's output parsing, not the model ([clio-agent #2369](https://github.com/iowarp/clio-agent/issues/2369)). The model writes its final answer as a `submit` tool call in the `[[ ## tool_calls ## ]]` field. In each failing turn that JSON is complete except for one closing `}` at the very end, after a deeply nested `workflow_state` object. DSPy's `parse_value` (`dspy/adapters/utils.py`, dspy 3.3.0b1 in the clio-agent venv) passes every field to `json_repair.loads` (0.63.5) first, which re-splits the answer string at `, ` and `:`; the mangled dict still validates as `ToolCalls` (`args` is a free-form dict), so clio-agent's own fallback `_recover_malformed_structured_value` never runs (no `LENIENT-ADAPTER RECOVERY` event in any log). An earlier version of this page, and the 2026-11-17 comment on #2369, blamed that clio-agent fallback; corrected in round 8. For `sess_1b8b5d341f24` the repaired arguments are `{"answer": "... (stride 20", "2016-03-18T02": 9, "2016-03-26T00": 59, "window)": "n\n- Records analysed: 759 ...", ...}`; adding the one missing `}` makes the same text parse strictly with the full 1,537-character answer. The `hdf5` failure (`sess_9f1cc1421175`) is the same: one missing `}`, answer cut at `(0 subgroups)` with `/` as a new key. Reproduced offline with `json_repair.loads` and with DSPy's `parse_value(raw, ToolCalls)` on the raw output. This also explains why every truncated `results` answer, including the 2026-11-16 ones, ends at `(stride 20`, the first `, ` in the text.
- The truncation rate here (10/60) is higher than in rounds 1–5 (3 of about 70); not explained, but it does not involve the cap: the cut answers' output token counts (1,086–2,460) match complete ones.

### Round 7: tuned blueprint with an empty `workflow_state` (2026-11-17)

Workaround for the truncation, on our side: one line in the tuned expert's prompt (`variants/porotomo-is-tuned/experts/main.md`) tells it to put the whole answer in `submit`'s `answer` and pass `workflow_state` as `{}`. Same 30 + 30 questions and cap as round 6; results in `agent/results/llm/bench_20261117_emptystate/`.

| task | completed | correct (round 6) | wall s, median (p90, max) (round 6 median) | input tokens, median | output tokens, median (round 6) |
|---|---|---|---|---|---|
| results | 30/30 | 28/30 (21/30) | 6.5 (7.7, 9.7) (8.2) | 18,694 | 1,120 (1,605) |
| hdf5 | 30/30 | 30/30 (29/30) | 6.2 (7.3, 8.7) (7.6) | 27,874 | 839 (1,228) |

- Truncated answers fell from 10 to 2 in 60 questions, and the shorter `submit` call also cut output tokens by about 30 % and the median time by 1.4–1.7 s.
- Still no stall in 60 more questions (120 in a row with the cap, max 14.9 s), and no `late_op rejected` lines.
- **The two remaining failures are the same parser bug, which the prompt cannot remove**: the model still ends with `"workflow_state": {}}]}`, one `}` short, so the missing brace does not depend on nesting depth. Only the upstream fix ([clio-agent #2369](https://github.com/iowarp/clio-agent/issues/2369), root cause posted 2026-11-17) removes it.

### Round 8: local DSPy patch (2026-11-17)

`agent/clio-agent/patches/`: `apply_dspy_patch.py` (with `--revert`) inserts `dspy_parse_value_rebalance.py` into the clio-agent venv's `dspy/adapters/utils.py` (backup `utils.py.orig-clio-patch`; the applied change is `dspy-3.3.0b1-utils.py.diff`). `parse_value` then tries a strict `json.loads`; if that fails, it rebalances brackets outside string literals (inserts a missing `}`/`]` where a mismatched closer appears, appends missing closers at the end, drops stray closers after the top-level value is closed) and parses strictly again, logging `CLIO-LOCAL-PATCH`; only if that fails does the original `json_repair` path run. Valid JSON and non-JSON values parse as before. A clio-agent reinstall drops the patch.

Test: the round-6 prompt (no empty-`workflow_state` line, from a temporary blueprint copy `porotomo-is-tuned-r6` outside the repo), cap 8192, 30 `results` + 30 `hdf5` questions, the same test that gave 50/60 correct in round 6.

| run | patch | correct | results median s | hdf5 median s | `CLIO-LOCAL-PATCH` repairs |
|---|---|---|---|---|---|
| round 6 (`bench_20261117_stall60`) | none | 50/60 | 8.2 | 7.6 | – |
| `bench_20261117_dspypatch` | first version | 59/60 | 8.0 | 7.0 | 38 (all "+1": a missing closer) |
| `bench_20261117_dspypatch2` | final | **60/60** | 8.3 | 6.5 | 47 (37 missing closer, 10 misplaced: `...}}]}}` where the `}` belongs before `]`) |

- The one miss of the first version was the misplaced-brace form (`sess_74445a43286f`: balanced counts, `}` after `]`); the final version handles it, and both offline samples now parse with their full answers (1,537 and 2,053 characters).
- Malformed tool-call JSON is common, not rare: 38–47 repairs in 60 questions (some questions have more than one malformed step). Without the patch most of these happened to survive `json_repair` and only about 1 in 6 questions lost its answer.
- No stall in another 120 questions (240 in a row with the cap), no `late_op rejected` lines.
- With the patch the empty-`workflow_state` prompt line is no longer needed for correctness; it stays in the tuned blueprint because it also cuts output tokens by about 30 % and time by about 1.5 s (round 7).

### Round 9: clio-agent 0.9.7.1 (2026-11-17)

clio-agent 0.9.7.1 (released 2026-11-13; dspy 3.4.0, json_repair 0.64.9, litellm 1.102.2) removed agent blueprints. Agents are now Python classes in plugin marketplaces, and `POST /v1/sessions/{sid}/agent-blueprint` is gone. The SDK client moved to `clio_agent.client`, and the server rejects that client's own `agent_id` argument (422). Our blueprints were not ported. Instead, `agent/clio-agent/bench_0971.py` uses the built-in `clio/standard` agent, puts the tuned expert's instructions in front of the question, approves only shell tools, and scores with `bench.py`. The run used the round-6 prompt (`--no-submit-hint`), cap 8192 and Minerva Mistral Large 4, with 60 `results` questions (no `hdf5` task, because `standard` has no HDF5 MCP tools). The server was installed in a scratch venv and started from an empty folder with its own `CLIO_AGENT_HOME`. Started from `~/poro`, 0.9.7.1 adopts the 0.9.4.24 store in `~/poro/.clio/agent` and resumes old sessions at boot; filed as [clio-agent #2375](https://github.com/iowarp/clio-agent/issues/2375).

| run | clio-agent | agent | correct | median s (min–max) | model calls |
|---|---|---|---|---|---|
| round 6 (`bench_20261117_stall60`, results half) | 0.9.4.24, no patch | `porotomo-is-tuned-r6` | 21/30 | 8.2 | – |
| `bench_20261117_v0971` | 0.9.7.1, no patch | `clio/standard` + tuned instructions | **60/60** | 4.3 (3.7–17.9) | 125 (about 2 per question) |

- **#2369 is avoided in this run, but not fixed:** 0.9.7.1's `standard` agent calls tools through native function calling. The 125 model calls ended 65 times with `tool_call` and 60 times with `stop`, and the final answer came back as plain message text. None produced the `[[ ## tool_calls ## ]]` text field that DSPy's `parse_value` / `json_repair` parse. So the truncation path never ran: the shortest answer was 1,608 characters, and all 60 were fully correct. The DSPy bug itself is unchanged; replaying the saved malformed outputs offline through 0.9.7.1's DSPy 3.4.0 still cuts the answers at 92 and 235 characters. It matters again for any agent or provider that uses the text-field adapter. Closed #2369 on 2026-11-18 as not applying to 0.9.7.x: the agent loop no longer uses DSPy's adapter, which 0.9.7.1 keeps only for side modules such as the goal judge, the summarizer and review, which do not write the turn's answer.
- About twice as fast as 0.9.4.24: one `shell_bash` call plus the answer, without the separate `submit` step. Median input was about 28k tokens and output about 770 tokens per question.
- No stall in 60 questions and no `late_op rejected` lines. #2371 (no default output cap) and #2372 (stream not cancelled) are not fixed in the code; the cap was set.
- The comparison is not like for like: different agent (`standard`, its own 27k-character system prompt and tools), instructions in the user message, `results` task only.
- **What this means for us:** moving to 0.9.7.x would drop the need for the DSPy patch for this kind of question, but the blueprint has to be rewritten as a plugin agent (Python class) with the HDF5 MCP tools.

### Round 10: the tuned blueprint ported to a 0.9.7.x plugin agent (2026-11-18)

`agent/clio-agent/marketplace/` is a local plugin marketplace, `poro`. Its agent `poro/porotomo-is` carries `core` and `memory`, the clio marketplace's `shell` and `hdf5` plugins (clio-kit's HDF5 MCP server, the same command as the blueprint), and a `porotomo-is` plugin. That plugin holds the expert's instructions as three prompt fragments (`mission`, `runs`, `hdf5`). The `marketplace/README.md` maps each blueprint field to its 0.9.7.x counterpart. `agent/clio-agent/start-0971.sh` installs or updates and trusts the marketplace in a separate home, starts the server from an empty folder on port 8101 (because of #2375), and sets `poro/porotomo-is` as the session default. Both the fresh-install and the update paths were tested.

Fixes found while porting:
- A fragment with `when: {"tools": [...]}` naming an MCP tool was never included, because the condition is checked before the MCP server lists its tools. The `hdf5` fragment is unconditional now.
- The model called `report.py` with a bare run name. The fragment now asks for the full path.
- The core plugin's "check the result before you report it" rule made the model re-read `summary.json` and re-check every dataset with `hdf5_get_shape` / `hdf5_get_dtype` (20 calls for one listing). The fragments now say that `report.py` and `hdf5_analyze_dataset_structure` are authoritative.

Test (`bench_0971.py --agent poro/porotomo-is --tasks results,hdf5`; Minerva Mistral Large 4, cap 8192, 30 `results` + 30 `hdf5` questions, the round 6–8 test):

| run | clio-agent | agent | results | hdf5 | results median s (min–max) | hdf5 median s (min–max) |
|---|---|---|---|---|---|---|
| round 8 (`bench_20261117_dspypatch2`) | 0.9.4.24 + DSPy patch | `porotomo-is-tuned` (round-6 prompt) | 30/30 | 30/30 | 8.3 | 6.5 |
| round 9 (`bench_20261117_v0971`) | 0.9.7.1 | `clio/standard` + instructions in the question | 60/60 | – | 4.3 (3.7–17.9) | – |
| `bench_20261118_port0971` | 0.9.7.1, no patch | `poro/porotomo-is` | **30/30** | **30/30** | 5.9 (4.2–9.8) | 5.4 (3.6–9.1) |

- All 60 answers were fully correct, with no stall and no `late_op rejected` lines. No DSPy patch was needed (native tool calls, round 9).
- The port is faster than the blueprint on both tasks: 2.4 s faster on results and 1.1 s on HDF5.
- The model still adds some confirming calls, run in parallel so they cost little time. On `results`, 14 of 30 questions used one `shell_bash` and 16 used 2–4 (mostly a look at `summary.json`). On `hdf5`, every question called `hdf5_analyze_dataset_structure`, and most also called `hdf5_visit` or `hdf5_list_keys`. `hdf5_list_attributes` failed in 11 questions (each failure followed by more calls), but no answer was affected. The median was 5 tool calls.
- Median tokens per question (clio-agent's estimate): about 37k input and 1.0k output on `results`, and 61k input and 0.76k output on `hdf5`. The composed system prompt is about 16 KB, against 27 KB for `clio/standard`. Input is higher than round 9's `standard` run (about 28k) because of the extra steps.
- **The port has been the default since 2026-11-18.** clio-agent 0.9.7.1 (tag v0.9.7.1, commit f8ef50d) is installed in `~/.local/share/clio/clio-agent-097/.venv` with its own home. `start-alcf-mistral.sh` runs `start-0971.sh` on :8100, and `run_query.py` pins `poro/porotomo-is` on 0.9.7.x. `CLIO_AGENT_SERIES=0.9.4` still starts the 0.9.4.24 blueprint. Checked on the installed setup: the server started with no sessions (nothing adopted), the session default was `poro/porotomo-is`, and two `run_query.py` questions answered correctly (results 17.5 s on the first question after start, HDF5 5.3 s).

### Round 11: the installed default (2026-11-18)

The same test as round 10 (`bench_0971.py --agent poro/porotomo-is --tasks results,hdf5`, 30 + 30 questions, Minerva Mistral Large 4, cap 8192), run against the installed default: clio-agent 0.9.7.1 in `~/.local/share/clio/clio-agent-097/.venv`, started by `start-alcf-mistral.sh` on :8100 (`agent/results/llm/bench_20261118_default0971/`).

| run | results | hdf5 | results median s (min–max) | hdf5 median s (min–max) | median tool calls (results / hdf5) | median input tokens (results / hdf5) |
|---|---|---|---|---|---|---|
| round 10, scratch install (`bench_20261118_port0971`) | 30/30 | 30/30 | 5.9 (4.2–9.8) | 5.4 (3.6–9.1) | 2 / 5 | 37k / 61k |
| **round 11, installed default** | **30/30** | **30/30** | 6.7 (4.3–15.2) | 4.8 (3.5–14.6) | 3 / 4 | 38k / 48k |

- All 60 answers were fully correct, with no stall and no `late_op rejected` lines. The installed setup behaves like the scratch one.
- The model still re-checks `report.py` against `summary.json`, despite the "needs no cross-check" line. Only 5 of 30 `results` questions used a single `shell_bash` call; the others made 2–5 calls (9, 9, 5 and 2 questions), reading `summary.json` with small `python3 -c` one-liners. Round 10 had 14 of 30 with one call. The extra calls run in parallel, so the median grew only by 0.8 s. No shell call failed.
- On `hdf5`, the median fell to 4 calls (3–10) and 48k input tokens. 15 tool calls failed (`hdf5_list_attributes` again), and no answer was affected.
- Ways to cut the re-checking: firmer wording, or a dedicated `report` tool in the `porotomo-is` plugin instead of the general shell (done in round 12).

### Round 12: a `porotomo_report` tool (2026-11-18)

The `porotomo-is` plugin (0.4.0) adds a read-only Python tool, `porotomo_report(run)`, that returns the `report.py` digest of a run. The `runs` fragment now points at it instead of `shell_bash` + `report.py`; the shell stays for PBS. Same test as round 11 on the installed default (`agent/results/llm/bench_20261118_reporttool/`).

| run | results | hdf5 | results median s (min–max) | hdf5 median s (min–max) | median tool calls (results / hdf5) | median input tokens (results / hdf5) |
|---|---|---|---|---|---|---|
| round 11, `shell_bash` + `report.py` (`bench_20261118_default0971`) | 30/30 | 30/30 | 6.7 (4.3–15.2) | 4.8 (3.5–14.6) | 3 / 4 | 38k / 48k |
| **round 12, `porotomo_report`** | **30/30** | **30/30** | **4.0 (3.3–4.8)** | 4.8 (3.9–6.9) | **1** / 4 | **24k** / 61k |

- Every `results` question made exactly one call, `porotomo_report`, with no permission prompt and no re-check of `summary.json` (round 11: 5 of 30 with one call). The median fell from 6.7 s to 4.0 s, the slowest run from 15.2 s to 4.8 s, and input tokens from 38k to 24k.
- `hdf5` is unchanged in time and calls. 6 tool calls failed, none affecting an answer. One run made 21 calls (the model again checked shapes and dtypes one dataset at a time).
- The tool had to be declared `defer=False, callers="direct"`. With the defaults, 0.9.7.1 offers plugin tools only through `search_tools` and allows calls from `run_code`. In a first probe the model found the tool, tried it through `run_code` (denied by the benchmark) and fell back to the shell, with 4 calls per question.
- An update that changes a plugin's Python files is held until the marketplace is trusted again, so `start-0971.sh` now runs `plugin trust poro` after every update.

### Round 13: a `porotomo_h5_layout` tool (2026-11-18)

Round 12 left the `hdf5` question at a median of 4 calls through clio-kit's HDF5 MCP server (up to 21), because the model re-checked `hdf5_analyze_dataset_structure` with `hdf5_get_shape` / `hdf5_get_dtype` despite the prompt. The `porotomo-is` plugin (0.5.0) adds a second read-only Python tool, `porotomo_h5_layout(path)`: it reads the file's metadata with h5py and returns every dataset's path, shape, dtype, chunks, compression and attributes, plus the root attributes, in about 3 KB. The `hdf5` fragment now points at it and keeps the `hdf5_*` tools for data values. Same test on the installed default (`agent/results/llm/bench_20261118_h5layout/`).

| run | results | hdf5 | results median s (min–max) | hdf5 median s (min–max) | median tool calls (results / hdf5) | median input tokens (results / hdf5) |
|---|---|---|---|---|---|---|
| round 11, shell + MCP | 30/30 | 30/30 | 6.7 (4.3–15.2) | 4.8 (3.5–14.6) | 3 / 4 | 38k / 48k |
| round 12, `porotomo_report` | 30/30 | 30/30 | 4.0 (3.3–4.8) | 4.8 (3.9–6.9) | 1 / 4 | 24k / 61k |
| **round 13, + `porotomo_h5_layout`** | **30/30** | **30/30** | 3.8 (3.3–4.6) | **3.2 (2.8–4.1)** | **1 / 1** | 24k / **25k** |

- Every one of the 60 questions made exactly one tool call (`porotomo_report` or `porotomo_h5_layout`), with no permission prompt and no failed call (round 12: 6 failed `hdf5_*` calls).
- On `hdf5` the median fell from 4.8 s to 3.2 s, the slowest run from 6.9 s to 4.1 s, and input tokens from 61k to 25k. The HDF5 MCP server is no longer started for this question.
- The tool reads no data values and only files under `CLIO_ALLOWED_ROOTS`. Questions about values (samples of `/das`) still use the `hdf5_*` tools.

### Failures seen (all variants)

- **Truncated answers (3 of 60 runs):** the stored `answer` part ended mid-sentence at 210, 250 and 514 characters (single-light round 1 run 2, single-light `low` round 3 run 2, baseline round 4 run 2). This is server side and affects both designs: re-reading the sessions with `GET /v1/sessions/{sid}/messages` returns the same cut-off `answer` parts, while the turns report `completed` / `end_turn`. Filed as [clio-agent #2369](https://github.com/iowarp/clio-agent/issues/2369).
- **Stalls (2 runs):** digest round 1 (the `seismicity` child, after 2 `shell_bash` calls; `main` waiting in `wait_agent_tasks`) and single-light `hdf5` round 4 run 3 (after a successful `hdf5_open_file`), both 600 s on the client. Server-side cause, from the sessions and the server log: the model's next reasoning step streamed without end (no output cap is set for this model), and the session went to status `error` only at the turn wall, about 906 s after creation. The first blueprint run of 2026-11-15 (`sess_0ceddb7a5b4d`, 926 s) shows the same pattern, so the HDF5 MCP server was not the cause. The stream also kept running after the turn failed (5,625–7,146 rejected `late_op` deltas per session, at least about 9 min). Filed as [clio-agent #2371](https://github.com/iowarp/clio-agent/issues/2371) (unbounded step) and [#2372](https://github.com/iowarp/clio-agent/issues/2372) (stream not cancelled).
- **Slow outliers:** tuned `hdf5` round 4 run 3 took 88.1 s but answered correctly.

## Recommendation

Use the tuned single-expert design for question answering: one expert with shell (running `report.py`) and the read-only HDF5 tools including `hdf5_analyze_dataset_structure`, light profile, the cwd and no-spawn lines. Keep the orchestrated blueprint only where delegation adds something (e.g. a long PBS workflow alongside file inspection). Adopted 2026-11-17: `porotomo-is-tuned` became the default in `start-alcf-mistral.sh` and `run_query.py`. Since 2026-11-18 the default is its clio-agent 0.9.7.1 port, `poro/porotomo-is` (round 10), which reads run results and HDF5 layouts with its own `porotomo_report` and `porotomo_h5_layout` tools (rounds 12 and 13). Upstream issues filed 2026-11-17: [clio-agent #2368](https://github.com/iowarp/clio-agent/issues/2368) (pass `reasoning_effort` for vLLM-served models with unknown thinking specs) and [clio-agent #2369](https://github.com/iowarp/clio-agent/issues/2369) (answer truncation; closed 2026-11-18 because it does not apply to 0.9.7.x, while the local DSPy patch is still needed on 0.9.4.24). The 0.9.7.1 store adoption is [clio-agent #2375](https://github.com/iowarp/clio-agent/issues/2375). The stalls are [clio-agent #2371](https://github.com/iowarp/clio-agent/issues/2371) and [#2372](https://github.com/iowarp/clio-agent/issues/2372).

## Related

- [agent_induced_seismicity.md](agent_induced_seismicity.md)
- [cae_hdf5_s3_vfd_vs_clio.md](cae_hdf5_s3_vfd_vs_clio.md)
