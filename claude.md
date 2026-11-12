This repository is an LLM wiki (see llm-wiki.md) for the PoroTomo distributed acoustic sensing (DAS) dataset,
Geothermal Data Repository submission 980 (DOI 10.15121/1778858, CC BY 4.0).
Raw sources are the public OEDI S3 objects under s3://nrel-pds-porotomo/ (DAS/H5, DAS/H5-standardized, DAS/SEG-Y, Nodal)
and the GDR submission pages; they are never modified. Cache downloaded files under ~/cae_test_data/porotomo/.
The wiki is maintained under wiki/ following wiki/CLAUDE.md.
Goals: document the dataset's structure, the science it supports (poroelastic tomography at Brady Hot Springs),
and how IOWarp's Context Assimilation Engine (clio-core CAE) ingests it selectively through OMNI files.
When testing clio-core, use the OMNI, configs and drivers under cae/ (see cae/README.md).
Record every ingest, query, and test run in wiki/log.md and keep wiki/index.md current.
