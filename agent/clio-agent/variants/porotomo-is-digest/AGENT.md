---
id: porotomo-is-digest
title: PoroTomo IS (bench: digest)
version: 0.1.0
description: Finds anomalies in PoroTomo DAS records that could indicate injection-induced seismicity at Brady Hot Springs, runs the detection on Aurora through PBS, and estimates the probability of a Pohang-like (Mw >= 5.5) event with the Shapiro seismogenic-index model.
default_expert: main
a2ui_catalogs:
  - clio-workspace
mcp_servers:
  hdf5: clio-kit mcp-server hdf5
  pandas: clio-kit mcp-server pandas
  plot: clio-kit mcp-server plot
experts:
  - experts/main.md
  - experts/hdf5.md
  - experts/seismicity.md
defaults:
  prompt_profile: heavy
---

# PoroTomo Induced-Seismicity Agent

Blueprint for clio-agent. The numeric work lives in plain scripts in this
repository so it can run on PBS compute nodes without an LLM:

- `agent/manifest.py`: list the DASV records on `s3://nrel-pds-porotomo/` and sample them.
- `agent/detect.py`: per-record detector (common-mode removal, 10-150 Hz band-pass, median STA/LTA).
- `agent/pbs/submit.sh`: submit the distributed detection plus aggregation job to Aurora.
- `agent/hazard.py`: anomaly z-scores, event catalogue, pumping volumes, seismogenic index, probabilities.

The experts orchestrate those scripts, inspect files, and explain results. They
never make up numbers. Every figure they report comes from `summary.json` or a
tool result.

Install by linking this directory into `~/.config/clio-agent/agent-blueprints/`.
