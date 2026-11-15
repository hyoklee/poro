# Source: triggered MEQ events on LBNL's Brady array, March 2016 (GDR 859)

GDR submission 859, "Triggered MEQ Events on LBNL Permanent Seismic Array, Brady's EGS, March 2016" (https://gdr.openei.org/submissions/859). The single file, `BradysEGS_triggeredEvents_NCEDC_catalog_March2016.pdf` (85,992 B), is an export from the NCEDC EGS catalogue (https://www.ncedc.org/egs/catalog-search.html). Fetched 2026-11-15 to `agent/sources/`; its text is in `brady_meq_ncedc_march2016.txt`.

## Content

5 events, all ML, source LBL:

| Time (UTC) | Lat | Lon | Depth MSL (km) | ML |
|---|---|---|---|---|
| 2016-03-14 06:47:46.45 | 39.79377 | −119.01800 | −0.106 | −0.17 |
| 2016-03-14 08:36:26.61 | 39.79442 | −119.02161 | −0.426 | −0.48 |
| 2016-03-14 08:39:05.23 | 39.79350 | −119.01717 | −0.106 | 0.07 |
| 2016-03-14 12:11:34.92 | 39.79328 | −119.01897 | −0.119 | 0.05 |
| 2016-03-16 22:03:10.24 | 39.79222 | −119.01427 | −0.424 | −0.29 |

All 5 fall in the full-field shutdown of 2016-03-13 21:17 to 03-18 12:12 ([source-brady-pumping-gdr917.md](source-brady-pumping-gdr917.md)) and before the first DASV record.

## Used by

- [agent_induced_seismicity.md](agent_induced_seismicity.md): the calibrated catalogue behind the seismogenic index.
