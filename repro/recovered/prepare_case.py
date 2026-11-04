"""Prepare a new two-outlet research case. Never edits another project's cases."""
from pathlib import Path
import gzip,json,re,subprocess,sys
import numpy as np
from scipy import ndimage as ndi
import vtk
from vtk.util.numpy_support import vtk_to_numpy
ROOT=Path(__file__).resolve().parents[1]

def topology(poly):
 edges=vtk.vtkExtractEdges();edges.SetInputData(poly);edges.Update()
 result={'points':poly.GetNumberOfPoints(),'triangles':poly.GetNumberOfCells(),'edges':edges.GetOutput().GetNumberOfCells()}
 for name,boundary,nonmanifold in [('boundary_edges',True,False),('nonmanifold_edges',False,True)]:
  f=vtk.vtkFeatureEdges();f.SetInputData(poly);f.FeatureEdgesOff();f.ManifoldEdgesOff();f.SetBoundaryEdges(boundary);f.SetNonManifoldEdges(nonmanifold);f.Update();result[name]=f.GetOutput().GetNumberOfCells()
 c=vtk.vtkPolyDataConnectivityFilter();c.SetInputData(poly);c.SetExtractionModeToAllRegions();c.Update();result['surface_regions']=c.GetNumberOfExtractedRegions();result['Euler']=result['points']-result['edges']+result['triangles']
 return result

def groups(triangles,indices):
 parent={int(i):int(i) for i in indices};owners={}
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i in indices:
  i=int(i)
  for point in triangles[i]:
   if point in owners:parent[find(i)]=find(owners[point])
   else:owners[point]=i
 result={}
 for i in indices:result.setdefault(find(int(i)),[]).append(int(i))
 return list(result.values())

def foamfile(path,body,cls='dictionary'):
 path.write_text(f'FoamFile {{version 2.0; format ascii; class {cls}; object {path.name};}}\n'+body)

def main():
 cfg=json.loads((ROOT/'run_config.json').read_text());case=ROOT/'cfd'/cfg['case_name']
 if case.exists():raise RuntimeError(f'Refusing to overwrite existing case: {case}')
 subprocess.run([sys.executable,str(ROOT/'src/_dictionary_template.py'),'--name',cfg['case_name'],'--cell-mm',str(cfg['base_cell_mm']),'--end',str(cfg['end_time_s'])],check=True)
 r=vtk.vtkXMLPolyDataReader();r.SetFileName(str(ROOT/'geometry/REPAIRED_surface_RAS_mm.vtp'));r.Update()
 planes=vtk.vtkPlaneCollection()
 for z,normal in [(-420,(0,0,1)),(-240,(0,0,-1))]:
  plane=vtk.vtkPlane();plane.SetOrigin(0,0,z);plane.SetNormal(*normal);planes.AddItem(plane)
 clip=vtk.vtkClipClosedSurface();clip.SetInputData(r.GetOutput());clip.SetClippingPlanes(planes);clip.SetGenerateFaces(True);clip.Update()
 tri=vtk.vtkTriangleFilter();tri.SetInputConnection(clip.GetOutputPort());tri.Update();clean=vtk.vtkCleanPolyData();clean.SetInputConnection(tri.GetOutputPort());clean.SetTolerance(0);clean.Update()
 normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(clean.GetOutputPort());normals.SplittingOff();normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.Update();poly=normals.GetOutput()
 pts=vtk_to_numpy(poly.GetPoints().GetData()).astype(float)*.001;faces=vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1,4)[:,1:];xyz=pts[faces]
 upper=np.flatnonzero(np.max(abs(xyz[:,:,2]+.240),axis=1)<1e-9);lower=np.flatnonzero(np.max(abs(xyz[:,:,2]+.420),axis=1)<1e-9)
 upper_groups=groups(faces,upper);lower_groups=groups(faces,lower)
 assert len(upper_groups)==1 and len(lower_groups)==2, (len(upper_groups),len(lower_groups))
 lower_groups.sort(key=lambda ids:float(xyz[ids,:,0].mean()))
 labels=np.full(len(faces),'wall',dtype='<U12');labels[upper]='inlet'
 for i,ids in enumerate(lower_groups,1):labels[ids]=f'outlet{i}'
 areas=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)/2
 assert np.all(areas>1e-18),'Degenerate triangles'
 stats={}
 with (case/'constant/triSurface/aorta.stl').open('w') as f:
  for name in ['wall','inlet','outlet1','outlet2']:
   sel=labels==name;sub=xyz[sel];stats[name]={'triangles':int(sel.sum()),'area_m2':float(areas[sel].sum()),'centroid_RAS_m':np.average(sub.mean(1),axis=0,weights=areas[sel]).tolist()};f.write(f'solid {name}\n')
   for points in sub:
    n=np.cross(points[1]-points[0],points[2]-points[0]);n/=np.linalg.norm(n);f.write('facet normal '+' '.join(f'{v:.12g}' for v in n)+'\nouter loop\n')
    for p in points:f.write('vertex '+' '.join(f'{v:.12g}' for v in p)+'\n')
    f.write('endloop\nendfacet\n')
   f.write(f'endsolid {name}\n')
 # Export the exact clipped surface with patch labels, in SI units.
 p=vtk.vtkPolyData();p.DeepCopy(poly)
 for i,point in enumerate(pts):p.GetPoints().SetPoint(i,*point)
 wr=vtk.vtkXMLPolyDataWriter();wr.SetFileName(str(ROOT/'geometry/CFD_surface_SI.vtp'));wr.SetInputData(p);assert wr.Write()==1
 raw=(ROOT/'data/repaired/GREEN_REPAIRED_RESEARCH.nrrd').read_bytes();header,payload=raw.split(b'\n\n',1);header=header.decode();sizes=list(map(int,re.search(r'^sizes: (.*)$',header,re.M)[1].split()));mask=np.frombuffer(gzip.decompress(payload),np.uint8).reshape(sizes[::-1])>0
 directions=re.search(r'^space directions: (.*)$',header,re.M)[1];columns=[list(map(float,s.split(','))) for s in re.findall(r'\(([^)]+)\)',directions)];matrix=np.eye(4);matrix[:3,:3]=np.array(columns).T;matrix[:3,3]=list(map(float,re.search(r'^space origin: \(([^)]+)\)',header,re.M)[1].split(',')))
 sp=np.linalg.norm(matrix[:3,:3],axis=0)[::-1];distance=ndi.distance_transform_edt(mask,sampling=sp);z=matrix[2,3]+np.arange(mask.shape[0])*matrix[2,2];distance[(z>=-245)|(z<=-415)]=0;k,j,i=np.unravel_index(distance.argmax(),distance.shape);seed=(matrix@np.array([i,j,k,1]))[:3]*.001
 sn=(case/'system/snappyHexMeshDict').read_text();sn=sn.replace('outlet {level (1 1);patchInfo {type patch;}}','outlet1 {level (1 1);patchInfo {type patch;}} outlet2 {level (1 1);patchInfo {type patch;}}');sn=re.sub(r'locationInMesh\s*\([^)]*\)', 'locationInMesh ('+' '.join(f'{x:.12g}' for x in seed)+')',sn);(case/'system/snappyHexMeshDict').write_text(sn)
 lo=pts.min(0)-.006;hi=pts.max(0)+.006;n=np.ceil((hi-lo)/(cfg['base_cell_mm']*.001)).astype(int);verts=[(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),(hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),(lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
 foamfile(case/'system/blockMeshDict','convertToMeters 1; vertices ('+' '.join('('+' '.join(map(str,p))+')' for p in verts)+'); blocks (hex (0 1 2 3 4 5 6 7) ('+' '.join(map(str,n))+') simpleGrading (1 1 1)); edges (); boundary (box {type patch; faces ((0 3 2 1)(4 5 6 7)(0 1 5 4)(3 7 6 2)(0 4 7 3)(1 2 6 5));}); mergePatchPairs ();')
 for name in ['U','p']:
  text=(case/'0'/name).read_text();pattern=r'aorta_outlet\s*\{([^{}]*)\}';match=re.search(pattern,text);assert match;text=re.sub(pattern,lambda _: 'aorta_outlet1 {'+match[1]+'} aorta_outlet2 {'+match[1]+'}',text);(case/'0'/name).write_text(text)
 t=np.arange(0,cfg['end_time_s']+.005,.01);wave='\n'.join(f'({x:.6f} {5e-5+3.5e-5*np.sin(2*np.pi*x):.12g})' for x in t)
 path=case/'0/U';text=path.read_text();text,count=re.subn(r'volumetricFlowRate table \(.*?\);','volumetricFlowRate table (\n'+wave+'\n);',text,flags=re.S);assert count==1;path.write_text(text)
 path=case/'system/controlDict';text=path.read_text().replace('purgeWrite 41','purgeWrite 0');text=re.sub(r'writeInterval\s+[^;]+;',f"writeInterval {cfg['write_interval_s']};",text);path.write_text(text)
 report={'status':'PREPARED_NOT_MESHED_OR_SOLVED','units':'metres','cuts_RAS_mm':[-420,-240],'patches':stats,'topology':topology(poly),'locationInMesh_RAS_m':seed.tolist(),'seed_distance_from_voxel_boundary_mm':float(distance[k,j,i]),'inlet_waveform':cfg['inlet_Q_m3_s'],'outlet_assumption':cfg['outlet_model'],'side_boundaries':'Other closed reconstructed surface is treated as rigid wall; no additional side-branch outlet flow is modeled.'}
 assert report['topology']['boundary_edges']==0 and report['topology']['nonmanifold_edges']==0
 (case/'geometry_provenance.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/case_preparation.json').write_text(json.dumps(report,indent=2));cfg['run_status']='PREPARED_NOT_MESHED_OR_SOLVED';(ROOT/'run_config.json').write_text(json.dumps(cfg,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
