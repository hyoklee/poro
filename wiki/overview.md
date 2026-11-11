# Overview — PoroTomo DAS

PoroTomo (DOE project EE0006760, University of Wisconsin, PI Kurt Feigl) instrumented the Brady Hot Springs geothermal field in Nevada in March 2016 to test **poroelastic tomography**: image where fluid flows in a reservoir by watching how the ground strains as pumping changes. Two distributed acoustic sensing (DAS) deployments produced the data this wiki is about:

- **DASH** — fiber in a zigzag trench across the field (8.7 km of cable), recorded 2016-03-08 to 2016-03-26.
- **DASV** — fiber down the first 363 m of a vertical well, recorded 2016-03-17 to 2016-03-28.

Both are archived as 30-second files in SEG-Y, native DAS-HDF5-1.0 and a GDR "standardized" HDF5 layout, about 172 TB and 33 million objects in the public OEDI bucket `s3://nrel-pds-porotomo/`. See [source-gdr-submission-980.md](source-gdr-submission-980.md) and [source-s3-nrel-pds-porotomo.md](source-s3-nrel-pds-porotomo.md).

## Why it matters here

1. **Science**: the strain records plus the pumping schedule, vibroseis sweeps and nodal seismometers feed inversions for hydraulic diffusivity and seismic velocity ([concept-poroelastic-tomography.md](concept-poroelastic-tomography.md)). The same physics governs induced seismicity ([concept-induced-seismicity-pohang.md](concept-induced-seismicity-pohang.md)) and CO2 storage monitoring.
2. **Data engineering**: millions of 30 s files make this a textbook small-object workload, and the native HDF5 release is nearly twice the SEG-Y size while the standardized HDF5 is smaller than SEG-Y ([concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)).
3. **IOWarp**: one DASV record (46 MB, 8 datasets) is the reference workload for the Context Assimilation Engine's selective HDF5 ingestion through OMNI files, verified byte-for-byte on Linux and Windows ([cae_omni_porotomo_dasv.md](cae_omni_porotomo_dasv.md)).

## Open threads

- Only one DASV record has been inspected; DASH files (1 GB each) have not been ingested yet.
- Sibling GDR submissions 825 and 829 hold the DAS metadata and the DASH deployment history; neither has a source page yet.
- Recording gaps and the pumping schedule live outside submission 980.
