# Concept: GDR, OEDI and HSDS

## Geothermal Data Repository (GDR)

The US Department of Energy's archive for geothermal research data, run by NREL for the Geothermal Technologies Office at https://gdr.openei.org. Projects funded by the office must deposit their data there. Each deposit is a numbered submission with a DOI, authors, keywords, license and a resource list; related datasets from one project get separate submissions (980 holds PoroTomo DAS data; 825 and 829 hold its metadata and deployment history). GDR is part of OpenEI, NREL's open energy information platform.

## Open Energy Data Initiative (OEDI)

Large GDR datasets are pushed to public AWS S3 buckets under OEDI; PoroTomo lives in `s3://nrel-pds-porotomo/` ([source-s3-nrel-pds-porotomo.md](source-s3-nrel-pds-porotomo.md)) and is listed in the Registry of Open Data on AWS. Objects are readable anonymously over HTTPS.

## Highly Scalable Data Service (HSDS)

NREL's HSDS serves HDF5 content over HTTP so h5pyd clients can read slices without downloading whole files. For PoroTomo the HSDS copies are daily files rather than 30 s files, which sidesteps the per-object overhead of millions of small files.

## Related

- [source-gdr-submission-980.md](source-gdr-submission-980.md)
- [concept-das-hdf5-layouts.md](concept-das-hdf5-layouts.md)
