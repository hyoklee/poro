# Wiki Index

## Overview

- [Overview](overview.md) — what PoroTomo is, why its DAS data matters, and where this wiki stands

## Sources

- [GDR submission 980](source-gdr-submission-980.md) — the DAS release page: authors, windows, resource sizes and counts
- [s3://nrel-pds-porotomo/](source-s3-nrel-pds-porotomo.md) — bucket layout, file naming, files fetched so far
- [PoroTomo_iDAS025_160318160317.h5](source-dasv-PoroTomo_iDAS025_160318160317.md) — one DASV record in native and standardized HDF5 (8 and 2 datasets)

## Concepts

- [The PoroTomo project](concept-porotomo-project.md) — DOE EE0006760, Brady Hot Springs natural laboratory, March 2016
- [Poroelastic tomography](concept-poroelastic-tomography.md) — inverting strain response to pumping for hydraulic and elastic properties
- [Distributed acoustic sensing](concept-das.md) — how fiber becomes a strain sensor; DASH vs DASV
- [GDR, OEDI and HSDS](concept-gdr-oedi-hsds.md) — the repository, the S3 buckets, the HDF5-over-HTTP service
- [The three storage layouts](concept-das-hdf5-layouts.md) — SEG-Y vs native HDF5 vs GDR standardized HDF5, and what to select
- [Induced seismicity and Pohang](concept-induced-seismicity-pohang.md) — why pressure diffusion matters: the 2017 M5.4 EGS earthquake

## CAE experiments

- [Selective ingestion of one DASV record](cae_omni_porotomo_dasv.md) — OMNI with dataset filters, verified byte-for-byte on Linux and Windows; bugs found

## Schema

- [CLAUDE.md](CLAUDE.md) — page conventions and workflows
