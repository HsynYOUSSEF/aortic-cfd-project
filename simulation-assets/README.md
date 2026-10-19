# Simulation asset upload status — 19 October 2026

The repository was verified as `HsynYOUSSEF/aortic-cfd-project`, public, with authenticated push permission. The owner requested that it remain public and that assets affected by the unresolved source-dataset redistribution license be held. **No simulation binaries or source medical images have been uploaded.**

## Located and checked

The preserved run is `large_assets/aortic_exploratory_demo_20261018_01/` in the local Desktop project `Aortic_Repaired_Simulation_20261015`. Its 2,675 files total 2,969,693,737 bytes. Each file was independently checked against the previously saved SHA-256 preservation manifest; see `inventory.json` for the result and selected asset hashes.

Selected source-project paths, all withheld:

- `deliverables/Aortic_Exploratory_SideBySide_20261018_01/Aortic_Exploratory_SideBySide_1080p.mp4` — 1080p demonstration; existing render evidence reports 300 frames and successful full decode. Media decoding was not rerun during this upload review.
- `geometry/REPAIRED_surface_Slicer.vtp` — VTK PolyData with 68,670 points and 137,336 polygons; the XML header contains a SPACE field. This is a geometry model, not a complete Slicer scene or a new Slicer load test.
- `large_assets/aortic_exploratory_demo_20261018_01/results/aorta/wall_metrics.vtp` — derived wall metrics.
- `large_assets/aortic_exploratory_demo_20261018_01/cfd/aorta/` — OpenFOAM case and saved fields.

## Blockers and storage route

The local source attribution identifies AortaSeg-60 v1.1, Anev_01, DOI 10.5281/zenodo.18147026. Its records disagree about CC0 versus CC BY 4.0. These statements were found in the existing project documentation; this review has not resolved the license. The owner chose to hold affected assets while retaining this public repository. That hold includes anatomy-derived video, geometry and numerical fields. No patient images, segmentation volumes or identifying medical metadata were published. Preservation hashes do not establish de-identification.

The C: drive had approximately 40 MB free at inspection, insufficient to stage the complete run for Git LFS or prepare a local release archive. Git LFS is installed. After redistribution is resolved, a versioned GitHub release with split archives and checksum verification is a suitable option for the full run; alternatively use Git LFS with confirmed available storage/quota. These uploads require workspace capacity or a suitable streaming transfer. No release, LFS object, or external-storage link has been created.

## Interpretation

The completed run is a coarse, exploratory, three-second simulation. The recorded phase-resolved WSS cycle difference is 8.8623%, exceeding the 5% acceptance threshold; it remains transient. A valid checksum or playable video does not establish anatomical or clinical validity.
