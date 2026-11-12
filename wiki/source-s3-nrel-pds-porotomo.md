# Source: s3://nrel-pds-porotomo/ (OEDI public bucket)

Anonymous HTTPS listing works: `https://nrel-pds-porotomo.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=<prefix>`.

## Layout (observed 2026-11-10)

```
DAS/
  H5/
    DASH/<YYYYMMDD>/PoroTomo_iDAS16043_<yymmddHHMMSS>.h5      ~1,047,162,640 B each
    DASH_NV-test-site-explosion_standardized/
    DASV/<YYYYMMDD>/PoroTomo_iDAS025_<yymmddHHMMSS>.h5        ~46,590,272 B each
  H5-standardized/
    DASH/<YYYYMMDD>/...
    DASV/<YYYYMMDD>/PoroTomo_iDAS025_<yymmddHHMMSS>.h5        ~46,344,096 B each
  SEG-Y/
Nodal/
```

DASV day folders start at `20160317`. The file-name timestamp is the record start (e.g. `160318160317` = 2016-03-18 16:03:17 UTC) and each file holds 30 s.

## Files fetched so far

| Key | Bytes | Local name |
|---|---|---|
| `DAS/H5/DASV/20160317/PoroTomo_iDAS025_160318160317.h5` | 46,590,272 | `dasv_native_PoroTomo_iDAS025_160318160317.h5` |
| `DAS/H5-standardized/DASV/20160317/PoroTomo_iDAS025_160318160317.h5` | 46,344,096 | `dasv_std_PoroTomo_iDAS025_160318160317.h5` |

Both are described in [source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md). The download script is `cae/porotomo/download_porotomo.sh` in this repository.

## Related

- [source-gdr-submission-980.md](source-gdr-submission-980.md)
- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
