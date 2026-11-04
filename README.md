# Aortic aneurysm CFD: segmentation, pulsatile flow and wall shear stress

Student project, MSc Advanced Mechatronics, Polytech Annecy-Chambéry (supervisor: Manuel Lagache). Team: Hussein and Marc.

**Question.** How much do the segmentation and surface-smoothing choices used to build an aorta from CT change the time-averaged wall shear stress (TAWSS) that CFD predicts? Low TAWSS (below about 0.4 Pa) has been linked to aneurysm growth and rupture, so a usable predictor must not depend on how the vessel was reconstructed.

**Read first:** [docs/state_of_the_art_and_methodology.md](docs/state_of_the_art_and_methodology.md): literature review (datasets, methods, clinical evidence), data check, pilot results, proposed method and semester plan.

## Status (4 November 2026)

| Part | Status |
| --- | --- |
| Literature review (supervisor's five questions per source) | Done: 8 datasets, 6 methods papers, 5 clinical studies |
| Data check of the pilot case (AortaSeg-60 Anev_01) | Done: CT/mask offset of about 651 mm, duplicate masks (Anev_03 = Anev_05), mask includes thrombus |
| Pilot CFD runs 1 and 2 | Done, exploratory only: pipeline works, results not mesh-converged |
| Corrected CFD setup (`cfd_v2/`) | Written and tested: meshing with wall layers, a short solve, analysis; WSS calculation within 0.6% of the exact pipe solution. Full 6-cycle solves and the mesh study not yet run |
| AI segmentation and lumen/thrombus split (`data_prep/`) | Written and tested on synthetic data; to run on the real CT |
| Mesh-independent baseline and sensitivity study | To do (weeks 5–10 of the plan) |
| Clinical prediction | Out of scope: no outcome data for public cases |

## Pipeline

```
CT (AortaSeg-60) ──► data_prep/check_duplicates.py      remove duplicate cases
                 ──► TotalSegmentator (aorta)            AI segmentation
                 ──► data_prep/lumen_from_ct.py          lumen vs thrombus, then review in 3D Slicer
                 ──► closed lumen surface (STL, RAS mm)
                 ──► cfd_v2/build_case.py                cuts, flow extensions, snapped mesh with layers, BCs
                 ──► cfd_v2/run_case.sh                  mesh, solve (OpenFOAM v1912), wall shear stress
                 ──► cfd_v2/analyze_case.py              TAWSS, OSI, RRT maps and regional means
                 ──► cfd_v2/gci.py                       grid convergence on three meshes
```

Install: `python -m pip install -r requirements.txt`; OpenFOAM v1912 on Ubuntu or WSL: `sudo apt install openfoam`; 3D Slicer and ParaView for viewing. Details: [data_prep/README.md](data_prep/README.md) and [cfd_v2/README.md](cfd_v2/README.md).

## Repository layout

| Folder | Contents |
| --- | --- |
| `docs/` | Report (state of the art and methodology), figures, archived guides of pilot run 2 |
| `data_prep/` | Duplicate check, TotalSegmentator instructions, lumen/thrombus split |
| `cfd_v2/` | Corrected CFD case builder, run script, analysis, GCI |
| `data/repaired/` | Anev_01 masks from pilot run 2: source reference, repaired mask, added/removed regions (`.seg.nrrd` opens in 3D Slicer) |
| `geometry/` | Surfaces from pilot run 2 (RAS mm for Slicer, SI metres for CFD) |
| `reports/` | Orientation and repair audits of pilot run 2 |
| `repro/` | Recovered scripts and rebuild driver of pilot run 2, with tests |
| `runs/runtime_optimization_20261018_01/` | Pilot run 2 status reports and video renderer |
| `video/` | Pilot run 2 video (flow and WSS, 30 s) |
| `tools/` | Backup, Slicer-scene and ParaView-state helpers |

## Pilot runs: what they show

Both runs used rigid walls, Newtonian blood (1060 kg/m³, 0.0035 Pa·s), an invented sine inflow of 50 ± 35 mL/s and zero-pressure outlets.

| | Run 1 (14 Oct) | Run 2 (18 Oct) |
| --- | --- | --- |
| Geometry | Raw AI mask, smoothed 10 iterations | Automatically repaired mask (20.5% of voxels changed) |
| Mesh | 12,318 and 41,540 cells; layers on 1.4% of the wall | 128,472 cells; staircase wall, no snapping, no layers |
| Cycles | 15, periodic | 3, not periodic (WSS change 8.9% between cycles 2 and 3) |
| Lesson | Mean TAWSS agrees between meshes (0.003%) but local maps differ by 54–57% | Staircase wall gives WSS spikes up to 11.8 Pa |
| Files here | Figure in the report; full case files kept by the team, not in this repository | Masks, surfaces, video, reports, scripts; full fields (about 3 GB) kept by the team |

Neither run gives usable WSS values. `cfd_v2/` fixes the causes: wall layers, flow extensions, a measured inflow waveform, a controlled outlet split and a mesh study.

## Data and credits

Data: AortaSeg-60 v1.1 (El Rahal, Rotzinger, Fahrni; Lausanne University Hospital), DOI [10.5281/zenodo.18147026](https://doi.org/10.5281/zenodo.18147026). The CT is not redistributed; derived masks, surfaces and results are. See [ATTRIBUTION.md](ATTRIBUTION.md) for the licence note, the list of modifications and software credits. Nothing in this repository is a clinical result.

No licence has been chosen yet for the project code.
