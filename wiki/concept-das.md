# Concept: distributed acoustic sensing (DAS)

## Definition

DAS turns an optical fiber into a dense line of strain sensors. An interrogator sends laser pulses down the fiber and measures changes in Rayleigh backscatter; strain between two points a gauge length apart shifts the backscatter phase. Each channel is a short fiber segment, so a kilometre of cable yields hundreds of sensors at a fraction of the cost of seismometers.

## In PoroTomo

- Interrogator names appear in the file names: `iDAS16043` for the trenched horizontal array (DASH), `iDAS025` for the well (DASV).
- DASV: 384 channels over 363 m of well fiber, 1 kHz sampling, stored as float32 strain rate ([source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md)).
- DASH: 8.7 km zigzag trench; each 30 s native HDF5 file is about 1 GB.
- Tap tests on 2016-03-08/09 locate channels along the cable.

## Why the dataset is a benchmark

Earthquakes, traffic, pumping noise, vibroseis sweeps and tap tests are all present in the raw records, which makes it a standard public test set for DAS event detection and machine learning, and the 172 TB / 33 million-object scale makes it a stress test for storage layouts ([concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)).

## Related

- [concept-poroelastic-tomography.md](concept-poroelastic-tomography.md)
- [concept-porotomo-project.md](concept-porotomo-project.md)
