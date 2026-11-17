---
id: porotomo-is-single-heavy
title: PoroTomo IS (bench: single expert, heavy)
version: 0.1.0
description: Benchmark variant of porotomo-induced-seismicity with one expert that holds the shell and HDF5 tools itself (no delegation); prompt profile heavy.
default_expert: main
a2ui_catalogs:
  - clio-workspace
mcp_servers:
  hdf5: clio-kit mcp-server hdf5
experts:
  - experts/main.md
defaults:
  prompt_profile: heavy
---

# PoroTomo IS, single-expert benchmark variant

See ../../porotomo-induced-seismicity/AGENT.md for the full blueprint.
