# poro: the PoroTomo agent for clio-agent 0.9.7.x

clio-agent 0.9.7 replaced agent blueprints with agents defined as Python classes
that carry plugins. This folder is a local plugin marketplace named `poro`. It
holds `poro/porotomo-is`, a port of the `porotomo-is-tuned` blueprint
(`../variants/porotomo-is-tuned/`), which still runs on 0.9.4.24.

| file | role |
|---|---|
| `ai.iowarp.clio/marketplace.json` | marketplace name and description |
| `agents/porotomo_is.py` | the agent: `core` and `memory` (every agent), `shell`, `hdf5` (clio marketplace) and `porotomo-is` |
| `plugins/porotomo-is/plugin.json` | the plugin; it requires `shell` and `hdf5` |
| `plugins/porotomo-is/ai.iowarp.clio/prompt/*.md` | the blueprint's instructions as three prompt fragments (`mission`, `runs`, `hdf5`), each within the 150-token fragment budget |

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

Two lines are new in the port:
- The fragments say that `report.py` and `hdf5_analyze_dataset_structure` are authoritative. Without that, the core plugin's "check the result before you report it" rule made the model re-read `summary.json` and re-check every dataset with `hdf5_get_shape` / `hdf5_get_dtype`.
- The `hdf5` fragment has no `when: {"tools": [...]}` condition. With one it was never included, because the condition is checked before the MCP server's tools are listed.

## Use

```bash
agent/clio-agent/start-0971.sh            # installs or updates the marketplace, starts on :8101
```

or by hand, with a 0.9.7.x `clio-agent` and its own `CLIO_AGENT_HOME`:

```bash
clio-agent plugin check   agent/clio-agent/marketplace
clio-agent plugin install agent/clio-agent/marketplace --name poro
clio-agent plugin trust   poro
clio-agent plugin update  poro               # after editing: installs keep a snapshot
clio-agent plugin resolve poro/porotomo-is --prompt   # the composed system prompt
```

Start the server from an empty folder, not from `~/poro`. 0.9.7.1 adopts the
0.9.4 store in `<cwd>/.clio/agent` and resumes its sessions
([clio-agent #2375](https://github.com/iowarp/clio-agent/issues/2375)).

`../bench_0971.py --agent poro/porotomo-is --tasks results,hdf5` runs the
benchmark. Results are in `wiki/agent_clio_performance.md`, round 10.
