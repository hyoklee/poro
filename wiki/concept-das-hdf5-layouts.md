# Concept: the three PoroTomo storage layouts

| Layout | DASH size | DASV size | Notes |
|---|---|---|---|
| SEG-Y | 46.4 TB | 980 GB | 30 s files, one per record |
| Native DAS-HDF5-1.0 | 81.2 TB | 1.34 TB | `/das` chunked (2000, 384), uncompressed, plus `/t`, `/trace`, `/channel`, `/x`, `/y`, `/z`, `/crs`; CF/ACDD root attributes |
| GDR standardized HDF5 | 38.9 TB | 984 GB | `/DasRawData/RawData` contiguous, `/DasRawData/DasTimeArray` uint64; acquisition metadata as group attributes under `/DasMetadata` |

Observations from the one DASV record inspected ([source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md)):

- The strain payload is 46,080,000 bytes in both HDF5 layouts; the native file is only 246 KB larger for one record. The 2x gap at collection scale (81 TB vs 39 TB for DASH) therefore comes from the DASH files, not from the extra DASV vectors.
- The native file is chunked (2000 x 384 float32 = 3 MB chunks) with no filter; the standardized file is contiguous.
- Per-object overhead dominates at 33 million S3 objects; HSDS daily files exist to fix that for remote access.

## Implication for selective ingestion

A strain-rate waterfall plot needs only `/das`, `/t` and `/z` from a native file, or `/DasRawData/*` from a standardized one. The CAE OMNI in [cae_omni_porotomo_dasv.md](cae_omni_porotomo_dasv.md) encodes exactly that.

## Related

- [concept-gdr-oedi-hsds.md](concept-gdr-oedi-hsds.md)
- [concept-das.md](concept-das.md)
