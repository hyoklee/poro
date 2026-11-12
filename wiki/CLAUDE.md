# PoroTomo DAS Wiki — Schema

This wiki documents the PoroTomo distributed acoustic sensing (DAS) dataset (GDR submission 980) and its use with IOWarp's Context Assimilation Engine (CAE). The LLM maintains all files under `wiki/`. Raw sources are the public OEDI S3 objects (`s3://nrel-pds-porotomo/`), the GDR submission pages, and the papers linked from them; they are never modified. Downloaded HDF5 files are cached under `~/cae_test_data/porotomo/` and are not committed.

## Directory layout

```
wiki/
  CLAUDE.md              ← this file (schema)
  index.md               ← catalog of all wiki pages
  log.md                 ← append-only event log
  overview.md            ← high-level synthesis
  source-*.md            ← one page per raw source (GDR submission, S3 prefix, HDF5 file, paper)
  concept-*.md           ← reusable concept / entity pages
  cae_*.md               ← CAE / OMNI ingestion experiments and their results
```

## Page conventions

- GitHub-flavored markdown. Links between pages use `[text](file.md)`.
- Every `source-*.md` page for an HDF5 file lists: S3 key, size, root attributes of note, every dataset with dtype / shape / chunking / bytes, and which GDR layout it uses (native DAS-HDF5-1.0 or GDR "standardized").
- Every `concept-*.md` page lists: definition, where it appears (which sources), related concepts.
- Every `cae_*.md` page lists: platform and compiler, clio-core commit, OMNI file used, what was verified and how, timings in milliseconds, and any bugs found.
- Numbers come from the source or from a run recorded in `log.md`; never from memory.

## Workflows

### Ingest an HDF5 record
1. Fetch the object from S3 (`cae/porotomo/download_porotomo.sh` style curl; no credentials needed).
2. Inspect it with h5py (or h5dump) and write `source-<name>.md`.
3. Update `index.md`; update or create `concept-*.md` pages it touches.
4. Append an entry to `log.md`.

### Run a CAE ingestion test
1. Write or reuse an OMNI file with a `dataset_filter` that selects only what the analysis needs.
2. Run it through `clio_cae` + `cae/porotomo/verify_porotomo.py` (Linux) or the `cae/omni_roundtrip` driver (any platform) and verify byte-for-byte.
3. File the result as `cae_<topic>.md`; log it.

### Answer a query
1. Read `index.md` to find relevant pages, then read them.
2. Synthesise an answer with page citations.
3. If valuable, file it as a new page or append to an existing one; log the query.

### Lint
- Orphan pages (no inbound links), stale claims superseded by newer runs, contradictions between pages, concepts mentioned but lacking a page.

## Log entry format

`## [YYYY-MM-DD] <kind> | <title>` where kind is one of `bootstrap`, `ingest`, `query`, `test`, `lint`.
