# Wiki Index

## Overview

- [Overview](overview.md) — what PoroTomo is, why its DAS data matters, and where this wiki stands

## Sources

- [GDR submission 980](source-gdr-submission-980.md) — the DAS release page: authors, windows, resource sizes and counts
- [s3://nrel-pds-porotomo/](source-s3-nrel-pds-porotomo.md) — bucket layout, file naming, files fetched so far
- [PoroTomo_iDAS025_160318160317.h5](source-dasv-PoroTomo_iDAS025_160318160317.md) — one DASV record in native and standardized HDF5 (8 and 2 datasets)

- [Brady pumping, GDR 917](source-brady-pumping-gdr917.md) — per-minute injection/extraction flows, 2016-03-11 to 03-27; shutdown windows and volumes
- [Brady MEQ catalogue, GDR 859](source-brady-meq-catalog-gdr859.md) — 5 LBNL events, March 2016, ML −0.48 to 0.07, all during the shutdown
- [Shapiro, Kim & Ree 2021](source-shapiro-2021-pohang.md) — Pohang seismogenic index, b-values, 15–17 % worst-case probability

## Concepts

- [The PoroTomo project](concept-porotomo-project.md) — DOE EE0006760, Brady Hot Springs natural laboratory, March 2016
- [Poroelastic tomography](concept-poroelastic-tomography.md) — inverting strain response to pumping for hydraulic and elastic properties
- [Distributed acoustic sensing](concept-das.md) — how fiber becomes a strain sensor; DASH vs DASV
- [GDR, OEDI and HSDS](concept-gdr-oedi-hsds.md) — the repository, the S3 buckets, the HDF5-over-HTTP service
- [The three storage layouts](concept-das-hdf5-layouts.md) — SEG-Y vs native HDF5 vs GDR standardized HDF5, and what to select
- [Induced seismicity and Pohang](concept-induced-seismicity-pohang.md) — why pressure diffusion matters: the 2017 M5.4 EGS earthquake
- [Seismogenic index](concept-seismogenic-index.md) — Σ, the Shapiro exceedance-probability model, Pohang vs Brady values

## CAE experiments

- [Selective ingestion of one DASV record](cae_omni_porotomo_dasv.md) — OMNI with dataset filters, verified byte-for-byte on Linux and Windows; bugs found

## Agent runs

- [DAS anomalies and Pohang-like earthquake probability](agent_induced_seismicity.md) — 759 DASV records on Aurora via PBS; detections are diurnal noise; P(Mw≥5.5) ≈ 1e-4/yr at Brady (b=1)

## Schema

- [CLAUDE.md](CLAUDE.md) — page conventions and workflows
