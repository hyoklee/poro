---
id: porotomo-is-tuned
title: PoroTomo IS (tuned, default)
version: 0.2.0
description: Default PoroTomo induced-seismicity blueprint. One expert (no delegation), light profile, report.py digest, and one-call HDF5 structure listing; about 6x faster than porotomo-induced-seismicity at the same accuracy.
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

# PoroTomo IS, tuned single-expert blueprint (default)

See ../../porotomo-induced-seismicity/AGENT.md for the full blueprint.
