# cae/ — clio-core CAE experiments on PoroTomo

Code and configuration for running IOWarp's Context Assimilation Engine (CAE)
over PoroTomo HDF5 records. The results are written up in
[wiki/cae_omni_porotomo_dasv.md](../wiki/cae_omni_porotomo_dasv.md).

- `porotomo/` — the OMNI files (`porotomo_dasv_omni.yaml`, Windows copy
  `porotomo_dasv_omni_win.yaml`), single-node runtime configs
  (`clio_porotomo_config*.yaml`, port 10600, RAM tier), the S3 download
  script, and the drivers: `run_porotomo.sh` (Linux: `clio_run` + `clio_cae`
  + the h5py verifier `verify_porotomo.py`) and `run_porotomo_win.bat`
  (Windows: the C++ driver below).
- `omni_roundtrip/` — `test_omni_hdf5_roundtrip.cc`, a standalone C++ driver
  that loads any OMNI file (`CAE_OMNI_FILE`), submits it through `ParseOmni`
  on an in-process runtime, and verifies every `format: hdf5` transfer
  byte-for-byte against the source file: selected datasets must land as a
  `description` blob plus `chunk_N` blobs equal to the dataset bytes, rejected
  ones must hold nothing. Portable (no fnmatch, no Python), so it is the
  verifier on Windows.

## Building the driver

The driver builds against an installed clio-core (built with
`-DCLIO_CORE_ENABLE_HDF5=ON`) through `find_package(clio-core)`:

```bash
cmake -S cae/omni_roundtrip -B cae/omni_roundtrip/build \
      -DCMAKE_PREFIX_PATH=<clio-core install prefix>
cmake --build cae/omni_roundtrip/build
```

On Windows add the vcpkg toolchain file used for the clio-core build (HDF5 and
yaml-cpp come from it) and pass `-DCMAKE_BUILD_TYPE=Release` with Ninja.

## Running

Linux (runtime + CLI + Python verifier):

```bash
cae/porotomo/download_porotomo.sh ~/cae_test_data/porotomo
CLIO_BIN=~/clio-core/build/bin cae/porotomo/run_porotomo.sh cae/porotomo/porotomo_dasv_omni.yaml
```

Windows (in-process runtime inside the driver):

```bat
cae\porotomo\run_porotomo_win.bat C:\src\core\build-icx
```

Either way the OMNI's `src:` paths must point at the downloaded files; edit
them for your machine.

## Known clio-core install issues (as of dev 2026-11-11, PR head 34a7d8fb)

- `find_package(clio-core)` fails on any clio-core installed with compression
  off: `cmake/ClioCoreConfig.cmake.in` expands `@CLIO_CTP_ENABLE_LIBPRESSIO@`,
  which the root CMakeLists only sets inside the `CLIO_CORE_ENABLE_COMPRESS`
  block, so the installed `iowarp-coreConfig.cmake` reads
  `if( AND NOT TARGET LibPressio::libpressio ...)`. Workaround used here: edit
  that line in the install to `if(OFF AND ...)`.
- A Windows (icx-cl, Ninja) `cmake --install` lands the libraries, DLLs and
  headers but none of the runtime's package files (`lib/cmake/clio_run`,
  `clio_run_admin`, `clio_run_bdev`), so the driver cannot be configured
  against a Windows install yet. On Windows the round trip was run with the
  driver built inside the clio-core tree instead (see the wiki page).

## History

Until 2026-11-11 these files were part of clio-core PR
[hyoklee/core#6](https://github.com/hyoklee/core/pull/6) under
`context-assimilation-engine/test/integration/porotomo/` and
`test/unit/omni_roundtrip/`. The PR was then cut down to the Windows
portability fix in the HDF5 assimilator plus a self-contained
`cae_hdf5_dataset_filter` test, and the PoroTomo material moved here.
