# Aortic CFD Project

Exploratory study of pulsatile blood flow in reconstructed aortic geometry, with wall shear stress analysis and flow visualization.

## Publication status

This repository currently contains a project overview. The cleaned implementation, detailed reproduction documents, verification manifests and simulation assets still need to be transferred from the source workspace. Paths listed below are source-workspace paths, not downloadable files in this repository.

The latest results below are transcribed from the source-workspace handoff dated 19 October 2026. The underlying files have not yet been independently checked against this repository.

## Objective and data provenance

The project investigates reconstruction of aortic geometry from medical-image segmentation, computational fluid dynamics, and flow-related wall quantities. It is an exploratory engineering study, not a clinically validated predictor of aneurysm rupture or a basis for treatment decisions.

The original anatomy comes from AortaSeg-60, case Anev_01. Its supplied automated segmentation is not expert-validated blood-lumen ground truth. The inlet flow is a modeling assumption rather than a patient measurement. The exact repaired-run settings must be taken from the preserved case dictionaries and reproduction document; older-case settings must not be substituted.

## Latest repaired-geometry run

| Item | Status reported by the source workspace |
| --- | --- |
| Run | aortic_exploratory_demo_20261018_01 |
| Simulated duration | 3.0 seconds |
| Phase-resolved WSS cycle change | 8.86% |
| Periodicity acceptance threshold | 5% |
| Periodicity result | **Failed: solution remains transient** |
| Video | Aortic_Exploratory_SideBySide_1080p.mp4 |
| Video checks | 300 frames, 1080p; metadata and full-decode checks passed |
| Durable case | large_assets/aortic_exploratory_demo_20261018_01 |
| Preservation checks | All 2,675 entries matched in path, type, size and SHA-256; no missing or extra entries |
| Preserved contents | Full fields, logs, reports, ParaView files and state directories 0, 1, 2 and 3 |

A successful video decode verifies the media file, not the physical accuracy of the flow. The failed cycle-agreement gate must remain visible in reports and presentations. Older simulations on different geometry cannot establish periodicity or mesh independence for this repaired case.

## Workflow

1. **Identify and preserve data.** Record the dataset, case identifier, image and mask checksums, physical units and coordinate metadata.
2. **Review and repair geometry.** Inspect image alignment, lumen interpretation, surface integrity and inlet/outlet definitions. Retain the exact repair code and parameters.
3. **Mesh the fluid domain.** Preserve meshing parameters and quality reports. Mesh-quality checks alone do not establish mesh-independent WSS.
4. **Define the flow model.** Record fluid properties, wall assumptions, inlet waveform, outlet condition, solver and time-step controls from the actual case.
5. **Solve and verify.** Check solver stability and mass conservation, then compare corresponding phases of consecutive cycles. Continue from preserved checkpoints when periodicity fails.
6. **Analyze wall quantities.** WSS represents tangential fluid traction on the wall; TAWSS averages its magnitude over a defined interval; OSI describes directional oscillation. State units, sample spacing and averaging interval. Do not label transient-cycle quantities as converged periodic results.
7. **Visualize and archive.** Document color scales, label simulation status and preserve full fields with checksums outside temporary storage.

This overview is not a runnable reproduction guide. Exact commands require the latest scripts, dependency versions, dictionaries and REPRODUCING.md.

## Source-workspace documentation

| Path | Purpose |
| --- | --- |
| REPRODUCING.md | Recorded reproduction steps and assumptions |
| REFERENCES.md | Full software and data bibliography |
| reports/CLEANUP_MANIFEST_20261019.json | Evidence for removal of approximately 196 MB of duplicates and caches |
| large_assets/latest_run_inventory.json | Durable case inventory and verification status |
| large_assets/aortic_exploratory_demo_20261018_01_SHA256.json | Per-file preservation checksums |
| deliverables/Aortic_Exploratory_SideBySide_20261018_01/Aortic_Exploratory_SideBySide_1080p.mp4 | Latest exploratory video |
| UPLOAD_STATUS.md | Publication status; update after transfer |

An untouched pre-cleanup backup was reported at backups/aortic_repaired_simulation_untouched_20261019.tar, with SHA-256:

    3ad5937ddf35c74900449b201d1d8f6701d82b8c54b67c92e7bd52e4f060ec77

CTs, masks, repaired geometry, unique validation evidence and restart checkpoints were retained. The original temporary case was left untouched after verification of the durable copy.

## Remaining work

- Transfer the cleaned code, detailed documentation and compact verification evidence.
- Recover the exact repaired-mask generation script, or reconstruct and verify a reproducible repair procedure. The original script was not retained.
- Continue the repaired case and reassess the unchanged periodicity criterion.
- Establish mesh and time-step sensitivity for the repaired geometry.
- Review anatomical validity and boundary conditions; patient-specific validation is not established.
- Publish large assets separately with verified download locations and checksums. No large-asset release is provided here yet.

## References and attribution

- **AortaSeg-60:** https://zenodo.org/records/18147026 — source of the Anev_01 image and supplied segmentation.
- **Gmsh official manual:** https://gmsh.info/doc/texinfo/ — meshing documentation; the source-workspace REFERENCES.md includes the paper citation requested by this manual. That full bibliography still needs transferring.

The source-workspace handoff reports conflicting dataset license metadata: CC BY 4.0 in the local README versus CC0 in API provenance, and no license value displayed on the record when checked. This overview does not resolve that conflict or grant redistribution rights. Preserve attribution and clarify applicable terms before redistributing source data. No blanket license is assigned to third-party data by this repository.
