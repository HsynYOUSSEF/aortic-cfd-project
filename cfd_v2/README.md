# cfd_v2: corrected CFD setup

This folder fixes the weak points of the two pilot runs (see the main README):

| Pilot runs | cfd_v2 |
| --- | --- |
| Staircase wall: snapping off, no or very few prism layers | Snapping on, 5 prism layers on the wall |
| Inlet and outlets cut flush with the region of interest | Flow extensions: 3 diameters at the inlet, 5 at each outlet |
| Invented sine inflow written into the code | Inflow read from a CSV file you supply (one cycle) |
| Two zero-pressure outlets, uncontrolled flow split | Flow split set explicitly (Murray's law by default) |
| 3 cycles, not periodic | 6 cycles by default, cycle-to-cycle TAWSS change reported |
| One mesh | Three meshes and a grid convergence index (GCI) |

What was tested here (2-core cloud machine, Ubuntu `openfoam` 1912 package):

| Test | Result |
| --- | --- |
| `build_case.py` on `geometry/REPAIRED_surface_RAS_mm.vtp` | Closed, manifold surface with extensions; inlet 33.5 mm, outlets 16.9 and 8.6 mm equivalent diameter |
| Meshing, 1.6 mm background (0.8 mm at the wall), no extra smoothing | 351,492 cells; layers on the vessel wall about 6% of target (staircase surface) |
| Same with `--smooth 30` (wall moved 0.25 mm, 95th percentile) | 430,409 cells; vessel-wall layers 2.5 of 5 on average (56% of target thickness); `checkMesh` fails only 3 skewed faces |
| Short solve, 2.4 mm mesh, 0.1 s on 2 cores, then `analyze_case.py` | Runs end to end; OpenFOAM's `wallShearStress` crashes (sha1 bug), WSS from velocity used instead |
| `tests/pipe_wss_check.py`: steady Poiseuille pipe, D = 10 mm, Re 77 | WSS 0.0708 Pa vs exact 0.0713 Pa: **error 0.6%**; 5 layers on 100% of the wall |
| `gci.py` on an exact second-order series | Observed order 2.00, correct extrapolated value |

Not run here: full 6-cycle solves and the 3-mesh study (hours each).

## 1. Supply a real inflow waveform

`inflow_waveform_PLACEHOLDER.csv` is the old sine and is **not physiology**; the builder refuses it unless you pass `--allow-placeholder-waveform` (for tests only).

Make `cfd_v2/inflow_waveform.csv` with one cardiac cycle of measured infrarenal flow:

```csv
t_s,Q_mL_s
0.00,...
...
1.00,...   (same flow as t = 0)
```

Source: digitise the resting infrarenal curve from Les et al. 2010 (Annals of Biomedical Engineering 38:1288-1313), for example with WebPlotDigitizer, and write the figure number in a `#` comment line at the top of the file. Keep the same waveform for every geometry variant.

## 2. Build three meshes

```bash
# Ubuntu: sudo apt install openfoam   (v1912, the version used in the pilot runs)
python cfd_v2/build_case.py geometry/REPAIRED_surface_RAS_mm.vtp runs/ms/coarse --cell-mm 1.6 --smooth 30 --waveform cfd_v2/inflow_waveform.csv
python cfd_v2/build_case.py geometry/REPAIRED_surface_RAS_mm.vtp runs/ms/medium --cell-mm 1.1 --smooth 30 --waveform cfd_v2/inflow_waveform.csv
python cfd_v2/build_case.py geometry/REPAIRED_surface_RAS_mm.vtp runs/ms/fine   --cell-mm 0.8 --smooth 30 --waveform cfd_v2/inflow_waveform.csv
```

`--smooth N` adds N windowed-sinc smoothing iterations before cutting and records how far the wall moved. Prism layers cannot grow on a voxel-staircase wall: on the pilot-run-2 surface, layers covered only about 6% of the wall thickness target without extra smoothing and 56% with `--smooth 30` (wall moved 0.25 mm at the 95th percentile). Use the same smoothing for every mesh of a study; varying it is study variant C.

Replace the surface by your reviewed lumen surface (STL or VTP in RAS millimetres, exported from 3D Slicer) when it exists. `--inlet-z` and `--outlet-z` set the two cut planes; the outlet plane must cross both iliac arteries. Each case gets `case_info.json` with diameters, extension lengths, flow split and all settings.

## 3. Mesh, solve, analyse

```bash
bash cfd_v2/run_case.sh runs/ms/coarse 4     # 4 = CPU cores
```

Steps: blockMesh → snappyHexMesh → checkMesh (must say `Mesh OK.`, or fail only on a few skewed faces, and must not leak) → pimpleFoam (in parallel with `mpirun`) → `analyze_case.py`. OpenFOAM's own `wallShearStress` is tried but optional: in Ubuntu's package it crashes with a 'sha1' error, so `analyze_case.py` computes WSS from the velocity of the wall cells (μ·U_t/d), checked against the exact pipe solution with `python cfd_v2/tests/pipe_wss_check.py /tmp/pipe_check`. The results are in `CASE/results/`: `wall_metrics.vtp` (TAWSS, OSI, RRT on the wall, open in ParaView) and `summary.json` (area-weighted means in 30 mm z bands, area below 0.4 Pa, cycle-to-cycle change).

Acceptance checks before you use a result:

- `TAWSS_cycle_change_relL2` below 0.01 (1%); otherwise run more cycles in a new case.
- Wall layers on most of the wall: look at the layer summary at the end of `log.snappyHexMesh`.
- Then the GCI below.

## 4. Grid convergence

```bash
python cfd_v2/gci.py runs/ms/fine/results/summary.json:0.8 runs/ms/medium/results/summary.json:1.1 runs/ms/coarse/results/summary.json:1.6
```

Target: GCI below 5% on the TAWSS of every band. Use the finest mesh that passes for the sensitivity study.

## Limits that remain

- Rigid wall, Newtonian blood, laminar flow: standard baselines, stated in the report.
- Outlets: an explicit flow split, not a Windkessel. A three-element Windkessel needs a compiled OpenFOAM (coded boundary condition) or SimVascular; Ubuntu's `openfoam` package has no headers to compile one.
- The cut planes are horizontal (normal to z), not normal to the vessel centreline. Check the outlet diameters in `case_info.json`: on the pilot surface the outlets are 16.9 and 8.6 mm, so Murray's law sends 89% of the flow to outlet 1. If a cut passes through the bifurcation rather than across both iliacs, move `--outlet-z`.
- Vessel-wall layers reach about half the target thickness on the pilot surface; check the layer table in `log.snappyHexMesh` for every mesh and report it.
- The inlet profile is flat; it develops along the inlet extension.
