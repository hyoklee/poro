# Source: PoroTomo_iDAS025_160318160317.h5 (DASV, 30 s starting 2016-03-18 16:03:17)

One vertical-DAS record from the Brady well fiber, in both GDR layouts. Inspected with h5py 2026-11-10.

## Native DAS-HDF5-1.0 file (46,590,272 B)

Root attributes: `Conventions = ['DAS-HDF5-1.0' 'CF-1.7' 'ACDD-1.3']`, `creator_name = Kurt Feigl`, `creator_institution = Uni. Wisconsin`, `date_created = 2020-07-31T02:52:24Z`, `geospatial_lat_min/max` about 39.80057, `geospatial_lon_min/max` about -119.00954 (a single well, so the box is a point).

| Dataset | dtype | shape | chunks | bytes | meaning |
|---|---|---|---|---|---|
| `/das` | float32 | (30000, 384) | (2000, 384) | 46,080,000 | strain-rate samples, time by channel |
| `/t` | float64 | (30000,) | (30000,) | 240,000 | sample times |
| `/trace` | int64 | (30000,) | (30000,) | 240,000 | sample index |
| `/channel` | int32 | (384,) | contiguous | 1,536 | channel numbers |
| `/x`, `/y`, `/z` | float32 | (384,) | contiguous | 1,536 each | channel coordinates; `/z` is depth along the well |
| `/crs` | uint8 | scalar | — | 1 | CF grid-mapping placeholder |

No compression anywhere. 30,000 samples per 30 s record means a 1 kHz sample rate; 384 channels along 363 m of fiber.

## GDR standardized file (46,344,096 B)

Metadata moved into group **attributes** (no datasets): `/DasMetadata` (Country, DigitalObjectIdentifier, EndDate, FundingAgency, Location, MetadataStandard, NetworkCode, Overview, PointOfContact, ...), `/DasMetadata/Cable` (bounding box, installation date and environment, model, diameter, owner, ...), `/DasMetadata/Cable/Fiber` (geometry, mode, attenuation, optical length, refraction index, start/end location), `/DasMetadata/Interrogator` (manufacturer, model, serial, firmware), `/DasMetadata/Interrogator/Acquisition` (sample rate, start/end time, gauge length, number of channels, pulse rate and width), `/DasMetadata/Interrogator/Acquisition/ChannelGroup` (first/last usable channel).

| Dataset | dtype | shape | chunks | bytes |
|---|---|---|---|---|
| `/DasRawData/RawData` | float32 | (30000, 384) | contiguous | 46,080,000 |
| `/DasRawData/DasTimeArray` | uint64 | (30000,) | contiguous | 240,000 |

The payload is identical in size; the standardized file drops `/trace`, `/channel`, `/x`, `/y`, `/z`, `/crs` and stores the time axis as uint64.

## Used by

- [cae_omni_porotomo_dasv.md](cae_omni_porotomo_dasv.md) — reference workload for CAE selective ingestion.

## Related

- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
- [concept-das.md](concept-das.md)
