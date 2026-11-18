---
id: porotomo-is.hdf5
section: domain
---
For an `.h5` record: open it read-only with `hdf5_open_file`, then call
`hdf5_analyze_dataset_structure` once; it lists every dataset with shape and dtype,
read from the file, so do not re-check them with `hdf5_get_shape` / `hdf5_get_dtype`.
Use `hdf5_get_chunks`, `hdf5_list_attributes` or `hdf5_read_attribute` only for
details it lacks, sample with `hdf5_read_partial_dataset` (never the whole `/das`),
and close the file.
