# CAE: HDF5 S3 VFD vs the CLIO stack, and cloud-optimized PoroTomo HDF5

Runs of 2026-11-16 on the Aurora login node `aurora-uan-0012`. Code and raw results: [`bench/hdf5_s3/`](../bench/hdf5_s3/README.md) (`results/real_s3_20261116T035249Z/`, `results/layouts_20261116T040034Z/`).

## Setup

| | HDF5 S3 VFD path | CLIO path |
|---|---|---|
| Software | HDF5 2.1.0 (conda-forge, ROS3 VFD on `aws-c-s3` 0.11.5), `ros3_bench.c` built with gcc | clio-core `clio-core.dev.wrk` at `100c062bb` (2026-11-12), Release, icpx 2026.1.0, `CLIO_CORE_ENABLE_CAE=ON`, `CLIO_CORE_ENABLE_HDF5=ON`, `CAE_ENABLE_S3=ON` (Poco 1.15.1, aws-sdk-cpp 1.11.747), installed to `~/clio-core.dev.wrk/install_s3`; `clio_s3_bench.cc` |
| How data moves | each `H5Fopen` issues ranged GETs; nothing persists between opens | CAE `S3FileAssimilator` copies the object into a CTE tag (1 MiB blobs, 8 striped streams of 16 MiB parts); readers fetch the blobs and open them as an HDF5 file image (core driver) |
| Runtime | none | single-node `clio_run`, CTE RAM tier 4 GB, 8 worker threads, port 10700 |

Access patterns on one DASV record ([source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md)), each from a fresh open: `meta` (open, list the 8 datasets' shape and dtype), `full` (all of `/das`, 46.08 MB), `window` (rows 10000–10999 on all 384 channels, 1.5 MB), `channel` (column 200 over 30,000 rows, 120 kB).

## Real S3: public NREL object, us-west-2

Object `DAS/H5/DASV/20160317/PoroTomo_iDAS025_160318160317.h5`, 46,590,272 B. Baselines with curl (new TLS connection each, median of 5): 1-byte range 0.304 s, 3 MB range 0.805 s, whole object 1.65 s (about 28 MB/s).

| pattern | ROS3, median of 5 (ms) | CLIO first access: stage + read-back + open + read (ms) | CLIO later accesses from CTE (ms, median of 9) |
|---|---|---|---|
| meta | 1,450 | 1,570 | 54 |
| window | 1,516 | 1,571 | 56 |
| channel | 2,520 | 1,579 | 63 |
| full | 2,490 | 1,600 | 84 |

- **ROS3 pays about 1.4 s on every open** (median open 1,404–1,449 ms across patterns). Its request trace shows why: a HEAD, then a GET of the first 16 MiB (it fetches this cache on every open), then a 168 B GET for metadata near the end of the file (offset 46,108,224), then one GET per chunk. `channel` needs 10 more 3,072,000 B chunk GETs (15 chunks; 5 are inside the first 16 MiB), so it costs as much as reading everything.
- **CLIO stages the whole object once** (1,515–1,615 ms, 3 runs, about 30 MB/s, the same rate as one curl), then every reader gets the bytes from CTE in 21–54 ms, opens the image in about 23 ms and reads in 1–44 ms. After the first access CLIO is 27–40x faster than ROS3 (1,450/54 to 2,520/63); on the first access it wins for `channel` and `full` and loses by about 50–120 ms for `meta` and `window`, because it moves 46.6 MB where ROS3 moves about 20 MB.
- **ROS3 startup trap:** with `authenticate = false` and no `~/.aws` files, HDF5 2.1's ROS3 still runs the AWS credential chain and probes the EC2 instance-metadata address 169.254.169.254, which times out on Aurora. Opens took 5.5–5.9 s until `AWS_EC2_METADATA_DISABLED=true` was set (then about 1.4 s).

## Cloud-optimized rewrites

No writable S3 bucket or AWS credentials were available, so the rewritten files were served by `s3_mock.py`, a stdlib S3-compatible server, with a 10 ms delay per request and a 28 MB/s cap per response. Those values reproduce the 110 ms that one 3 MB chunk GET took on real S3. The mock does not add TLS or client set-up, so absolute times are lower than on real S3 (orig `window` 811 ms vs 1,516 ms); request counts and bytes are exact, and the comparison between layouts is what this measures. Three records (`160318160317`, `160321120917`, `160324003917`), 3 opens each; all rewrites hold `/das` identical to the original (checked with numpy).

Variants (`h5repack` 2.1.0; recipe in [concept-cloud-optimized-hdf5.md](concept-cloud-optimized-hdf5.md)):

| variant | page size | `/das` chunk | filter | file size (MB) |
|---|---|---|---|---|
| orig | none (`FSM_AGGR`) | 2000 x 384 (3.07 MB) | none | 46.6 |
| paged1m | 1 MiB | 2000 x 384 | none | 49.3 |
| paged | 4 MiB | 2000 x 384 | none | 67.1 |
| paged_fit | 4 MiB | 8192 x 128 (4 MiB) | none | 58.7 |
| paged_bal | 4 MiB | 5000 x 128 (2.56 MB) | none | 79.7 |
| paged_bal_gz | 4 MiB | 5000 x 128 | shuffle + gzip 1 | 58.7 (46.1–67.1) |

ROS3 over the mock (median ms; GETs and MB per open, averaged over the 3 records):

| variant | meta | window | channel | full |
|---|---|---|---|---|
| orig | 724 (3.0 GETs / 16.8 MB) | 811 (4.0 / 19.8) | 1,914 (13.0 / 47.5) | 1,921 (12.7 / 46.5) |
| paged1m | 638 (1.7 / 14.0) | 759 (3.0 / 19.8) | 1,984 (13.0 / 50.6) | 1,980 (13.0 / 52.3) |
| paged | 638 (1.7 / 14.0) | 797 (3.0 / 21.0) | 2,595 (14.0 / 67.1) | 2,592 (14.0 / 68.5) |
| paged_fit | 635 (1.7 / 14.0) | 1,121 (5.0 / 29.4) | **1,123 (5.0 / 29.4)** | 2,258 (12.0 / 60.1) |
| paged_bal | 638 (1.7 / 14.0) | 1,127 (5.0 / 29.4) | 1,448 (7.0 / 37.7) | 3,077 (17.0 / 81.1) |
| paged_bal_gz | 637 (1.7 / 14.0) | 1,129 (4.8 / 28.4) | 1,292 (5.7 / 32.2) | 2,450 (11.9 / 59.7) |

- **Paged aggregation removes the metadata round trip.** Every paged file opens in 635–638 ms against 723 ms (the 168 B GET near the end of the file is gone), so `meta` is 12 % faster and `window` 6 % faster with 1 MiB pages.
- **Page size must fit the chunks.** With 4 MiB pages and 3.07 MB chunks each chunk fills its own page, the file grows 44 % and `full`/`channel` move 67 MB instead of 47 MB (+35 % time). 1 MiB pages cost only 6 % in size.
- **Chunk shape decides the partial reads, and there is no free lunch.** Taller, narrower chunks (8192 x 128) make one channel 41 % faster (1,123 vs 1,914 ms, 29 MB instead of 48 MB) but a 1 s window 38 % slower (1,121 vs 811 ms). The original 2000 x 384 chunks suit time windows, the access the detector uses.
- **gzip with shuffle** makes the file 16–42 % smaller than the same layout uncompressed (79.7 MB), but still larger than the original for 2 of the 3 records (62.9 and 67.1 MB; 46.1 MB for the third). It helps `channel` over the uncompressed balanced layout (1,292 vs 1,448 ms), but costs decompression on every read.
- **For CLIO the layout hardly matters**: it stages whole objects (614–645 ms per object over the mock, whose per-response cap lets the 8 streams reach 8 x 28 MB/s, unlike real S3) and then reads from CTE in 42–71 ms plus 22–62 ms to open and read, except gzip, whose `full` read takes 142 ms instead of 43 ms (decompression).

## Conclusions

1. For one-off partial reads of a record, ROS3 is enough, but set `AWS_EC2_METADATA_DISABLED=true` and expect about 1.4 s per open from Aurora to us-west-2.
2. For repeated or multi-reader access (the agent's detector, notebooks, LLM tools) the CLIO stack wins: one 1.5 s staging, then about 55–85 ms per access, 27–40x faster than ROS3.
3. The cheapest cloud optimization for these files is `h5repack -S PAGE -G 1048576` (consolidated metadata, +6 % size, −12 % open). Re-chunk only for a known access pattern; for channel-wise reads, 8192 x 128 chunks with 4 MiB pages cut a single-channel read by 41 %.

## Bugs and caveats found

- clio-core install: `iowarp-coreConfig.cmake` still has the empty LibPressio flag (see [cae/README.md](../cae/README.md)), and with `CAE_ENABLE_S3` (cfs:: destinations) the installed CAE targets reference `clio::cte::filesystem_client`, which the package config never loads, so `find_package(clio-core)` fails. Worked around in `bench/hdf5_s3/CMakeLists.txt`. Filed as [clio-core #1374](https://github.com/iowarp/clio-core/issues/1374) (LibPressio flag) and [clio-core #1375](https://github.com/iowarp/clio-core/issues/1375) (`filesystem_client`).
- The pip `iowarp_core` 2.2.1 used by clio-agent is built without CAE HDF5, S3 and Globus support.
- aws-c-s3 parses an ETag of the form `"<x>-<n>"` as a multipart ETag; a non-numeric `<n>` made ROS3 hang after its first GET (`s3_mock.py` now sends a plain hex ETag).
- The mock caps speed per response, not overall, so it favours CAE's parallel streams; the real-S3 table is the fair CLIO-vs-ROS3 comparison.

## Related

- [concept-cloud-optimized-hdf5.md](concept-cloud-optimized-hdf5.md)
- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
- [cae_omni_porotomo_dasv.md](cae_omni_porotomo_dasv.md)
- [agent_clio_performance.md](agent_clio_performance.md)
