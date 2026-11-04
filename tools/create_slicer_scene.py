"""Run inside Slicer's Python console. Creates a new geometry-only scene bundle."""
from pathlib import Path
import slicer

def create_scene(package_root, output_mrb, corrected_ct=None):
    root=Path(package_root); out=Path(output_mrb)
    if out.exists():raise FileExistsError(out)
    if slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSegmentationNode') or slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScalarVolumeNode'):
        raise RuntimeError('Use a fresh Slicer session to avoid including unrelated data.')
    seg=slicer.util.loadSegmentation(str(root/'data/repaired/REPAIRED_AND_CHANGES.seg.nrrd'))
    if not seg:raise RuntimeError('Segmentation failed to load')
    seg.CreateClosedSurfaceRepresentation()
    if corrected_ct:
        volume=slicer.util.loadVolume(str(corrected_ct))
        if not volume:raise RuntimeError('CT failed to load')
        slicer.util.setSliceViewerLayers(background=volume)
    slicer.util.resetThreeDViews()
    out.parent.mkdir(parents=True,exist_ok=True)
    if not slicer.util.saveScene(str(out)):raise RuntimeError('Scene save failed')
    print('Saved',out,'; reopen and inspect alignment before sharing.')
