# Aortic CFD — latest 3-second exploratory run

Blood-flow visualization in a repaired AortaSeg-60 Anev_01 vessel, with synthetic pulsatile inflow and two zero-pressure outlets.

## Start here

- [Step-by-step guide](PROJECT_GUIDE.md): data, reconstruction, CFD, Slicer, ParaView and video.
- [Latest compact package](aortic-cfd-publication-ready.zip): latest presentation assets, geometry, selected evidence and helper scripts. Extract before use.
- [What is included and what is still missing](COMPLETION_STATUS.md).
- [1080p simulation video](Aortic_Exploratory_SideBySide_1080p.mp4).
- [Slicer segmentation](REPAIRED_AND_CHANGES.seg.nrrd), [Slicer surface](REPAIRED_surface_Slicer.vtp), [STL](REPAIRED_surface_RAS_mm.stl).
- [Latest validation summary](LATEST_VALIDATION.json), [checksums](PUBLICATION_MANIFEST.json), [references](REFERENCES.md), [attribution](ATTRIBUTION.md).

## Latest result

The solver reached 3.0 s on 128,472 cells. Saved-field checks covered 200 states from 1.01 to 3.0 s. Maximum relative flow imbalance was 2.37e-10; inlet waveform error was 3.28e-8. Phase-resolved WSS change was **8.86%, exceeding the 5% periodicity threshold**. The result remains **exploratory and transient**; anatomical and mesh accuracy are not established.

The movie shows 300 saved states at 1920×1080, approximately 29.91 seconds, with 10× slowed playback and no cycle replay. The right panel shows unvalidated coarse-mesh WSS.

## Assumptions

Rigid walls; laminar Newtonian flow; density 1060 kg/m³; dynamic viscosity 0.0035 Pa·s; synthetic Q(t)=5e-5+3.5e-5 sin(2πt) m³/s. Both outlets use zero kinematic gauge pressure. These are research assumptions, not patient measurements. CT orientation is inferred, and mask repair modifies anatomy. The exact mask-repair generating program was not retained.

## Reproduction and preservation

The full mesh, solver fields/checkpoints, exact run controller/analysis modules and original/corrected CT are **not in this compact package**. Their separate transfer is still required. Scene-generation scripts are included, but a finished `.mrb` or `.pvsm` has not been generated and tested here. This repository is not yet a complete backup; retain the laptop project.

## Attribution

El Rahal, D., Rotzinger, D. C., and Fahrni, G. (2026), AortaSeg-60 v1.1, Lausanne University Hospital and University of Lausanne. DOI: [10.5281/zenodo.18147026](https://doi.org/10.5281/zenodo.18147026). The publisher's README states CC BY 4.0. Modifications include inferred orientation correction, research mask repair, derived surfaces and synthetic-boundary-condition CFD visualization. Source authors do not endorse the modifications; automated masks are not reference-standard anatomy. See REFERENCES.md and ATTRIBUTION.md.
