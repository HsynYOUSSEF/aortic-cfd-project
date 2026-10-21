# Rebuild files from the supplied inputs

## What this workflow does

The expanded ZIP includes recovered case-preparation and analysis source, the source-reference and repaired masks, a repaired RAS surface, and a new portable driver. You can prepare a fresh OpenFOAM case without the laptop's saved flow fields. Those fields must then be calculated by running OpenFOAM locally.

This is a **new reconstruction of the workflow**, not an exact replay of the published 3-second run. The historical controller, complete solver dictionaries/checkpoints and exact repair generator have not been recovered. The documented driver uses the supplied repaired geometry; it does not silently replace it with a newly repaired mask. A matching cell count or matching WSS is not guaranteed.

## 1. Download and install dependencies

Download `aortic-cfd-publication-ready.zip` from this repository and extract it into a new folder. Run the following commands from the extracted package root in Ubuntu/WSL. Use a native Linux run directory rather than a Windows-mounted directory for the solver.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r repro/requirements.txt
python repro/tools/test_reconstruction.py
```

The pinned Python packages record the preprocessing test environment, not the historical solver environment. Python 3.11 or newer is required by these package versions. Use the environment version in `repro/verification/TEST_STATUS.json` if matching the preprocessing test exactly.

Install FFmpeg, FFprobe and DejaVu Sans for video rendering using your Ubuntu package manager. Install a compatible OpenCFD OpenFOAM build using the [official installation instructions](https://www.openfoam.com/download/openfoam-installation-on-linux). The recorded demonstration used v1912 patch 200626; the reconstructed driver has not been solver-tested against another version. Foundation and OpenCFD release numbers are not interchangeable. Source your installation's `etc/bashrc`, then verify:

```bash
command -v blockMesh snappyHexMesh checkMesh pimpleFoam ffmpeg ffprobe
foamVersion
```

Do not interpret a missing command as a passed stage. Keep the OpenFOAM version, system details and logs with your run. More installation and viewing details are in `PROJECT_GUIDE.md`.

## 2. Prepare a fresh case

```bash
RUN="$HOME/aortic-runs/my_run_01"
python repro/tools/rebuild.py prepare "$RUN"
```

The output directory must not already exist. The driver copies the necessary input files and recovered scripts, adapts their paths and writes a case at `$RUN/cfd/aorta`. It records file hashes and package versions in `$RUN/reports/preparation.json`.

The included repaired surface is clipped at RAS z = -420 and -240 mm, converted to metres and divided into a wall, one inlet and two outlets. The source mask determines an interior meshing seed. Preparation refuses missing/degenerate cap regions or an open/nonmanifold surface.

The proposed mesh uses a 2 mm background with level-one surface/interior refinement (nominal 1 mm), no snapping and no prism layers. This staircase boundary is exploratory and unsuitable for claiming mesh-independent WSS without further study. Boundary assumptions are rigid walls, Newtonian viscosity 0.0035 Pa·s, density 1060 kg/m³, sinusoidal inflow `5e-5 + 3.5e-5*sin(2*pi*t)` m³/s and two zero kinematic-gauge-pressure outlets. The inflow is synthetic, not a patient measurement.

## 3. Mesh, solve and calculate WSS

```bash
python repro/tools/rebuild.py mesh "$RUN"
python repro/tools/rebuild.py solve "$RUN"
```

Meshing runs `blockMesh`, `snappyHexMesh -overwrite`, and `checkMesh -allTopology -allGeometry`. A gate requires `Mesh OK.`, all four nonempty vessel patches and no retained outer-box faces. A pre-existing mesh is preserved and rejected for remeshing.

The solve stage requires that gate to pass. It runs `pimpleFoam` to 3 seconds with outputs every 0.01 s, no output purging, adaptive time stepping, maximum Courant number 0.7 and maximum timestep 0.0002 s. The inherited dictionaries use two outer PIMPLE correctors; this is a stated reconstruction choice, not a recovered final-controller setting. After solving, it uses `pimpleFoam -postProcess -func wallShearStress -time 0.01:3`.

This may require hours and several GB. Check available disk space first. Failed commands stop the driver and retain logs under `$RUN/logs`. The driver refuses to overwrite an attempted solve. Diagnose the log and prepare another run directory; do not delete existing results to make a command pass.

## 4. Analyze and check periodicity

```bash
python repro/tools/rebuild.py analyze "$RUN"
```

The recovered analyzer exports wall fields, TAWSS, OSI, RRT and conservation summaries into `$RUN/results/aorta`. It verifies kinematic WSS dimensions and multiplies WSS by density exactly once to obtain Pa. Its TAWSS cycle statistic is **not** a phase-resolved periodicity test.

The new `check_periodicity.py` separately compares 100 matching phases from 1.01–2.0 s and 2.01–3.0 s, using volume-weighted U/p and area-weighted WSS relative L2 changes. It writes `phase_periodicity.json`. All three must be below the unchanged 5% threshold for its PASS status. A computed report is not necessarily a passing report. Review conservation, inlet error, finite fields and periodicity before interpretation. Neither numerical periodicity nor `Mesh OK.` demonstrates anatomical or mesh accuracy.

These analysis stages have not been executed on a new solved case in the hosted environment. They may require compatibility fixes for a different OpenFOAM build. Preserve their errors rather than modifying thresholds to obtain a pass.

## 5. Recreate the video

```bash
python repro/tools/rebuild.py video "$RUN"
```

The driver installs a path-adapted copy of the retained renderer. It requires all 300 U/WSS snapshots from 0.01 to 3.0 s, reads the actual fields, applies the WSS density conversion once, and writes `$RUN/video/Aortic_Exploratory_SideBySide_1080p.mp4`. It verifies frame count, 1080p resolution and a full FFmpeg decode. This new movie reflects the new run; it is not expected to be byte-identical to the supplied demonstration.

## 6. Recreate a ParaView state

```bash
pvpython tools/create_paraview_state.py "$RUN/cfd/aorta" "$RUN/latest_flow.pvsm"
```

`pvpython` comes with ParaView and may need its absolute executable path. The helper creates a basic velocity view. Open the state in ParaView, add slices/streamlines and wall stress using `PROJECT_GUIDE.md`, save it, close it, and reopen it to verify data paths. A `.pvsm` references external case data; it does not embed the flow fields. Share the case too, or share this regeneration workflow with its compatibility limitations.

## 7. Recreate a Slicer scene

In a fresh 3D Slicer session, open the Python console and use Windows paths to the extracted package:

```python
exec(open(r'C:/path/to/package/tools/create_slicer_scene.py').read())
create_scene(r'C:/path/to/package', r'C:/path/to/new/latest_geometry.mrb')
```

This bundles the included segmentation as a geometry scene. CT is optional and is not in the package. To include an independently checked aligned CT, pass `corrected_ct=r'C:/path/to/aligned_CT.nii.gz'`. The helper does not align CT, infer patient orientation or regenerate a CT volume. Reopen the `.mrb` and visually inspect it. Slicer and ParaView helpers have not been application-tested here.

## 8. Run the new mask-reconstruction baseline separately

```bash
python repro/tools/reconstruct_mask.py \
  data/repaired/ORIGINAL_GREEN_REFERENCE.nrrd \
  "$HOME/aortic-runs/repair_baseline_01" \
  --reference data/repaired/GREEN_REPAIRED_RESEARCH.nrrd
```

This new algorithm fills enclosed axial holes, smooths a signed-distance field with a 0.65 mm Gaussian, restores slices if major source components merge or lose more than 20% of their voxels, and retains the largest 3D component. A final report checks the component-retention condition after that last operation. Coordinates and voxel spacing are preserved. The output folder must be new.

Outputs are `RECONSTRUCTED_BASELINE.nrrd`, `RECONSTRUCTED_BASELINE_RAS_mm.vtp` and `repair_report.json`. Inspect them against the source segmentation and CT in Slicer. If `component_retention_gate` is false or topology is unsuitable, do not use the candidate for CFD. Passing these limited checks is not anatomical validation.

The executed baseline has one 3D component, no detected boundary/nonmanifold surface edges and passed the component-retention gate. Its Dice overlap with the published repaired mask is approximately 0.9338; **the masks are not identical**. It does not recreate the original repair, automatic CT segmentation, inferred CT alignment or the original movie's exact geometry. The CFD driver intentionally continues using the supplied published geometry. Using the new candidate for CFD requires reviewing it, exporting it to the case's expected coordinates and repeating all preparation/mesh/flow checks in a separate case.

## Verification and provenance

- `repro/recovered/`: byte-preserved source recovered from the original uploaded archive.
- `repro/tools/`: new driver, repair baseline, phase checker and tests.
- `repro/verification/source_recovery.json`: recovered source hashes.
- `repro/verification/case_preparation.json`: executed geometry-preparation evidence.
- `repro/verification/repair_report.json`: executed replacement-repair evidence.
- `repro/verification/TEST_STATUS.json`: what was tested and what was not.

The two synthetic geometry tests and real-input preprocessing passed. OpenFOAM meshing/solving, analysis on new solved fields, new video generation and GUI scene creation remain untested here. Complete local end-to-end verification before calling this workflow fully reproducible. Retain the original laptop project until an independent backup has been verified.

References: [SciPy binary morphology](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_closing.html), [SciPy physical distance transforms](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.ndimage.distance_transform_edt.html), [OpenCFD WSS function](https://doc.openfoam.com/2312/tools/post-processing/function-objects/field/wallShearStress/), plus `REFERENCES.md` and the unchanged dataset attribution.
