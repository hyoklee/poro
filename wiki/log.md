# Wiki Log

## [2026-11-11] bootstrap | Create the poro wiki from the NeuroFAIR template

Instantiated the llm-wiki pattern (`llm-wiki.md`, copied from hyoklee/NeuroFAIR) for the PoroTomo DAS dataset. Wrote the schema (`wiki/CLAUDE.md`), `overview.md`, three source pages (GDR submission 980, the `nrel-pds-porotomo` S3 bucket, the DASV record `PoroTomo_iDAS025_160318160317.h5` in both layouts), six concept pages (project, poroelastic tomography, DAS, GDR/OEDI/HSDS, storage layouts, induced seismicity/Pohang) and one experiment page (`cae_omni_porotomo_dasv.md`) recording the clio-core CAE round trips of 2026-11-10 (Linux, WSL) and 2026-11-11 (Windows, oneAPI icx-cl) and the three bugs they surfaced. All facts come from the GDR page, anonymous S3 listings, h5py inspection of the two 46 MB files, and the recorded test runs; the DASH files have not been ingested yet.
