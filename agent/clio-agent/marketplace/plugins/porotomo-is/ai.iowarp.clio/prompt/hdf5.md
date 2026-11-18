---
id: porotomo-is.hdf5
section: domain
---
For what an `.h5` record contains (datasets, shapes, dtypes, chunks, attributes),
call `porotomo_h5_layout` once with the file path. For data values, call
`porotomo_h5_slice` once (`start` and `count` per dimension, e.g. "0,200" and
"100,1"); it returns the slice's min, max, mean, std and its first `show` values.
Both read the file and are authoritative: answer from them directly, without
`hdf5_*`, shell or `run_code` re-checks. Never read the whole `/das`.
