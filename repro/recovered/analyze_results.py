"""Read the executed two-outlet case and calculate WSS/conservation summaries."""
from pathlib import Path
import json,re
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy,numpy_to_vtk
ROOT=Path(__file__).resolve().parents[1]

def reader(case):
 r=vtk.vtkOpenFOAMReader();r.SetFileName(str(case/'aorta.foam'));r.UpdateInformation();r.EnableAllPatchArrays();r.EnableAllCellArrays();return r

def fields(r,t):
 r.UpdateTimeStep(float(t));output=r.GetOutput();datasets={}
 def visit(block):
  for i in range(block.GetNumberOfBlocks()):
   obj=block.GetBlock(i)
   if obj is None:continue
   name=block.GetMetaData(i).Get(vtk.vtkCompositeDataSet.NAME()) or f'block{i}'
   if obj.IsA('vtkMultiBlockDataSet'):visit(obj)
   elif obj.IsA('vtkDataSet'):datasets[name]=obj
 visit(output)
 internal=datasets.get('internalMesh')
 if internal is None:raise RuntimeError(f'Internal mesh missing; found {list(datasets)}')
 return internal,datasets

def areas(poly):
 f=vtk.vtkCellSizeFilter();f.SetInputData(poly);f.Update();return vtk_to_numpy(f.GetOutput().GetCellData().GetArray('Area'))

def patch_flux(path,patch,count):
 b=path.read_bytes();start=b.index(patch.encode());part=b[start:b.index(b'}',start)+1];match=re.search(rb'value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(',part)
 if match:
  n=int(match[1]);assert n==count,(patch,n,count);offset=start+match.end()
  if re.search(rb'format\s+binary\s*;',b[:1000]):
   assert b'LSB' in b[:1000] and b'scalar=64' in b[:1000], 'Unsupported phi binary architecture'
   if b[offset+n*8:offset+n*8+4].lstrip()[:1]!=b')':
    assert b[offset:offset+1]==b'\n';offset+=1
   assert b[offset+n*8:offset+n*8+4].lstrip()[:1]==b')','Binary phi list offset mismatch'
   return float(np.frombuffer(b,dtype='<f8',count=n,offset=offset).sum())
  close=b.index(b')',offset);values=np.fromstring(b[offset:close].decode(),sep=' ');assert len(values)==n;return float(values.sum())
 uniform=re.search(rb'value\s+uniform\s+([^;]+);',part);assert uniform,f'No phi values for {patch}'
 return float(uniform[1])*count

def main():
 cfg=json.loads((ROOT/'run_config.json').read_text());case=ROOT/'cfd'/cfg['case_name'];out=ROOT/'results'/cfg['case_name'];out.mkdir(exist_ok=True)
 end=float(cfg['end_time_s']);rho=cfg['density_kg_m3'];r=reader(case);all_times=vtk_to_numpy(r.GetTimeValues());times=all_times[(all_times>=end-2-1e-7)&(all_times<=end+1e-7)]
 assert len(times)>=41 and abs(times[-1]-end)<1e-6,'Missing final two cycles'
 directories={float(p.name):p for p in case.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name)}
 series=[];stresses=[];wall=None
 for t in times:
  mesh,blocks=fields(r,t);wall=blocks['aorta_wall'];wa=areas(wall);velocity=vtk_to_numpy(mesh.GetCellData().GetArray('U'));arr=wall.GetCellData().GetArray('wallShearStress');assert arr is not None,f'No WSS at {t}'
  folder=directories[min(directories,key=lambda v:abs(v-t))];header=(folder/'wallShearStress').read_bytes()[:1500];assert re.search(rb'dimensions\s*\[\s*0\s+2\s+-2\s+0\s+0\s+0\s+0\s*\]',header),'Unexpected WSS dimensions'
  tau=vtk_to_numpy(arr).astype(float)*rho;stresses.append(tau)
  names=['aorta_inlet','aorta_outlet1','aorta_outlet2'];flux=[patch_flux(folder/'phi',name,blocks[name].GetNumberOfCells()) for name in names]
  pressures=[float(np.average(vtk_to_numpy(blocks[name].GetCellData().GetArray('p')),weights=areas(blocks[name]))*rho) for name in names]
  qin=-flux[0];qout=flux[1]+flux[2];outpressure=np.average(pressures[1:],weights=[areas(blocks[n]).sum() for n in names[1:]])
  series.append([t,qin,flux[1],flux[2],qout,pressures[0]-outpressure,np.linalg.norm(velocity,axis=1).max(),np.average(np.linalg.norm(tau,axis=1),weights=wa)])
  if t>=end-1-1e-7:
   export=vtk.vtkPolyData();export.DeepCopy(wall);a=numpy_to_vtk(tau,deep=True);a.SetName('WSS_Pa');export.GetCellData().AddArray(a);w=vtk.vtkXMLPolyDataWriter();w.SetFileName(str(out/f'wall_{t:g}.vtp'));w.SetInputData(export);assert w.Write()==1
 d=np.array(series);tau=np.array(stresses);sel=times>=end-1-1e-7;t=times[sel];x=tau[sel];duration=t[-1]-t[0];assert abs(duration-1)<1e-6
 taw=np.trapezoid(np.linalg.norm(x,axis=2),t,axis=0)/duration;mean=np.linalg.norm(np.trapezoid(x,t,axis=0)/duration,axis=1);osi=np.clip(.5*(1-np.divide(mean,taw,out=np.full_like(mean,np.nan),where=taw>1e-12)),0,.5);rrt=np.divide(1.,mean,out=np.full_like(mean,np.inf),where=mean>1e-12)
 exported=vtk.vtkPolyData();exported.DeepCopy(wall)
 for name,values in [('TAWSS_Pa',taw),('OSI',osi),('RRT_Pa_inverse',rrt)]:
  a=numpy_to_vtk(values,deep=True);a.SetName(name);exported.GetCellData().AddArray(a)
 w=vtk.vtkXMLPolyDataWriter();w.SetFileName(str(out/'wall_metrics.vtp'));w.SetInputData(exported);assert w.Write()==1
 prev=np.array([np.argmin(abs(times-(z-1))) for z in t]);assert np.allclose(times[prev],t-1,atol=1e-6);prior=np.trapezoid(np.linalg.norm(tau[prev],axis=2),t,axis=0);den=np.sqrt(np.average(taw*taw,weights=wa));cycle=float(np.sqrt(np.average((taw-prior)**2,weights=wa))/den) if den else None
 imbalance=float(np.max(abs(d[:,1]-d[:,4])/np.maximum(abs(d[:,1]),1e-12)));expected=5e-5+3.5e-5*np.sin(2*np.pi*d[:,0]);flow_error=float(np.max(abs(d[:,1]-expected)/expected))
 summary={'case':cfg['case_name'],'cells':mesh.GetNumberOfCells(),'cycle_s':[float(t[0]),float(t[-1])],'mean_TAWSS_Pa':float(np.average(taw,weights=wa)),'area_mean_OSI':float(np.average(osi[np.isfinite(osi)],weights=wa[np.isfinite(osi)])),'max_relative_flow_imbalance':imbalance,'max_relative_inlet_waveform_error':flow_error,'TAWSS_cycle_relative_L2':cycle,'mean_outlet1_fraction':float(np.mean(d[sel,2]/d[sel,4])),'peak_speed_m_s':float(d[sel,6].max()),'density_kg_m3':rho,'stress_units':'Kinematic wallShearStress multiplied once by density to Pa; RRT is Pa^-1','conservation_under_0_5_percent':imbalance<.005,'cycle_change_under_5_percent':cycle is not None and cycle<.05,'interpretation':'Executed exploratory CFD with inferred alignment, repaired geometry, synthetic inflow and two zero-pressure outlets. Not patient-validated; mesh convergence not established.'}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));np.savetxt(out/'time_series.csv',d,delimiter=',',header='time_s,inflow_m3_s,outlet1_m3_s,outlet2_m3_s,total_outflow_m3_s,pressure_drop_Pa,max_speed_m_s,mean_WSS_Pa',comments='');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
