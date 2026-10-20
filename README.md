# Aortic CFD project

Exploratory blood-flow simulation in a repaired aortic geometry derived from AortaSeg-60 case Anev_01.

## Downloads

- [Complete prepared project — 212 files, ZIP](aortic-cfd-publication-ready.zip): scripts, configuration, repaired segmentation, geometry, validation reports, video and references. Extract the ZIP to preserve the documented directory structure.
- [Simulation video — 1080p MP4](Aortic_Exploratory_SideBySide_1080p.mp4)
- [3D Slicer segmentation — repaired vessel and changes](REPAIRED_AND_CHANGES.seg.nrrd)
- [3D surface — STL, RAS millimetres](REPAIRED_surface_RAS_mm.stl)
- [3D Slicer surface — VTP](REPAIRED_surface_Slicer.vtp)
- [Reproduction instructions](REPRODUCING.md)
- [Data and software references](REFERENCES.md)
- [Dataset attribution and modifications](ATTRIBUTION.md)
- [Original package checksum manifest](PUBLICATION_MANIFEST.json)

## Open the vessel in 3D Slicer

Download the `.seg.nrrd` file using GitHub's raw/download control. In 3D Slicer choose **Add Data**, select it, and load it as a segmentation. Use **Show 3D** in the Segmentations module. For a surface-only view, load the STL or VTP as a model. The original CT is not included in this public package; obtain it from the cited dataset if CT overlay is needed.

## Latest result and interpretation

The solver reached **3.0 simulated seconds** on a **128,472-cell coarse staircase mesh**. Saved-field checks covered 200 states from 1.01 to 3.00 s. Maximum relative flow imbalance was 2.37e-10 and inlet-waveform error 3.28e-8.

**The result remains transient and exploratory.** Phase-resolved wall shear stress changed **8.86%**, exceeding the unchanged **5% periodicity threshold**. Velocity and pressure changes were 4.28% and 3.65%. Solver completion and conservation do not establish mesh convergence, anatomical accuracy or clinical validity. Coarse-mesh WSS is unvalidated.

The 300-frame, 1920 × 1080 video shows saved states once, at 10× slowed playback. It does not replay cycles to imply a longer simulation. The right panel shows unvalidated coarse-mesh WSS.

## Model assumptions

The model uses rigid walls, laminar Newtonian flow, density 1060 kg/m³, dynamic viscosity 0.0035 Pa·s, synthetic 1-second sinusoidal inflow and two independent zero-gauge-pressure outlets. Outlet split is solved, not patient measured. CT orientation was inferred without DICOM orientation metadata. Research repair added 17.26% and removed 3.25% of mask voxels; anatomical correctness is not established.

The authoritative latest report is `runs/runtime_optimization_20261018_01/reports/FINAL_STATUS.json` inside the archive. Earlier runs are retained as development and validation evidence, not as the latest result.

## Reproduction and package scope

Extract the archive before following `REPRODUCING.md`; the loose copies here are convenient downloads. It contains the prepared source, configurations, repaired geometry, compact reports and presentation assets. Original CT, full CFD fields/restart directories, environments, caches and backups are **not included**. Full fields were preserved separately in the owner's project storage at `large_assets/aortic_exploratory_demo_20261018_01`; this repository does not host them. The exact original mask-repair generating script was not retained, so that preprocessing step is not fully reproducible from code.

The uploaded archive is unchanged from the supplied publication package. Its `UPLOAD_STATUS.md` records the earlier connector permission failure and is historical; the archive's internal paths and checksums refer to its extracted contents. The standalone README on this page documents the web publication layout.

## Attribution

Dataset: El Rahal, D., Rotzinger, D. C., and Fahrni, G. (2026), **AortaSeg-60 v1.1**, Lausanne University Hospital and University of Lausanne. [Zenodo record](https://zenodo.org/records/18147026), DOI: 10.5281/zenodo.18147026. The publisher's [dataset README](https://zenodo.org/records/18147026/files/README.md?download=1) states **CC BY 4.0**. Modifications include inferred orientation, research mask repair, generated surfaces and synthetic-boundary-condition CFD visualization. Source authors do not endorse these modifications. Automated source masks are not reference-standard anatomy.

See `REFERENCES.md` and `ATTRIBUTION.md` for software citations, including OpenFOAM, Gmsh (used for candidate meshes, not the final staircase mesh), VTK, ParaView and FFmpeg. Dataset licensing does not automatically license all project code.
