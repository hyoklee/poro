---
id: porotomo-is-tuned
title: PoroTomo IS (bench: tuned)
version: 0.1.0
description: Benchmark variant of porotomo-induced-seismicity with one expert (no delegation), light profile, report.py digest, and one-call HDF5 structure listing.
default_expert: main
a2ui_catalogs:
  - clio-workspace
mcp_servers:
  hdf5: clio-kit mcp-server hdf5
experts:
  - experts/main.md
defaults:
  prompt_profile: light
---

# PoroTomo IS, single-expert benchmark variant

See ../../porotomo-induced-seismicity/AGENT.md for the full blueprint.
