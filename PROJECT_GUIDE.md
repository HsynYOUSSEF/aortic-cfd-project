# Complete project guide: data, CFD, 3D Slicer, ParaView and video

This guide describes the recorded project and practical ways to use its outputs. Commands labelled **conditional** require the separately preserved full case. Commands labelled **new reconstruction** create a new experiment; they do not certify reproduction of the published result. This documentation update does not rerun the solver.

## 1. Start here: choose the task

| Goal | Required files | Possible with the public ZIP alone? |
|---|---|---|
| Watch the simulation | MP4 | Yes |
| Inspect the repaired vessel and edit a copy | `.seg.nrrd`, Slicer VTP or STL | Yes |
| Read source, settings and validation evidence | Extracted ZIP | Yes |
| Inspect geometry in ParaView | Geometry VTP/STL | Yes, geometry only |
| Animate actual velocity, pressure or WSS in ParaView | Full case with mesh and saved fields, or complete PVD/VTP series | No |
| Regenerate the exact side-by-side movie | 300 saved states with U and wallShearStress, analysis module, renderer | No |
| Repeat the recorded CFD | Full case, initial fields, dictionaries, compatible software | No |
| Rebuild the original repaired mask bit for bit | Exact original repair program and inputs | Not currently possible: program not retained |

**Latest result:** 3.0 s on a 128,472-cell coarse mesh. Phase-resolved WSS cycle difference was 8.86%, above the unchanged 5% criterion. This is a transient exploratory calculation, not a validated clinical prediction. “Mesh OK” and a playable movie do not mean accurate WSS.

## 2. Download and organize the files

1. Open this repository and download `aortic-cfd-publication-ready.zip` using **Download raw file**. Downloading the entire repository gives an outer ZIP that still contains this project ZIP; extract both levels.
2. Extract the project ZIP into a new folder, for example `C:\dev\aortic_project_public`. Keep the original ZIP unchanged.
3. The extracted folder should contain `src`, `runs`, `reports`, `data`, `geometry`, `deliverables`, `REPRODUCING.md` and `PUBLICATION_MANIFEST.json`.
4. Read this guide from the repository. The ZIP is a frozen historical package: its upload status predates successful publication and its older launcher is not the latest run procedure.
5. Put experiments in separate folders. Never solve inside the preserved reference run or overwrite the supplied geometry.

Use PowerShell for Windows/WSL administration:

```powershell
Get-Location
wsl --list --verbose
wsl -d Ubuntu
```

Use the exact distribution name displayed by `wsl --list --verbose`. Inside Ubuntu, Windows C: is normally `/mnt/c`. Do not type PowerShell commands into Bash.

Example Bash setup for documentation checks:

```bash
export PROJECT=/mnt/c/dev/aortic_project_public
cd "$PROJECT"
pwd
ls
```

Verify the public package using its publication manifest, not the full-input manifest that references excluded assets:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path.cwd()
manifest = json.loads((root/'PUBLICATION_MANIFEST.json').read_text())
bad = []
for item in manifest['files']:
    path = root/item['path']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        bad.append(item['path'])
if bad:
    raise SystemExit('Missing or changed files: ' + ', '.join(bad))
print('PASS:', len(manifest['files']), 'manifest entries match')
PY
```

There are 211 manifest records for the 212-file archive; the manifest does not hash itself. Run this in the untouched extraction, before editing scripts. Hashes detect changes; they do not establish scientific correctness.

## 3. Software and environment

The recorded solver was OpenCFD OpenFOAM v1912, patch 200626, on Ubuntu 24.04 under WSL. It ran serially. Other releases or builds may behave differently. OpenFOAM Foundation version numbers are not interchangeable with OpenCFD release numbers.

General Ubuntu prerequisites (installation changes your Ubuntu environment):

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg unzip fonts-dejavu-core
python3 -m venv "$HOME/aortic-docs-env"
source "$HOME/aortic-docs-env/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT/requirements.txt"
python -m pip freeze > "$PROJECT/environment-new.txt"
```

These are setup instructions, not a frozen historical environment. The public requirements request NumPy 2.x; several archived analysis scripts call `np.trapezoid`. The completed run also records a NumPy 1.26 compatibility repair using `np.trapz`. Use the analysis module accompanying the full case and record its NumPy version. Do not mix historical modules blindly.

For OpenFOAM, first inspect the existing installation:

```bash
command -v pimpleFoam
command -v checkMesh
pimpleFoam -help
```

If it is absent, use the [official OpenCFD Linux installation page](https://www.openfoam.com/download/openfoam-installation-on-linux) and select a compatible release/build. Do not assume installing today's default package recreates patch 200626. Source the `etc/bashrc` of the installation actually present. The historical Ubuntu package used `/usr/share/openfoam/etc/bashrc`; use that path only if the file exists:

```bash
source /usr/share/openfoam/etc/bashrc
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

Install Windows desktop versions of [3D Slicer](https://www.slicer.org/) and [ParaView](https://www.paraview.org/download/) for interactive viewing. The cited ParaView instructions use the 5.12 interface; labels can differ between versions. A Slicer installation contains its own Python environment: it is separate from Ubuntu's virtual environment.

Before copying full fields, check `df -h` in Ubuntu and free space on C:. The recorded simulation working set was about 3.42 GiB, excluding its separate snapshot. A reference copy plus a fresh run needs substantially more space. Do not treat the 16 MB public ZIP as an estimate of solver storage.

## 4. Where the vessel and flow data came from

The vessel comes from **AortaSeg-60 v1.1**, case **Anev_01**, by Dania El Rahal, David C. Rotzinger and Guillaume Fahrni. The source dataset supplies CT and an automated segmentation; it is not an expert-reviewed lumen ground truth.

- Dataset: https://zenodo.org/records/18147026
- Recorded source archive: https://zenodo.org/records/18147026/files/Anev.zip?download=1
- CT member: `Anev_01/nifti/Anev_01_image.nii.gz`
- Source mask: `Anev_01/segmentation/Anev_01_segmentation.nii.gz`
- License statement: https://zenodo.org/records/18147026/files/README.md?download=1

Download the dataset archive, inspect its members and extract only the required case into a new `source-data` folder. Keep the downloaded files immutable. The recorded source CT SHA-256 is `a678305ded7a2d60faf28211d73b9fc34f836e0cedf322e9ef966d5fda1cf4c7`; mask SHA-256 is `22710cf5e959497cac698a8015b2c04075773ea67c8293d3b291eacc5a920a07`. Compare with `sha256sum <filename>` before calling a download the same source. A mismatch requires investigation, not changing the expected checksum.

The publisher's README states **CC BY 4.0**. Preserve attribution and describe modifications. Older local provenance mentions a conflicting CC0 API value; that is historical evidence, not permission to remove attribution. See [ATTRIBUTION.md](ATTRIBUTION.md) and [REFERENCES.md](REFERENCES.md).

**Flow was assumed, not measured from this patient:**

```text
Q(t) = 5e-5 + 3.5e-5 sin(2*pi*t) m³/s
     = 50 + 35 sin(2*pi*t) mL/s
Period = 1 s; range = 15–85 mL/s
Density rho = 1060 kg/m³
Dynamic viscosity mu = 0.0035 Pa·s
Kinematic viscosity nu = mu/rho = 3.30188679245283e-6 m²/s
```

Both outlets use zero kinematic gauge pressure; their flow division is solved. There are no measured patient pressure/flow waveforms or calibrated outlet resistance/compliance models in this case.

## 5. CT alignment and mask repair: what was actually done

### 5.1 Alignment

The source CT and mask shared dimensions and spacing but their z origins differed by approximately 651 mm. The research correction reversed the CT slice direction from +0.6000000238 to −0.6000000238 mm per slice, retained the origin and voxel intensities, and updated qform/sform and qfac consistently. CT slice K maps to mask slice 1085−K. The corrected extent is approximately −647.638 to +3.362 mm.

This was a metadata correction without resampling; the uncompressed voxel payload was checked unchanged. It is inferred from image/file consistency, not independently confirmed acquisition orientation. Do not reproduce this by casually flipping a displayed image. Use `reports/alignment_provenance.json` and the separately preserved corrected CT, or reconstruct and audit both coordinate forms explicitly. Inspect axial, sagittal and coronal overlays before proceeding.

### 5.2 Recorded repair sequence

The following parameters come from `reports/repair_audit.json`; they document history, not a complete executable replacement for the missing program:

1. Begin from the extended green research candidate, which includes three actual source slices at each end. The raw AI mask alone is not a fully specified substitute for this intermediate.
2. Apply axial closing with a 1.6 mm scale and fill enclosed 2D holes while retaining cross-section components.
3. Regularize the signed distance with Gaussian sigma 0.8 mm; retain the largest 3D region and restore sizeable source components with less than half retained.
4. Apply 3D closing at 1.6 mm and fill enclosed 3D and axial cavities.
5. Reconstruct the two persistent terminal components separately from extended slice 279, using 0.8 mm local closing and preserving their separation.
6. Apply final signed-distance regularization with sigma 0.65 mm, cavity filling and largest-component selection.
7. Smooth the surface only with 10 windowed-sinc iterations, pass band 0.1.
8. Export the repaired mask, original reference, added voxels, removed voxels and surface; record checksums.

Result: source volume 112.196 mL; repaired volume 127.914 mL. Added 53,953 voxels (17.26%); removed 10,161 (3.25%); net +14.01%; total changed 20.51%. Both meaningful terminal channels persist across 26 slices. Surface: 137,336 triangles, one connected region, zero boundary/non-manifold edges, Euler characteristic 2. Self-intersection was not tested. Surface smoothing moved vertices by at most 0.161 mm, but mask-boundary changes reached 10.45 mm: these are different measurements.

**Reproducibility gap:** the exact repair-producing script and all intermediate selection decisions were not retained. Slicer smoothing with superficially similar values is a new reconstruction, not exact reproduction. Use the supplied repaired segmentation for downstream reproduction and label any further edits as a new version.

## 6. 3D Slicer: view, compare, edit and save

1. Start Slicer. Choose **File → Add Data** and select `data/repaired/REPAIRED_AND_CHANGES.seg.nrrd` from the extracted ZIP, or the loose repository copy. Confirm the description is **Segmentation**, then load.
2. Open **Segmentations**. Select the loaded segmentation and enable **Show 3D** / closed-surface representation if needed. Reset the 3D view to fit the vessel.
3. Toggle each segment's eye icon. Inspect the repaired vessel, original reference, added regions and removed regions separately. Lower opacity to compare overlapping structures. Do not interpret all simultaneously visible segments as one lumen.
4. Choose a four-up layout to see axial, sagittal and coronal slices plus the 3D view. Scroll through the terminal region and confirm that both lower channels remain visible.
5. For surface-only viewing, load `geometry/REPAIRED_surface_Slicer.vtp` as a **Model**. Prefer this tagged file to generic VTP/STL for Slicer. STL carries no units; the supplied STL represents RAS millimetres. Verify orientation before overlaying it. The CFD surface is in metres, a factor of 1000 smaller.
6. CT overlay is optional and requires the separately preserved corrected research CT. Load it as a **Volume**, select it as background and inspect the segmentation through all three slice views. Do not treat the uncorrected source CT as already aligned. Avoid applying the slice reversal twice.
7. To measure volume, open **Segment Statistics**, choose the segmentation and calculate the labelmap statistics. Record the segment name and representation. Smooth surface volume and binary labelmap volume can differ.
8. To edit, first save a new copy. Open **Segment Editor**, select the segmentation and reference volume if available, and choose the target segment. Use Paint/Erase or other effects only on that copy. Recheck narrow branches and both channels after every morphology operation. Record effects, physical parameters and software version.
9. To export a model, use **Segmentations → Export/import models and labelmaps**, choose the desired segments and export to models. Save the selected model with its coordinates/units documented. Do not export all audit segments as a single CFD vessel.
10. Click **Save**. Save the edited segmentation as a new `.seg.nrrd`. For a portable scene, choose a scene bundle `.mrb` when offered, or save the `.mrml` scene together with every referenced data file. A scene file alone may contain paths rather than all data. Reopen the saved bundle/copy to confirm it works.

Slicer is used here for anatomy and segmentation inspection. Loading a surface does not calculate velocity or WSS.

## 7. From surface to CFD domain

The retained preparation code is `src/prepare_case.py`. It clips the repaired RAS-mm surface at **z = −420 and −240 mm**, caps the cuts and converts coordinates to metres. It requires one upper inlet and two lower connected outlet groups. Lower groups are ordered by their x-centroid and named `outlet1` and `outlet2`; no anatomical branch identity is implied.

The OpenFOAM patch names are `aorta_wall`, `aorta_inlet`, `aorta_outlet1`, `aorta_outlet2`. Other closed reconstructed branches are treated as walls. `geometry/CFD_surface_SI.vtp` is a geometry artifact, not a solved volumetric mesh.

Do not run `src/prepare_case.py` blindly as a complete current pipeline. It calls `_dictionary_template.py`, which expects the excluded historical `results/pilot/surface_smooth10_RAS_mm.vtp`. The later coarse preparation script also expects an excluded archived case and boundary VTP. Resolving these inputs and auditing the generated dictionaries is necessary before a new mesh build.

The selected mesh was a nominal 1 mm uniform staircase mesh with **snapping off and no prism layers**. The recorded script `runs/runtime_optimization_20261018_01/src/prepare_coarse_uniform.py` used `blockMesh`, `snappyHexMesh -overwrite` and full native mesh checks. It depends on local historical paths; it is not a standalone ZIP-only builder.

For a **new mesh build with complete prepared dictionaries**, run in a new case only:

```bash
set -o pipefail
blockMesh -case "$CASE" 2>&1 | tee "$WORK/logs/blockMesh.log"
snappyHexMesh -case "$CASE" -overwrite 2>&1 | tee "$WORK/logs/snappyHexMesh.log"
checkMesh -case "$CASE" -allTopology -allGeometry 2>&1 | tee "$WORK/logs/checkMesh.log"
```

Stop on a failed command; do not run the next line automatically after failure. Inspect patch areas, disconnected regions, cell quality, wall approximation and inlet/outlet continuity. Recorded reference counts: 128,472 cells; wall 31,344 faces; inlet 881; outlet1 201; outlet2 46. These are reference measurements, not targets to obtain by removing mesh checks.

## 8. Full-case reproduction: prerequisites and safe copy

The separately preserved full run was reported at `large_assets/aortic_exploratory_demo_20261018_01` in the owner's local project. Its historical `/tmp` path is not a reliable permanent location. This directory and any tar archive of it are not included on GitHub.

A usable full run root must include:

```text
cfd/aorta/constant/polyMesh/{points,faces,owner,neighbour,boundary}
cfd/aorta/constant/transportProperties
cfd/aorta/constant/turbulenceProperties
cfd/aorta/system/{controlDict,fvSchemes,fvSolution}
cfd/aorta/0/...
cfd/aorta/<saved-time>/{U,p,phi,wallShearStress}
src/  run_config.json  reports/  logs/
```

An `aorta.foam` file is only an empty reader marker. A PVD is an index: its referenced VTP files must accompany it. Neither is a substitute for the mesh and fields.

**Conditional Bash example:** change `REFERENCE` to the actual durable run root, then copy to a new directory. This may require several GiB.

```bash
export REFERENCE=/mnt/c/path/to/project/large_assets/aortic_exploratory_demo_20261018_01
export WORK="$HOME/aortic_runs/my_run_01"
export CASE="$WORK/cfd/aorta"
test -d "$REFERENCE/cfd/aorta/constant/polyMesh" || { echo 'Full reference case missing'; exit 1; }
test ! -e "$WORK" || { echo 'Choose a new run name'; exit 1; }
mkdir -p "$(dirname "$WORK")"
cp -a "$REFERENCE" "$WORK"
mkdir -p "$WORK/logs" "$WORK/reports" "$WORK/results"
```

For **revalidation**, retain every saved state and do not solve. For a **fresh repeat**, move copied numeric time folders later than 0.01 s outside `cfd/aorta` into a checkpoint archive under the new run root. Do this only in the new copy. Keep 0 and the verified 0.01 state. This repeats the continuation from the reference initialization; it is not an independently initialized t=0 run. Never use an unreviewed recursive deletion command on the reference.

For a new t=0 calculation, the archived startup record includes `potentialFoam -initialiseUBCs -writephi` followed by independent reconstruction (`reconstruct_poly_initial.py`) and a bounded 0–0.01 s solve. All scripts and their inputs must be restored and audited first. Do not replace that procedure with a zero-velocity start and call it identical initialization.

## 9. Solver settings, execution and WSS

Inspect `constant/transportProperties`, `constant/turbulenceProperties`, `0/U`, `0/p`, `system/controlDict`, `system/fvSchemes`, and `system/fvSolution` in the copied case. Preserve the actual case's discretization and linear solvers.

| Setting | Latest recorded value |
|---|---|
| Solver | `pimpleFoam`, serial |
| Wall | rigid, no slip |
| Fluid | laminar, Newtonian; nu = 3.30188679245283e-6 m²/s |
| Inlet | synthetic flow-rate waveform above |
| Outlets | two zero kinematic gauge-pressure boundaries |
| `startFrom` | `latestTime` for continuation |
| `endTime` | 3.0 s |
| `adjustTimeStep` | yes |
| `maxCo` | 0.7 |
| `maxDeltaT` | 0.0002 s |
| `writeControl` | adjustableRunTime |
| `writeInterval` | 0.01 s |
| `purgeWrite` | 0 |
| PIMPLE | 1 outer, 2 pressure, 2 non-orthogonal correctors |

In the copied run configuration set `case_name` to `aorta` and `end_time_s` to 3. Do not use the ZIP root `run_config.json`: it describes the older 30-second `repaired_run_01` preparation.

1. Check the copied mesh with the native command above; inspect the log for `Mesh OK.` and all required patches.
2. Confirm no other solver/controller is writing this case. Start only one.
3. Prefer the full case's retained `src/run_cycles.py` controller after adapting its `PROJECT`, `ROOT`, `OUTER` and `CAD` paths and checking its required reports. That controller is **not in the public ZIP**. The historical command was `python3 src/run_cycles.py` from the full run root.
4. If using a manually supervised new continuation instead, the native command below is an alternative, not the original automatic safety controller. Monitor storage, Courant numbers, finite fields and time-step progress; stop if a gate fails.

```bash
set -o pipefail
pimpleFoam -case "$CASE" -noFunctionObjects 2>&1 | tee "$WORK/logs/manual_solver.log"
```

5. Require a normal `End`, exit code zero and a saved 3 s state. Residuals alone do not establish convergence. Recorded watchdog criteria included fatal/nonfinite output, deltaT below 1e-8 s, no progress for six minutes and a configured wall-time limit.
6. Calculate wall stress for the saved output range:

```bash
pimpleFoam -case "$CASE" -postProcess -func wallShearStress -time '0.01:3' \
  2>&1 | tee "$WORK/logs/WSS.log"
```

7. Confirm each required time has `wallShearStress`, and inspect its dimensions. The reference field uses `[0 2 -2 0 0 0 0]` (m²/s²). Multiply by rho **once** to obtain Pa. If the output is already in Pa, do not multiply again. In this incompressible case, p also needs multiplication by rho to display pressure in Pa.

The historical run used a SHA1 compatibility library for some post-processing commands. If encountering that exact failure, inspect its retained logs and build instructions. Do not blindly preload an old binary on another platform; a current compatible installation may not need it.

## 10. Validation and cycle metrics

Use the modules accompanying the complete run. Inspect CLI options before copying commands: the public historical `validate_saved_fields.py` accepts fewer flags than the completed-run version.

**Conditional completed-run commands** (only if its `--help` confirms these options):

```bash
cd "$WORK"
python3 src/validate_saved_fields.py --help
python3 src/validate_saved_fields.py . --require-end 3 --minimum-times 199 \
  --minimum-time 1.01 --report-name saved_field_validation_final.json
python3 src/analyze_results.py
python3 src/check_periodicity.py .
```

The older validator in `runs/runtime_repair_20261017_01/src` supports `--require-end` and `--minimum-times` but not `--minimum-time` or `--report-name`. Its report labels initial-transient checks. Do not silently substitute it for the final validator. Both depend on a matching `src/analyze_results.py` under the chosen run root.

The checks establish:

- Required end time and sufficient saved fields; finite U, p and wall stress.
- Relative flow imbalance `abs(Qin − Qout1 − Qout2)/abs(Qin) < 0.005`.
- Relative synthetic inlet error below 0.01.
- Successive-cycle TAWSS change below 5%, plus separate phase-resolved U, p and WSS relative-L2 checks below 5%.

For the last 1-second window (2–3 s), with wall traction vector tau in Pa:

```text
TAWSS = integral(|tau(t)| dt) / T                       [Pa]
OSI   = 0.5 * (1 - |integral(tau(t) dt)| / integral(|tau(t)| dt))
RRT   = 1 / ((1 - 2*OSI)*TAWSS)                        [Pa^-1]
```

Use actual timestamps and trapezoidal integration, not an unweighted average of irregularly spaced samples. Treat zero denominators explicitly. RRT is this derived index, not a directly measured residence time in seconds. Area-weight aggregate wall metrics and volume/time-weight phase comparisons. Do not average stress vectors before taking magnitudes for TAWSS.

Recorded final results: flow imbalance 2.37e-10; inlet error 3.28e-8; U cycle difference 4.28%; p 3.65%; **phase-resolved WSS 8.86% (FAIL)**. Passing TAWSS change does not override that failure. Coarse/fine startup differences were 26.4% U, 7.9% p and 68.5% mapped WSS, so mesh accuracy is not established. The latest evidence is `runs/runtime_optimization_20261018_01/reports/FINAL_STATUS.json` in the ZIP.

## 11. ParaView: open the geometry or actual CFD

### Geometry-only route: public files

Open `geometry/CFD_surface_SI.vtp` or the repaired surface with **File → Open**, then **Apply** and **Reset Camera**. Use Surface With Edges to inspect triangles. This displays shape only: no velocity, p or WSS should be expected on a geometry-only file. Do not infer zero flow from an absent field.

### Full-case route: velocity and pressure

1. Access the full case from Windows through its Windows path or `\\wsl.localhost\Ubuntu\home\<user>\...`. Use the exact installed distribution name. If copying exported results elsewhere, preserve relative PVD dependencies.
2. If needed, create the reader marker in the new case with `touch "$CASE/aorta.foam"`.
3. In ParaView choose **File → Open**, select `aorta.foam`, and select OpenFOAM Reader if prompted. Choose reconstructed/serial case, not decomposed mode for this serial run.
4. In Properties enable `internalMesh` and the relevant boundary patches; enable arrays U, p and wallShearStress. Click **Apply**, then **Reset Camera**.
5. Select a saved time. Check the Information panel for the time range and cell count. If all time controls are inactive, verify the numeric field folders actually exist.
6. To inspect internal velocity, select the internal mesh, use **Slice**, position a plane across the vessel and click Apply. Color the slice by **U → Magnitude** in m/s. Use the eye icons to hide opaque surfaces that obscure it.
7. For pressure, add a **Calculator** on the appropriate cell-data input. Use `1060*p`, name it `pressure_Pa`, and Apply. This is gauge pressure, not absolute arterial pressure. Keep rho conversion tied to the field dimensions.
8. To inspect a distribution, open a Spreadsheet View for the selected output or use Plot Over Line on the flow volume. Save sampled data with **File → Save Data** and state which interpolation/filter was used.

### Streamlines and flow visualization

1. Isolate the internal volume using Extract Block if necessary.
2. If U exists only as cell data and the tracer needs point vectors, apply **Cell Data to Point Data**. This interpolates the display field; do not call it additional solver accuracy.
3. Apply **Stream Tracer**, choose U and place a line or point-cloud seed just inside the inlet. Use the actual inlet location and domain dimensions in metres, not arbitrary default seeds.
4. Apply and inspect whether seeds lie within the lumen. Set integration direction consistent with the flow; increase maximum streamline length only as needed. A Tube filter can make lines easier to see.
5. Color by speed. Show a semitransparent wall for context. Keep one fixed speed scale across the animation.

These are instantaneous streamlines at each time. They are not particle pathlines through a changing velocity field. The delivered movie uses a separate particle-advection renderer described below.

### Wall shear stress and derived metrics

1. Extract **only `aorta_wall`**. WSS is a wall quantity, not the internal volume or inlet cap.
2. On raw native wallShearStress with the dimensions above, add a cell-data Calculator: expression `1060*mag(wallShearStress)`, result `WSS_Pa`. Apply and color by that scalar.
3. If opening exported `WSS_Pa`, inspect whether it is a scalar magnitude or a three-component vector. The archived analysis exporter uses that name for a vector, while another exporter uses it for a scalar. Select Magnitude for a vector; do not multiply either Pa-valued version by rho again.
4. Open the full run's `wall_metrics.vtp` for `TAWSS_Pa`, `OSI` and `RRT_Pa_inverse`. A single metrics VTP is normally static, even if the flow movie is time-dependent.
5. If a `.pvd` series is provided, open the PVD rather than a single VTP to get all times. Keep the index and its referenced files together.
6. For comparison with the supplied movie, use a fixed WSS range 0–11.9 Pa for that original dataset. For a new run, compute and disclose its own global range; do not clip larger values silently. OSI has a defined 0–0.5 range.
7. Save the visualization with **File → Save State** (`.pvsm`). State preserves the pipeline and views, not all source fields. Reopen it and resolve moved data paths before sharing.

## 12. Make a video

### A. Recreate the supplied side-by-side renderer (full fields required)

The retained renderer is `runs/runtime_optimization_20261018_01/src/render_side_by_side.py`. It uses VTK to read the OpenFOAM case and streams raster frames into FFmpeg; the supplied movie was not a Slicer screen recording or a ParaView camera animation.

1. Verify that the full run contains all **300 actual saved times 0.01, 0.02, …, 3.00 s**, with U and wallShearStress, and a matching `WORK/src/analyze_results.py`.
2. Copy the renderer to a new scripts folder. Change `WORK` to the full run root; change `OUT` to a new output directory; leave `CASE=WORK/'cfd/aorta'` and use a new `MOVIE` name. It refuses to overwrite an existing final movie.
3. Use a Python environment compatible with the full case's analysis module. Ensure FFmpeg has libx264 and drawtext support and the configured DejaVu font exists. Check `ffmpeg -encoders` and `ffmpeg -filters` if it fails.
4. Run the edited renderer, retaining its log:

```bash
set -o pipefail
python3 /absolute/path/to/copied/render_side_by_side.py 2>&1 | tee /absolute/path/to/new-render.log
```

5. It reads each saved velocity/WSS state, checks finite values and native WSS units, converts stress once with rho, and determines one global stress color scale.
6. It seeds 1,400 particles in the inlet with random seed 20261018, samples U, advances positions by an Euler step of 0.01 s using that snapshot, and reinjects invalid/exiting particles. This visualization integration is distinct from the solver's smaller time steps. It does not interpolate unsaved flow fields.
7. It draws matching orthographic views in two 960×1080 panels. Left: particles colored by speed; right: wall points colored by instantaneous WSS. Both panels use the same camera basis. This is a raster visualization, not a newly computed flow solution.
8. It feeds 1920×1080 RGB frames through FFmpeg, labels simulation time, slows playback tenfold, and outputs H.264/yuv420p. There are 300 frames, approximately 29.91 s in the recorded MP4. No cycles are replayed.
9. The renderer checks metadata and fully decodes a temporary movie before promoting it to the final filename. Retain `encoding.log` and `render_report.json` alongside the video.

### B. Make a new ParaView animation

This creates a new visualization of the same saved data, not an exact reproduction of the supplied particle movie.

1. Build the velocity and wall pipelines above; split the layout into two render views if desired. Show flow on one side and wall WSS on the other. Link cameras through the view/camera-link controls, or explicitly match camera settings.
2. Open **View → Time Manager** (Animation View in some versions), choose **Snap To TimeSteps**, and select the required saved times. Preview Play to confirm the geometry/fields change with time.
3. Add **Annotate Time Filter** or time annotation and a text label stating “Exploratory transient CFD — coarse-mesh WSS unvalidated”. Preserve units in legends. Time should represent solver seconds, not playback duration.
4. Keep camera, opacity and color ranges fixed unless camera motion is a deliberate, disclosed presentation choice. Avoid automatic range rescaling on each frame.
5. Choose **File → Save Animation**, select the full layout, 1920×1080 and a new output directory. A PNG image sequence is portable across builds. Select the frame window corresponding to the desired saved states. Check the number and ordering of exported images.
6. Encode the PNG sequence with FFmpeg. For files renamed sequentially as `frame_0000.png` through `frame_0299.png`, this example gives 10 frames/s:

```bash
ffmpeg -n -framerate 10 -start_number 0 -i frame_%04d.png \
  -c:v libx264 -crf 20 -pix_fmt yuv420p -movflags +faststart new_paraview_video.mp4
```

Adapt the input pattern/start number to the actual exported filenames. `-n` prevents overwriting. Do not rename files out of time order. With 0.01 s simulated spacing and 10 fps, playback is 10× slower than simulation time. Exporting the same single state 300 times does not create transient flow.

### C. Video checks for either method

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,avg_frame_rate,nb_frames \
  -show_entries format=duration -of json new_video.mp4
ffmpeg -v error -xerror -i new_video.mp4 -f null -
```

Inspect first, middle and final frames for labels, legends, synchronization and missing data. Check that timestamps cover the intended range. Keep the output video, a preview image, the render settings, the saved ParaView state or renderer copy, source run ID and checksums together. Successful decoding proves file integrity, not physical validity.

## 13. Troubleshooting

| Symptom | Check and response |
|---|---|
| Slicer vessel is invisible | Correct data type, segment visibility, Show 3D and Reset Camera |
| CT and mask do not align | Corrected versus raw CT; qform/sform, slice mapping, RAS/LPS; do not guess a visual transform |
| Model is 1000× too small | CFD metres versus Slicer millimetres; scale only a new display copy |
| ParaView has no U/p/WSS | Geometry-only file or missing fields; obtain the full case |
| ParaView has only one time | Single VTP or incomplete numeric folders/PVD references |
| WSS looks zero in the volume | Extract wall patch and inspect the native field |
| WSS is 1060× too large | Density conversion applied twice |
| Stream Tracer is empty | Seed outside fluid, wrong vector association, unavailable U or wrong length units |
| `np.trapezoid` is missing | NumPy/module mismatch; use the matching retained environment or an explicitly recorded compatibility edit |
| Renderer reports fewer than 300 states | Required outputs absent; recover saved fields or run a new case; do not duplicate frames |
| `Mesh OK` but WSS changes strongly | Mesh validity differs from solution accuracy; conduct controlled refinement studies |
| Phase WSS check fails | Retain FAIL and label transient; further cycles require a new planned run and rechecking |
| Old script cannot find `/tmp/...` | Recorded absolute path needs relocation; confirm asset exists before editing paths |
| Disk fills | Stop your own new run safely; preserve checkpoints; do not delete the reference to force continuation |

## 14. What remains before stronger research claims

Retain a reproducible repair implementation with all intermediate decisions; independently check anatomy and orientation; perform spatial and time-step sensitivity studies; reach and verify cycle agreement without relaxing thresholds; evaluate boundary-condition sensitivity; and compare against independent measurements if claiming validation. The larger project also proposes a physical phantom/pump experiment and AI work: neither is delivered or validated by this CFD archive.

For each new run, record software versions, input checksums, geometry changes, mesh settings, boundary conditions, solver dictionaries, runtime, storage, all checks (including failures), and exact export commands. Keep original and new results separately.

## 15. Sources and how to read the historical archive

Project-specific evidence is in the extracted ZIP: `reports/repair_audit.json`, `reports/repair_README.md`, `reports/alignment_provenance.json`, `runs/runtime_optimization_20261018_01/reports/COARSE_MESH_UNIFORM.json`, `FINAL_STATUS.json` in the same reports folder, the renderer source and its delivered `render_report.json`. A report saying “no solve performed” describes its earlier stage; it does not supersede the later final status.

Official software references for the instructions:

- [Slicer: loading and saving data](https://slicer.readthedocs.io/en/latest/user_guide/data_loading_and_saving.html)
- [Slicer: Segmentations](https://slicer.readthedocs.io/en/latest/user_guide/modules/segmentations.html)
- [ParaView 5.12 user guide](https://docs.paraview.org/en/v5.12.0/UsersGuide/)
- [ParaView: filtering](https://docs.paraview.org/en/v5.12.0/UsersGuide/filteringData.html)
- [ParaView: saving results and animation](https://docs.paraview.org/en/v5.12.0/UsersGuide/savingResults.html)
- [OpenCFD: Linux installation](https://www.openfoam.com/download/openfoam-installation-on-linux)
- [OpenCFD: wallShearStress](https://doc.openfoam.com/2312/tools/post-processing/function-objects/field/wallShearStress/) — newer documentation; recorded commands were checked against project scripts for v1912.
- [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) and [ffprobe](https://ffmpeg.org/ffprobe.html)

These explain software operation, not patient-specific validation. See [REFERENCES.md](REFERENCES.md) for dataset and software publication credits.
