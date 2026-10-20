> Public subset, 21 October 2026: raw CT volumes and full CFD fields/checkpoints are intentionally excluded. The following historical guide describes the preserved local package. Commands that read those assets require the local originals or source dataset. Scripts with recorded absolute paths must be adapted. See UPLOAD_STATUS.md for uploaded scope.

# Reproduction and validation record

This document distinguishes the completed exploratory result from the older prepared 30-second pipeline. The old `run_all.sh` / `Run-Simulation.ps1` launcher targets a different, fine mesh and a 30-second solve; it is not the procedure that produced the latest result and must not be used to reproduce the 3-second demonstration.

## Recorded environment

- Solver: OpenFOAM OpenCFD build `OPENFOAM=1912 patch=200626`, recorded in solver logs.
- Platform: Ubuntu 24.04 under WSL, accessed from the Windows project path. The run was serial (`nProcs=1`) with one OpenMP/BLAS thread. A managed MPI socket restriction prevented a parallel benchmark; do not infer parallel speed.
- Mesh: native OpenFOAM `checkMesh -allTopology -allGeometry` passed for the selected uniform staircase coarse candidate; 128,472 cells. This is mesh-validity only, not mesh-accuracy validation.
- Solver: `pimpleFoam`, adjustable time step, `maxCo=0.7`, `maxDeltaT=0.0002 s`, one outer corrector, two pressure correctors and two non-orthogonal correctors. Time integration used its solver-controlled time steps; saved-state cadence was 0.01 s (`purgeWrite 0`).
- Fluid: Newtonian, rigid wall; kinematic viscosity `3.30188679245283e-6 m²/s` (dynamic viscosity 0.0035 Pa·s at density 1060 kg/m³).
- Inlet: synthetic `Q(t)=5e-5 + 3.5e-5 sin(2 pi t)` m³/s, period 1 s. Both separate outlets use zero kinematic gauge pressure and the split is solved. The other closed branches are walls.
- Runtime: 2,331.98 s per one-second cycle for the solver, about 1.94 h total solver wall time across 0.01–3.0 s. The report's measured solver elapsed time is authoritative; allow extra time for saved-field/WSS and rendering checks.

## Reproduce or revalidate the existing run

The self-contained input for revalidation is the separate archive `large_assets/aortic_exploratory_demo_20261018_01.tar.gz`. Extract it into a new working directory (never over the retained run). It contains the actual OpenFOAM case, all written states, source scripts, reports and logs. The tested controller also reads project reports, the validated coarse-mesh record and bounded-test directories by their recorded project paths. On another computer, edit the `PROJECT`, `ROOT`, `OUTER` and `CAD` path constants in `src/run_cycles.py` to the local project and bounded-test locations before running it.

The completed run's controller command was:

```bash
python3 src/run_cycles.py
```

For a fresh repeat, make a new copy of the extracted case and keep the initial 0.01 s state while removing later numeric time folders **only in that new copy**. Keep the solver dictionaries, mesh, scripts and reports. Configure `startFrom latestTime`, `endTime 3.0`, `writeInterval 0.01`, `purgeWrite 0`, `maxCo 0.7`, `maxDeltaT 0.0002`, and the corrector settings above. Run the controller once, without a second solver/controller. It includes a storage guard and rejects missing/failed mesh, finite-field, flow balance, inlet, timestep-collapse, and Courant checks.

After the solver reaches 3.0 s, retain and run the same checks, without changing thresholds:

```bash
python3 src/validate_saved_fields.py . --require-end 3 --minimum-times 199 --minimum-time 1.01 --report-name saved_field_validation_final.json
python3 src/analyze_results.py
python3 src/check_periodicity.py .
```

The final command returns a failure for periodicity when the phase-resolved U, pressure or WSS relative L2 difference is at least 5%. That outcome is meaningful: the completed run failed only the phase-resolved WSS gate at 8.8623% and remains transient. Do not extend it automatically or relabel the failure. Conservation, inlet, finite-field checks and TAWSS-cycle change passed.

## Reproduce the delivered video

The renderer reads the actual 300 saved states and the saved `U` and `wallShearStress` fields from the extracted case. The checked-in `runs/runtime_optimization_20261018_01/src/render_side_by_side.py` records the tested absolute paths at its top. Set `WORK` to the extracted case root and `OUT`/`MOVIE` to a new output folder on the target machine before running:

```bash
python3 runs/runtime_optimization_20261018_01/src/render_side_by_side.py
ffprobe -v error -show_entries stream=codec_name,width,height,avg_frame_rate,nb_frames -show_entries format=duration -of json <new-video.mp4>
ffmpeg -v error -xerror -i <new-video.mp4> -f null -
```

The recorded output is 1920×1080, 300 frames, 29.91 s (10× slowed across the 2.99 s interval between 0.01 and 3.00 s), decoded without errors. No cycles are replayed and no interpolated flow fields are used. Particle positions advance by the current saved velocity over the 0.01 s interval. Both panels use the same orthographic camera basis. Native WSS dimensions are `[0 2 -2 0 0 0 0]` (m²/s²); the renderer multiplies by density 1060 kg/m³ once to convert to Pa. One global 0–11.9 Pa color scale is held throughout.

The earlier single-panel video is still at its original path under `/tmp/aortic_exploratory_demo_20261018_01/results/video_1080p_transient/`. The new side-by-side video is the durable project deliverable.

## Input preparation and geometry assumptions

To check the prepared package and geometry without solving, use its local environment and the existing scripts:

```bash
python3 src/verify_package.py
python3 src/check_surface.py
```

The repaired mask is a research morphology reconstruction, not an anatomical ground truth. Its recorded method and measurements are in `reports/repair_audit.json` and `reports/repair_README.md`. It uses inferred CT direction correction because original DICOM orientation was unavailable. The symmetric changed volume is 20.51%, including 17.26% added and 3.25% removed source voxels. Both lower channels were deliberately retained. Self-intersection was not tested in the repair audit. Do not equate watertightness with an accurate lumen boundary.

The coarse run started from the validated 128,472-cell uniform staircase candidate and independently reproduced the established initialization. Coarse/fine startup sensitivity was 26.4% U, 7.9% p and 68.5% mapped WSS; the mesh was accepted for exploration only. The chosen corrector setting was supported by a 0.04 s bounded comparison (one vs. two outer correctors gave 0.1426% U, 0.0518% pressure and 0.6161% WSS differences). The 0.01 s output cadence passed a bounded 0.01–0.05 s comparison (U and WSS identical at saved comparison phases; pressure difference 8.45e-11 relative L2), but this is not proof of full-cycle or mesh accuracy.

## Known limits on exact reproduction

The package contains the original CT, masks, geometry, scripts, run status, latest full run in the existing WSL `/tmp` directory, and delivered video. Software package freeze data for the completed exploratory run was not captured as a full lockfile, and several controller paths were absolute. The exact repair-producing program was not retained in the workspace: its algorithm and parameter audit remain in `reports/repair_audit.json` and `reports/repair_README.md`, but regeneration of the repaired mask from original voxels is not bit-for-bit reproducible from the current source tree. The OpenFOAM build and operative model settings are recorded above; exact host package versions beyond those logged were not captured as a full lockfile. Solver trajectories may differ across hardware and library builds. The initial/final fields and verification reports in `/tmp/aortic_exploratory_demo_20261018_01` are the reference evidence.
