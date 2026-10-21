# Latest-run package status

## Source recovery update

Recovered preparation and analysis scripts were found in the original uploaded archive. They are now included under `repro/recovered`, with byte hashes. New tools and source masks are in the expanded ZIP. See [REBUILD_FROM_SOURCE.md](REBUILD_FROM_SOURCE.md).

Real-input case preparation, replacement-mask execution, two synthetic geometry tests and overwrite rejection passed. OpenFOAM meshing, solving, new analysis/video and Slicer/ParaView application tests were not run. The replacement mask is a distinct research candidate, not the original repair.

## Included and checked

- Latest 1080p side-by-side video, preview and render report.
- Repaired segmentation and Slicer-tagged surface, STL, SI-unit CFD surface.
- Latest final-status report, selected mesh evidence and geometry/alignment audits.
- Renderer source, step-by-step guide and attribution.
- SHA-256 inventory of the compact package.
- Newly prepared backup and scene-generation helpers.

## Still required from the laptop

- Full `large_assets/aortic_exploratory_demo_20261018_01` directory: mesh, dictionaries, initial/restart states, all saved U/p/phi/WSS, exact analysis/controller source and logs.
- Source CT and corrected research CT; any required segmentation-generation inputs.
- Exact environment records if available. No exact historical dependency lockfile has been recovered.
- A generated and reopened `.mrb` scene and `.pvsm` visualization; the helper scripts are not those finished artifacts.

The complete original case and CT volumes were not found in the current hosted workspace. Some preparation/analysis source has now been recovered, but not the exact final controller or complete original run setup. This package does not replace a complete laptop backup. Do not delete the local project on the basis of this upload.

## Helper commands

Stop the solver before backing up. In Windows PowerShell, with Python installed, replace both paths:

```powershell
python tools/backup_latest_run.py "C:\path\to\large_assets\aortic_exploratory_demo_20261018_01" "E:\AorticBackup\latest-full-run.zip"
```

The output must be outside the source directory and must not exist. The tool checks basic case structure, refuses symlinks, checks free space, creates a ZIP64 archive, hashes each archived file after reading it back, checks that source files did not change, and writes an archive checksum. It never removes source data. This is byte-preservation verification, not a check of scientific completeness or every restart state. Store CT files and other required project inputs separately too. Use independent storage and verify a restored copy before deleting originals.

To make a segmentation scene, open a fresh Slicer session and use its Python console (edit paths):

```python
exec(open(r'C:/path/to/latest-package/tools/create_slicer_scene.py').read())
create_scene(r'C:/path/to/latest-package', r'E:/AorticBackup/latest_geometry.mrb')
```

To include the correctly aligned CT, supply `corrected_ct=r'C:/path/to/corrected_research_CT.nii.gz'` as a third argument. Inspect alignment and reopen the saved scene. The helper does not perform or validate CT alignment.

For a basic velocity visualization state, use ParaView's `pvpython`:

```bash
pvpython tools/create_paraview_state.py /path/to/full_run/cfd/aorta /path/to/new/latest_flow.pvsm
```

The state references the full case, so share both. Follow PROJECT_GUIDE.md to add slices, streamlines and wall stress. This helper is a basic starting view, not a finished WSS layout.

## Verification of the new helpers

Backup helper: tested on a temporary binary-data fixture, including archive readback, overwrite rejection and rejection of output inside source. All three helpers passed Python syntax checks. Slicer and ParaView are unavailable in this environment, so their helper scripts have not been application-tested. No simulation was rerun for this publication update.
