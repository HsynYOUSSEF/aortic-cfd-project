"""Generate the documented exploratory Anev_01 OpenFOAM case, in SI units."""
from pathlib import Path
import argparse,json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
ROOT=Path(__file__).resolve().parents[1]
def write(c,name,s,cls='dictionary'):
 p=c/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(f'FoamFile {{version 2.0; format ascii; class {cls}; object {p.name};}}\n'+s)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--name',default='aorta_coarse');ap.add_argument('--cell-mm',type=float,default=5);ap.add_argument('--end',type=float,default=15);ap.add_argument('--no-layers',action='store_true');ap.add_argument('--max-skew',type=float,default=4);ap.add_argument('--snap-tolerance',type=float,default=2);a=ap.parse_args();c=ROOT/'cfd'/a.name;c.mkdir(parents=True,exist_ok=False)
 r=vtk.vtkXMLPolyDataReader();r.SetFileName(str(ROOT/'results/pilot/surface_smooth10_RAS_mm.vtp'));r.Update();conn=vtk.vtkPolyDataConnectivityFilter();conn.SetInputConnection(r.GetOutputPort());conn.SetExtractionModeToLargestRegion();conn.Update();planes=vtk.vtkPlaneCollection()
 for z,n in [(-420,(0,0,1)),(-240,(0,0,-1))]:
  p=vtk.vtkPlane();p.SetOrigin(0,0,z);p.SetNormal(*n);planes.AddItem(p)
 clip=vtk.vtkClipClosedSurface();clip.SetInputConnection(conn.GetOutputPort());clip.SetClippingPlanes(planes);clip.SetGenerateFaces(True);clip.Update();tri=vtk.vtkTriangleFilter();tri.SetInputConnection(clip.GetOutputPort());tri.Update();clean=vtk.vtkCleanPolyData();clean.SetInputConnection(tri.GetOutputPort());clean.Update();norm=vtk.vtkPolyDataNormals();norm.SetInputConnection(clean.GetOutputPort());norm.AutoOrientNormalsOn();norm.ConsistencyOn();norm.SplittingOff();norm.Update();s=norm.GetOutput();v=vtk_to_numpy(s.GetPoints().GetData()).astype(float)*.001;f=vtk_to_numpy(s.GetPolys().GetData()).reshape(-1,4)[:,1:];xyz=v[f];labels=np.full(len(f),'wall',dtype='<U6');labels[np.max(abs(xyz[:,:,2]+.24),axis=1)<1e-7]='inlet';labels[np.max(abs(xyz[:,:,2]+.42),axis=1)<1e-7]='outlet';path=c/'constant/triSurface/aorta.stl';path.parent.mkdir(parents=True,exist_ok=True);stats={}
 with path.open('w') as out:
  for label in ['wall','inlet','outlet']:
   sub=xyz[labels==label];stats[label]={'triangles':len(sub),'area_m2':float(np.linalg.norm(np.cross(sub[:,1]-sub[:,0],sub[:,2]-sub[:,0]),axis=1).sum()/2)};out.write(f'solid {label}\n')
   for p in sub:
    n=np.cross(p[1]-p[0],p[2]-p[0]);n=n/np.linalg.norm(n) if np.linalg.norm(n)>0 else n;out.write('facet normal '+' '.join(map(str,n))+'\nouter loop\n');out.writelines('vertex '+' '.join(f'{x:.10g}' for x in q)+'\n' for q in p);out.write('endloop\nendfacet\n')
   out.write(f'endsolid {label}\n')
 stats.update(status='Exploratory unreviewed AI geometry; not patient-lumen validated',z_cuts_mask_RAS_mm=[-420,-240],SI_units=True,inlet_waveform='Assumed Q=50+35 sin(2 pi t) mL/s; period 1 s; not a patient measurement');(c/'geometry_provenance.json').write_text(json.dumps(stats,indent=2))
 lo=np.array([-.075,-.02,-.43]);hi=np.array([.04,.085,-.23]);n=np.ceil((hi-lo)/(a.cell_mm*.001)).astype(int);verts=[(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),(hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),(lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
 write(c,'system/blockMeshDict','convertToMeters 1; vertices ('+' '.join('('+' '.join(map(str,x))+')' for x in verts)+'); blocks (hex (0 1 2 3 4 5 6 7) ('+' '.join(map(str,n))+') simpleGrading (1 1 1)); edges (); boundary (box {type patch; faces ((0 3 2 1)(4 5 6 7)(0 1 5 4)(3 7 6 2)(0 4 7 3)(1 2 6 5));}); mergePatchPairs ();')
 sn='''castellatedMesh true; snap true; addLayers true;
geometry {aorta.stl {type triSurfaceMesh; name aorta;}}
castellatedMeshControls {maxLocalCells 600000;maxGlobalCells 1200000;minRefinementCells 0;nCellsBetweenLevels 3;features (); refinementSurfaces {aorta {level (1 1);patchInfo {type wall;} regions {inlet {level (1 1);patchInfo {type patch;}} outlet {level (1 1);patchInfo {type patch;}} wall {level (1 1);patchInfo {type wall;}}}}} resolveFeatureAngle 30;refinementRegions {};locationInMesh (-0.002 0.027 -0.300);allowFreeStandingZoneFaces true;}
snapControls {nSmoothPatch 3;tolerance 2.0;nSolveIter 30;nRelaxIter 5;nFeatureSnapIter 10;implicitFeatureSnap true;explicitFeatureSnap false;multiRegionFeatureSnap false;}
addLayersControls {relativeSizes true;layers {"aorta_wall" {nSurfaceLayers 3;}} expansionRatio 1.2;finalLayerThickness 0.4;minThickness 0.08;nGrow 0;featureAngle 80;nRelaxIter 5;nSmoothSurfaceNormals 1;nSmoothNormals 3;nSmoothThickness 10;maxFaceThicknessRatio 0.5;maxThicknessToMedialRatio 0.3;minMedianAxisAngle 90;nBufferCellsNoExtrude 0;nLayerIter 50;nRelaxedIter 20;}
meshQualityControls {maxNonOrtho 65;maxBoundarySkewness 20;maxInternalSkewness 4;maxConcave 80;minVol 1e-15;minTetQuality 1e-20;minArea -1;minTwist 0.02;minDeterminant 0.001;minFaceWeight 0.02;minVolRatio 0.01;minTriangleTwist -1;nSmoothScale 4;errorReduction 0.75;relaxed {maxNonOrtho 75;}}
mergeTolerance 1e-6;
''';sn=sn.replace('addLayers true','addLayers false' if a.no_layers else 'addLayers true').replace('maxInternalSkewness 4',f'maxInternalSkewness {a.max_skew}').replace('tolerance 2.0',f'tolerance {a.snap_tolerance}');write(c,'system/snappyHexMeshDict',sn)
 write(c,'system/controlDict',f'''application pimpleFoam;startFrom latestTime;startTime 0;stopAt endTime;endTime {a.end};deltaT 0.002;writeControl adjustableRunTime;writeInterval 0.05;purgeWrite 41;writeFormat binary;writePrecision 8;writeCompression off;timeFormat general;timePrecision 8;runTimeModifiable true;adjustTimeStep yes;maxCo 0.7;maxDeltaT 0.005;functions {{}}''')
 write(c,'system/fvSchemes','''ddtSchemes {default backward;} gradSchemes {default Gauss linear;} divSchemes {default none;div(phi,U) bounded Gauss linearUpwind grad(U);div((nuEff*dev2(T(grad(U))))) Gauss linear;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;} wallDist {method meshWave;}''')
 write(c,'system/fvSolution','''solvers {p {solver GAMG;tolerance 1e-8;relTol 0.02;smoother GaussSeidel;} pFinal {$p;relTol 0;} U {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-8;relTol 0;} UFinal {$U;relTol 0;}} PIMPLE {nOuterCorrectors 2;nCorrectors 2;nNonOrthogonalCorrectors 1;momentumPredictor yes;} relaxationFactors {equations {U 0.9;}}''')
 write(c,'constant/transportProperties','transportModel Newtonian;nu [0 2 -1 0 0 0 0] 3.30188679245283e-6;');write(c,'constant/turbulenceProperties','simulationType laminar;')
 t=np.arange(0,20.001,.01);q=5e-5+3.5e-5*np.sin(2*np.pi*t);wave='\n'.join(f'({x:.6f} {y:.12g})' for x,y in zip(t,q))
 write(c,'0/U','dimensions [0 1 -1 0 0 0 0];internalField uniform (0 0 0);boundaryField {aorta_wall {type noSlip;} aorta_inlet {type flowRateInletVelocity;volumetricFlowRate table ('+wave+');extrapolateProfile false;value uniform (0 0 -0.03);} aorta_outlet {type pressureInletOutletVelocity;value uniform (0 0 0);} box {type zeroGradient;}}','volVectorField');write(c,'0/p','dimensions [0 2 -2 0 0 0 0];internalField uniform 0;boundaryField {aorta_wall {type zeroGradient;} aorta_inlet {type zeroGradient;} aorta_outlet {type fixedValue;value uniform 0;} box {type zeroGradient;}}','volScalarField');(c/'aorta.foam').touch();print('Built',c,flush=True)
if __name__=='__main__':main()
