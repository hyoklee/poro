# Concept: cloud-optimized HDF5

## Definition

An HDF5 file laid out so that a reader on object storage (S3) needs few, large range requests. Each S3 request costs a round trip (tens of ms) and is billed with a 32 KB minimum, so many small reads of scattered metadata hurt more than on a local disk. The usual recipe, from the sources below (read 2026-11-16):

1. **Paged aggregation** (`h5repack -S PAGE -G <bytes>`, or the file-space strategy at creation): metadata and raw data are allocated in fixed-size pages, so the file metadata sits together and a reader gets it in one or two requests. Recommended page sizes range from 4 MiB (Caltech/GHRSST) through 8,000,000 B (NSIDC ICESat-2, `h5repack -S PAGE -G 8000000`) to 16 MiB (NASA).
2. **Chunks of a few MiB** (1–4 MiB in the HDF Group's 2024 talk, "several MiB" in its SC22 slides), shaped for the expected access.
3. **A page buffer at read time** (`H5Pset_page_buffer_size`, h5py `page_buf_size`), a multiple of the page size and at least the total metadata. It works only on paged files and is set when the file is opened, not by h5repack.
4. **Trade-off:** pages are allocated whole, so files grow; paged files cannot be read through the native netCDF library (h5netcdf can).

**HDF5 2.0** rewrote the read-only S3 VFD (ROS3) on AWS's `aws-c-s3`: automatic credential sourcing, parallel splitting of large requests, `s3://` URIs, a 64 MiB default page buffer and an 8 MiB default chunk cache. h5py wheels from PyPI lack ROS3; conda-forge `hdf5` has it.

## Where it appears

- [cae_hdf5_s3_vfd_vs_clio.md](cae_hdf5_s3_vfd_vs_clio.md): measured on three PoroTomo DASV records. With HDF5 2.1.0, ROS3 fetches the first 16 MiB of the file on every open; the original files keep a small piece of metadata near the end (a 168 B GET at offset 46,108,224), which paging removes (open 723 → 635–638 ms over an emulated S3). 1 MiB pages cost 6 % in size; 4 MiB pages around 3 MB chunks cost 44 %. Re-chunking `/das` to 8192 x 128 speeds a one-channel read by 41 % and slows a 1 s window by 38 %.
- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md): the native PoroTomo files are not paged (`H5F_FSPACE_STRATEGY_FSM_AGGR`, 16,968 B of metadata, 3.07 MB chunks).
- [concept-gdr-oedi-hsds.md](concept-gdr-oedi-hsds.md): HSDS is the other route to remote access.

## Sources

- Cloud-Optimized Geospatial Formats Guide, "Cloud-Optimized HDF/NetCDF": https://guide.cloudnativegeo.org/cloud-optimized-netcdf4-hdf5/
- NSIDC, cloud-optimized ICESat-2: https://nsidc.github.io/cloud-optimized-icesat2
- A. Jelenak (HDF Group), "Cloud-optimized HDF5 files – current status" (2024): https://www.slideshare.net/slideshow/cloud-optimized-hdf5-files-current-status/270703576 and the 2025 workshop slides https://hdfdap.hdfgroup.org/workshops/ws25/presentations/axj.pdf
- NASA NTRS 20230016687 (Jelenak slides on optimizing HDF5 for cloud access): https://ntrs.nasa.gov/api/citations/20230016687/downloads/Optimizing_Jelenic.pdf
- HDF Group, HDF5 in the cloud, SC22: https://www.hdfgroup.org/wp-content/uploads/2022/11/HDF5_Cloud_SC22_Robinson.pdf
- Caltech/GHRSST cloud computing slides: https://zenodo.org/records/13141963/files/GHRSST-25_EArmstrong_Recent%20Advances%20of%20Cloud%20Computing.pdf
- HDF Group forum, "HDF5 2.0.0: High-Performance HDF5 Data Access Directly from S3": https://forum.hdfgroup.org/t/hdf5-2-0-0-high-performance-hdf5-data-access-directly-from-s3/13529
- HDF Group blog post cited for the 32 KB per-request billing minimum: https://www.hdfgroup.org/?p=26626
- HDF Group forum, "Retroactive Cloud Optimization Using h5repack": https://forum.hdfgroup.org/t/retroactive-cloud-optimization-using-h5repack/11320

## Related

- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
- [concept-gdr-oedi-hsds.md](concept-gdr-oedi-hsds.md)
- [cae_hdf5_s3_vfd_vs_clio.md](cae_hdf5_s3_vfd_vs_clio.md)
