---
id: porotomo-is.hdf5
section: domain
---
For what an `.h5` record contains (datasets, shapes, dtypes, chunks, attributes),
call `porotomo_h5_layout` once with the file path. It reads every dataset and
attribute from the file, so it is authoritative: answer from it directly, with no
`hdf5_*` re-checks. Use the `hdf5_*` tools only for data values: open the file,
sample with `hdf5_read_partial_dataset` (never the whole `/das`), and close it.
