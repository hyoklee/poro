# poro: the PoroTomo agent for clio-agent 0.9.7.x

clio-agent 0.9.7 replaced agent blueprints with agents defined as Python classes
that carry plugins. This folder is a local plugin marketplace named `poro`. It
holds `poro/porotomo-is`, a port of the `porotomo-is-tuned` blueprint
(`../variants/porotomo-is-tuned/`), which still runs on 0.9.4.24. Since 2026-11-18
it is the default PoroTomo agent, run by clio-agent 0.9.7.1 from
`~/.local/share/clio/clio-agent-097/.venv`.

| file | role |
|---|---|
| `ai.iowarp.clio/marketplace.json` | marketplace name and description |
| `agents/porotomo_is.py` | the agent: `core` and `memory` (every agent), `shell`, `hdf5` (clio marketplace) and `porotomo-is` |
| `plugins/porotomo-is/plugin.json` | the plugin; it requires `shell` and `hdf5` |
| `plugins/porotomo-is/ai.iowarp.clio/prompt/*.md` | the blueprint's instructions as three prompt fragments (`mission`, `runs`, `hdf5`), each within the 150-token fragment budget |
| `plugins/porotomo-is/ai.iowarp.clio/tools/report.py` | the `porotomo_report` tool (since 0.4.0): the digest of a run's `summary.json`, from `agent/report.py` |
| `plugins/porotomo-is/ai.iowarp.clio/tools/h5.py` | the `porotomo_h5_layout` tool (since 0.5.0): every dataset of an HDF5 record with shape, dtype, chunks, compression and attributes; the `porotomo_h5_slice` tool (since 0.6.0): a slice's statistics and values |

How the blueprint maps to the port:

| blueprint (0.9.4.24) | plugin agent (0.9.7.x) |
|---|---|
| one expert, `tools:` list (`shell_bash`, 11 `hdf5_*` tools) | `shell` plugin plus the shipped `hdf5` plugin (clio-kit's HDF5 MCP server with all its tools, plus the HDF5 team's `hdf5` skill) |
| `mcp_servers: hdf5: clio-kit mcp-server hdf5` | the `hdf5` plugin's `mcp.json` (same command) |
| `prompt_profile: light` | no equivalent. The agent carries only `core`, `memory`, `shell` and `hdf5`, so its system prompt is about 16 KB, against about 27 KB for `clio/standard`. |
| the expert's Markdown body | the three prompt fragments |
| "never call `spawn_agent_task`" | dropped: the agent has no delegation plugin |
| "pass `workflow_state` as `{}`" (#2369 workaround) | dropped: 0.9.7.x uses native tool calls and needs no `submit` call |
| `CLIO_DEFAULT_AGENT_BLUEPRINT_ID` | `PATCH /v1/session-defaults {"agent_ref": "poro/porotomo-is"}` (done by `../start-0971.sh`), or `metadata.agent_ref` when the session is created |

## The `porotomo_report` tool

`porotomo_report(run="")` returns the ~1 KB digest that `agent/report.py` prints,
for a run name or path under `agent/results/` (empty: the latest finished run).
It loads `agent/report.py` from the repo (`POROTOMO_ROOT`, default `~/poro`), so
the script and the tool share one implementation, and it refuses any path that
is not a finished run there. It is read-only and needs no permission prompt.
It replaces `shell_bash` + `report.py` for run results: with the shell, the
model re-read `summary.json` with `python3 -c` one-liners in 25 of 30 questions
(round 11 in `wiki/agent_clio_performance.md`). `shell_bash` is still there for
PBS submission.

## The `porotomo_h5_layout` tool

`porotomo_h5_layout(path)` reads an HDF5 file's metadata with h5py (in the
server's venv) and returns, in one call, one line per dataset (path, shape,
dtype, chunks, compression, attributes) and the root attributes, about 3 KB for
a DASV record. It reads no data values, skips the dimension-scale reference
attributes, cuts values at 80 characters, and refuses files outside
`CLIO_ALLOWED_ROOTS`. It replaces the open / analyze / `hdf5_get_shape` /
`hdf5_get_dtype` / `hdf5_list_attributes` round trips through clio-kit's HDF5 MCP
server, which the model made even when told not to (round 12: median 4 calls,
up to 21; round 13 with this tool: one call, 3.2 s median).

## The `porotomo_h5_slice` tool

`porotomo_h5_slice(path, dataset, start, count, show=10)` reads one hyperslab
(`start` and `count` comma-separated per dimension, e.g. `"0,200"` and `"100,1"`)
and returns its n, NaN count, min, max, mean and std (float64, over the whole
slice) and its first `show` values (at most 1000) at full precision. It reads at
most 1,000,000 elements per call, so never the whole `/das` (11.5 M), and only
files under `CLIO_ALLOWED_ROOTS`. clio-kit's HDF5 server has no statistics over
a slice (`hdf5_aggregate_stats` works on whole datasets only), so without this
tool the model reads the slice with `hdf5_read_partial_dataset` and then computes
the statistics through `run_code` or the shell. On clio-kit 2.12.7 that took a
median of 14.8 s and 6 calls (round 17); with this tool, 2.5 s and one call
(round 15). clio-kit 2.10.6, installed here until 2026-11-18, made it worse: its
`hdf5_read_partial_dataset` showed only five values of a slice (round 14).

All three tools are declared `@tool(read_only=True, defer=False, callers="direct")`. With the
defaults, clio-agent 0.9.7.1 defers plugin tools (the model must find them with
`search_tools` first) and lets them be called from `run_code`; the model then
tried `run_code`, was denied and fell back to the shell.

Two lines are new in the port:
- The fragments say that the run digest and `hdf5_analyze_dataset_structure` are authoritative. Without that, the core plugin's "check the result before you report it" rule made the model re-read `summary.json` and re-check every dataset with `hdf5_get_shape` / `hdf5_get_dtype`.
- The `hdf5` fragment has no `when: {"tools": [...]}` condition. With one it was never included, because the condition is checked before the MCP server's tools are listed.

## Use

```bash
agent/clio-agent/start-alcf-mistral.sh minerva   # = start-0971.sh: installs or updates the marketplace, starts on :8100
```

or by hand, with a 0.9.7.x `clio-agent` and its own `CLIO_AGENT_HOME`:

```bash
clio-agent plugin check   agent/clio-agent/marketplace
clio-agent plugin install agent/clio-agent/marketplace --name poro
clio-agent plugin trust   poro
clio-agent plugin update  poro               # after editing: installs keep a snapshot
clio-agent plugin trust   poro               # again, if the update changed Python files
clio-agent plugin resolve poro/porotomo-is --prompt   # the composed system prompt
```

Start the server from an empty folder, not from `~/poro`. 0.9.7.1 adopts the
0.9.4 store in `<cwd>/.clio/agent` and resumes its sessions
([clio-agent #2375](https://github.com/iowarp/clio-agent/issues/2375)).

`../bench_0971.py --agent poro/porotomo-is --tasks results,hdf5` runs the
benchmark. Results are in `wiki/agent_clio_performance.md`, rounds 10–17.
