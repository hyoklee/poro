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

### DASV coverage on the bucket

Records per day folder under `DAS/H5/DASV/` (from `agent/results/run_20261115T155359Z_s20/manifest.log`, listed 2026-11-15). A full day is 2,880 records of 30 s.

| Folder | Records |
|---|---|
| 20160317 | 2 (both start on 2016-03-18: `160318160317`, `160318203917`) |
| 20160318 | 2,622 |
| 20160319 | 469 |
| 20160320 | 426 |
| 20160321 | 2,880 |
| 20160322 | 101 |
| 20160323 | 2,880 |
| 20160324 | 2,880 |
| 20160325 | 2,781 |
| 20160326 | 123 |
| Total | 15,164 |

So the HDF5 DASV data runs from 2016-03-18 02:09:17 to early 2016-03-26 UTC, with large gaps on 03-19, 03-20 and 03-22. [source-gdr-submission-980.md](source-gdr-submission-980.md) gives the DASV window as 2016-03-17 to 2016-03-28; no folder after `20160326` exists under this prefix. Whether the remaining records exist in another format (e.g. SEG-Y) has not been checked.

Size of `DAS/H5/DASV/` (anonymous listing, 2026-11-16): the day folders 20160318 to 20160326 hold 15,162 records, 706,258,848,880 B (706.3 GB). The 759 records used by [agent_induced_seismicity.md](agent_induced_seismicity.md) are all 46,590,272 B.

## Files fetched so far

| Key | Bytes | Local name |
|---|---|---|
| `DAS/H5/DASV/20160317/PoroTomo_iDAS025_160318160317.h5` | 46,590,272 | `dasv_native_PoroTomo_iDAS025_160318160317.h5` |
| `DAS/H5-standardized/DASV/20160317/PoroTomo_iDAS025_160318160317.h5` | 46,344,096 | `dasv_std_PoroTomo_iDAS025_160318160317.h5` |

Both are described in [source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md). The download script is `cae/porotomo/download_porotomo.sh` in this repository.

## Related

- [source-gdr-submission-980.md](source-gdr-submission-980.md)
- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
