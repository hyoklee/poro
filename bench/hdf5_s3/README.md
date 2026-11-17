# bench/hdf5_s3: HDF5 S3 VFD vs the CLIO stack, and cloud-optimized layouts

Results and interpretation: [wiki/cae_hdf5_s3_vfd_vs_clio.md](../../wiki/cae_hdf5_s3_vfd_vs_clio.md).

| File | Role |
|---|---|
| `ros3_bench.c` | HDF5 read through the read-only S3 VFD (ROS3, HDF5 >= 2.0); patterns `meta`, `full`, `window`, `channel`, fresh open per rep |
| `clio_s3_bench.cc` | CLIO path: CAE `S3FileAssimilator` stages the object into a CTE tag, chunk blobs are read back, HDF5 opens the bytes as a file image (core driver), same four patterns |
| `run_clio.sh` | starts a single-node runtime (`clio_s3bench_config.yaml`, port 10700), runs `clio_s3_bench`, stops it |
| `run_real_s3.sh` | real-S3 comparison on one public NREL record: curl baselines, ROS3, CLIO |
| `s3_mock.py` | stdlib S3-compatible server (HEAD + ranged GET, anonymous, path-style) with per-request delay and per-response MB/s cap; logs every request |
| `run_layouts.py` | every record x layout variant through `s3_mock.py`, ROS3 and CLIO |
| `files/` (not committed) | the three sample records and their `h5repack` rewrites |
| `results/` | raw outputs of each run |

## Build

Needs HDF5 2.x with ROS3 (conda-forge `hdf5`; the `iowarp` conda env here has
2.1.0) and, for `clio_s3_bench`, clio-core installed with
`-DCLIO_CORE_ENABLE_CAE=ON -DCLIO_CORE_ENABLE_HDF5=ON -DCAE_ENABLE_S3=ON`
(needs Poco and `aws-sdk-cpp`).

```bash
E=~/miniconda3/envs/iowarp
cmake -S . -B build -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx \
  -DCMAKE_PREFIX_PATH="$HOME/clio-core.dev.wrk/install_s3;$E" -DHDF5_DIR=$E/cmake
make -C build
```

Two install bugs needed workarounds: the installed `iowarp-coreConfig.cmake`
has `if( AND NOT TARGET LibPressio::libpressio ...)` (edit to `if(OFF AND ...)`),
and with `cfs::` destinations on, the CAE targets reference
`clio::cte::filesystem_client` that the package never loads (`CMakeLists.txt`
declares an empty stand-in).

## Layout variants (`files/<record>_<variant>.h5`)

```bash
h5repack -S PAGE -G 1048576                                   orig.h5 paged1m.h5
h5repack -S PAGE -G 4194304                                   orig.h5 paged.h5
h5repack -S PAGE -G 4194304 -l /das:CHUNK=8192x128            orig.h5 paged_fit.h5
h5repack -S PAGE -G 4194304 -l /das:CHUNK=5000x128            orig.h5 paged_bal.h5
h5repack -S PAGE -G 4194304 -l /das:CHUNK=5000x128 -f /das:SHUF -f /das:GZIP=1 orig.h5 paged_bal_gz.h5
```

## Run

```bash
export AWS_EC2_METADATA_DISABLED=true   # else ROS3 waits ~4 s probing EC2 instance metadata
./run_real_s3.sh
~/.local/share/clio/clio-agent/.venv/bin/python run_layouts.py --delay-ms 10 --mbps 28 --reps 3 --clio \
    --out results/layouts_$(date -u +%Y%m%dT%H%M%SZ)
```
