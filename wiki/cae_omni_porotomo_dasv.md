# CAE: selective ingestion of one PoroTomo DASV record through an OMNI file

Reference workload for IOWarp clio-core's Context Assimilation Engine (CAE). Files live in clio-core at `context-assimilation-engine/test/integration/porotomo/` (PR [hyoklee/core#6](https://github.com/hyoklee/core/pull/6), commit `c65ca27c`).

## OMNI

Two `format: hdf5` transfers over [source-dasv-PoroTomo_iDAS025_160318160317.md](source-dasv-PoroTomo_iDAS025_160318160317.md):

1. Native file → tag prefix `porotomo_dasv`, `include_patterns: [/das, /t, /z]`, `exclude_patterns: [/crs, /channel, /trace]` — only what a strain-rate waterfall plot needs.
2. Standardized file → tag prefix `porotomo_dasv_std`, `include_patterns: [/DasRawData/*]`.

Each selected dataset becomes a CTE tag `<prefix>/<dataset>` holding a `description` blob (`tensor<dtype, dims...>`) and `chunk_N` blobs of 1,572,864 bytes (1.5 MB), e.g. 30 chunks for the 46,080,000-byte `/das`.

## Runs

| Date | Platform | Compiler / build | Driver | Result |
|---|---|---|---|---|
| 2026-11-10 | WSL Ubuntu-26.04, clio-core main `f0d75829` | gcc, Ninja Release, HDF5 from micromamba | `clio_run start` + `clio_cae` + Python/h5py verifier | PASS: 3/8 native datasets ingested byte-exact, 5 excluded hold 0 blobs; 2/2 standardized byte-exact. `clio_cae` scheduling call 161–223 ms; 46 MB readback ~60 ms |
| 2026-11-10 | same | same | `cae_omni_hdf5_roundtrip` (in-process runtime) | PASS, identical findings; `ParseOmni` 214 ms |
| 2026-11-11 | Windows 11, clio-core `c65ca27c` | oneAPI icx-cl 2026.1, Ninja Release, vcpkg HDF5 2.2.0, `CLIO_CORE_ENABLE_HDF5=ON` | `cae_omni_hdf5_roundtrip` | PASS, identical findings; `ParseOmni` 130 ms; 46 MB readback 47 ms |
| 2026-11-11 | same | same | `clio_run.exe start` + `clio_cae.exe` + `cte_search.exe` | 5 tags present with `description`/`chunk_*` blobs only for selected datasets |

In single-node mode the data is fully in CTE by the time `ParseOmni` returns, even though the CLI reports assimilation as asynchronous.

## Bugs found

- **`depends_on` silently skips HDF5 transfers.** `Hdf5FileAssimilator::Schedule` returns success without ingesting when `depends_on` is non-empty (a TODO branch), and `ParseOmni` still reports the transfer as scheduled. Workaround: leave `depends_on` empty. Not fixed as of 2026-11-11.
- **Unsigned integers mislabeled.** `GetTypeName` ignores signedness, so the uint64 `/DasRawData/DasTimeArray` is described as `tensor<int64, 30000>`; 1- and 2-byte integers become `unknown`. Not fixed.
- **Not portable to Windows (fixed in PR #6).** The assimilator called `fnmatch()` and `stat()` while guarding their headers out on `_WIN32`; replaced with `std::filesystem::file_size` and a portable glob matcher on Windows. This was the first time the CAE HDF5 path was compiled or run on Windows; CI's Windows jobs leave HDF5 off.

## Reproduce

Linux: `download_porotomo.sh`, then `run_porotomo.sh porotomo_dasv_omni.yaml`. Windows: build with the `icx` recipe from `.github/workflows/ci-windows.yml` plus `-DCLIO_CORE_ENABLE_HDF5=ON`, then `run_porotomo_win.bat <build_dir>`. Either way the `cae_omni_hdf5_roundtrip` test takes the OMNI path in `CAE_OMNI_FILE`.

## Related

- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
- [source-s3-nrel-pds-porotomo.md](source-s3-nrel-pds-porotomo.md)
