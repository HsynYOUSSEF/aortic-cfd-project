# References, software credits and data attribution

## Dataset

El Rahal, D., Rotzinger, D. C., & Fahrni, G. (2026). *AortaSeg-60*, version 1.1. Lausanne University Hospital and University of Lausanne. Zenodo record 18147026. DOI: [10.5281/zenodo.18147026](https://doi.org/10.5281/zenodo.18147026). The project used the Anev_01 CT and its supplied AI mask; attribution and source hashes are in `ATTRIBUTION.md`.

The publisher’s README states CC BY 4.0. Attribute the dataset creators and disclose the research modifications. No authorship of the source CT or supplied mask is claimed.

## Software used

- OpenCFD Ltd. *OpenFOAM v1912*, build `OPENFOAM=1912 patch=200626` as recorded in the solver logs. [Official v1912 distribution and guides](https://dl.openfoam.com/source/v1912/).
- Kitware. *Visualization Toolkit (VTK)* documentation and API reference: [vtk.org/documentation](https://vtk.org/documentation/). VTK was used to read, inspect, compare and render saved mesh/field data.
- Kitware. *ParaView User’s Guide*, [official documentation](https://docs.paraview.org/en/v5.12.0/UsersGuide/). ParaView/VTK readers were used for output inspection and the case provides `.foam`/PVD views.
- FFmpeg developers. *FFmpeg documentation*, [ffmpeg](https://ffmpeg.org/ffmpeg.html), [filters](https://ffmpeg.org/ffmpeg-filters.html), and [ffprobe](https://ffmpeg.org/ffprobe.html). FFmpeg encoded and fully decoded the delivered MP4.

## Project assumptions are not external references

The rigid wall, Newtonian viscosity/density, synthetic inflow, zero-pressure outlets, CT orientation inference, repair operations, mesh choices, validation thresholds and all numerical results are project assumptions or measurements. They should not be described as established patient-specific clinical parameters. No external clinical CFD study was used as a validation reference.


## Public distribution update — 21 October 2026

The dataset publisher's live README explicitly states CC BY 4.0: https://zenodo.org/records/18147026/files/README.md?download=1 . This publication follows that stated attribution license: https://creativecommons.org/licenses/by/4.0/ . The older CC0 metadata discrepancy is retained as historical provenance, rather than a replacement for the publisher's stated terms. Credit: Dania El Rahal, David C. Rotzinger, Guillaume Fahrni; Lausanne University Hospital and University of Lausanne; AortaSeg-60 v1.1, case Anev_01; DOI https://doi.org/10.5281/zenodo.18147026 .

Project modifications comprise inferred orientation correction, research mask repair, derived surfaces, synthetic-boundary-condition CFD and visualization. The source authors do not endorse this project. Source segmentation is automated and not reference-standard anatomy. Third-party dataset attribution and license remain applicable; no blanket project-code license is assigned.
- 3D Slicer: https://slicer.readthedocs.io/en/latest/ — segmentation inspection and scene saving.
