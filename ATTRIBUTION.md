# Data attribution and software credits

## Dataset

El Rahal D, Rotzinger DC, Fahrni G. *AortaSeg-60*, version 1.1. Lausanne University Hospital and University of Lausanne, 2026. Zenodo record 18147026, DOI [10.5281/zenodo.18147026](https://doi.org/10.5281/zenodo.18147026). Paper: [AortaSeg-60 preprint](https://www.preprints.org/manuscript/202605.1002).

This project uses case **Anev_01** (CT and its automatic TotalSegmentator mask). The CT itself is not redistributed here; the repository contains derived masks, surfaces, simulation results and a video.

Licence: the record metadata and the preprint state CC0, while the dataset README states CC BY 4.0. We follow the stricter one: the creators are credited here and every modification is listed below. The creators do not endorse this project.

Modifications made in this project:

- inferred CT orientation correction (slice order reversed in the metadata; voxels unchanged)
- automatic research repair of the mask (closing, hole filling, smoothing; 20.5% of voxels changed)
- surfaces derived from the masks, cut and extended for CFD
- CFD simulations with assumed boundary conditions, and their visualisation

The source masks are automatic and not expert-reviewed; nothing here is clinical anatomy or a clinical result.

## Software

- OpenFOAM v1912 (OpenCFD Ltd), build 1912 patch 200626, Ubuntu package: meshing (blockMesh, snappyHexMesh) and solving (pimpleFoam). [Documentation](https://www.openfoam.com/documentation/)
- VTK (Kitware): reading, processing and rendering surfaces and fields. [vtk.org](https://vtk.org/documentation/)
- ParaView (Kitware): inspection of results. [User guide](https://docs.paraview.org/en/v5.12.0/UsersGuide/)
- 3D Slicer: segmentation inspection and editing. [slicer.org](https://slicer.readthedocs.io/en/latest/)
- TotalSegmentator (Wasserthal et al., 2023): automatic segmentation. [GitHub](https://github.com/wasserth/TotalSegmentator)
- NumPy, SciPy, NiBabel; FFmpeg for video encoding.

## Literature

The literature review, with all references, is in [docs/state_of_the_art_and_methodology.md](docs/state_of_the_art_and_methodology.md).
