# Concept: poroelastic tomography

## Definition

An inversion that recovers subsurface hydraulic and elastic properties from how the ground strains when pore pressure is perturbed. The forcing is the pumping schedule: pressure diffuses from the injection well, the rock around it deforms, and sensors (DAS fiber, seismometers, InSAR) record the strain. Active seismic sources add velocity information so elastic structure can be separated from fluid pressure. The result is a 3D block model (cells of tens of metres) with per-cell values such as hydraulic diffusivity or permeability and P/S-wave velocity.

## What the output looks like

A gridded cross-section or volume coloured by the inverted property, with wells and mapped faults overlaid. At Brady, published results show high-permeability zones aligned with mapped faults and a strong velocity contrast in the shallow hydrothermally altered layer.

## Inputs from this dataset

- DASH and DASV strain-rate records (this wiki's sources) during pumping stages and vibroseis sweeps.
- Not in submission 980: the pumping schedule, nodal seismometer data and InSAR, which live in sibling GDR submissions.

## Why it matters beyond geothermal

The same pressure-diffusion physics drives induced seismicity from fluid injection ([concept-induced-seismicity-pohang.md](concept-induced-seismicity-pohang.md)), CO2 storage leakage risk, and land subsidence from aquifer pumping.

## Related

- [concept-porotomo-project.md](concept-porotomo-project.md)
- [concept-das.md](concept-das.md)
