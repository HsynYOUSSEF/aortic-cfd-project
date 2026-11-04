"""Run with ParaView pvpython, not system Python. Requires real full case fields."""
import argparse
from pathlib import Path
from paraview.simple import OpenFOAMReader, GetAnimationScene, GetActiveViewOrCreate, Show, ColorBy, ResetCamera, SaveState
p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('output_pvsm',type=Path);a=p.parse_args()
case=a.case.resolve();out=a.output_pvsm.resolve()
if out.exists():raise FileExistsError(out)
if not (case/'constant/polyMesh/points').is_file():raise RuntimeError('Full mesh required')
marker=case/'aorta.foam'
if not marker.exists():marker.touch()
r=OpenFOAMReader(FileName=str(marker));r.MeshRegions=['internalMesh'];r.CellArrays=['U','p'];r.UpdatePipelineInformation()
scene=GetAnimationScene();scene.UpdateAnimationUsingDataTimeSteps()
view=GetActiveViewOrCreate('RenderView');display=Show(r,view);ColorBy(display,('CELLS','U','Magnitude'));ResetCamera(view)
out.parent.mkdir(parents=True,exist_ok=True);SaveState(str(out));print('Saved',out,'; state references case files, it does not embed them.')
