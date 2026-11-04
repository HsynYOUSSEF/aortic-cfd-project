"""Stream a synchronized side-by-side flow/WSS video from actual saved CFD snapshots."""
from pathlib import Path
import sys,json,subprocess,shutil,re,math
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy,numpy_to_vtk
WORK=Path('/tmp/aortic_exploratory_demo_20261018_01'); CASE=WORK/'cfd/aorta'
OUT=Path('/mnt/c/Users/Admin/Desktop/Aortic_Repaired_Simulation_20261015/deliverables/Aortic_Exploratory_SideBySide_20261018_01')
MOVIE=OUT/'Aortic_Exploratory_SideBySide_1080p.mp4'
if MOVIE.exists(): raise FileExistsError(MOVIE)
if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg not found')
sys.path.insert(0,str(WORK/'src'));import analyze_results as analysis
reader=analysis.reader(CASE);alltimes=vtk_to_numpy(reader.GetTimeValues()).astype(float)
times=alltimes[(alltimes>=.01-1e-8)&(alltimes<=3+1e-8)]
expected=np.round(np.arange(.01,3.0001,.01),8)
assert len(times)==300 and np.allclose(times,expected,atol=1e-7),f'expected 300 output snapshots, got {len(times)}'
# Verify source WSS units are kinematic; convert each vector to Pa exactly once using rho.
source_header=(CASE/'0.01/wallShearStress').read_bytes()[:1400]
assert re.search(rb'dimensions\s*\[\s*0\s+2\s+-2\s+0\s+0\s+0\s+0\s*\]',source_header), 'Unexpected source WSS units; refusing conversion'
rho=1060.0
Uall=[];Tauall=[];mesh0=None;wall0=None;wall_centres=None
centres=vtk.vtkCellCenters()
for t in times:
    mesh,patches=analysis.fields(reader,float(t))
    ua=mesh.GetCellData().GetArray('U');ta=patches['aorta_wall'].GetCellData().GetArray('wallShearStress')
    assert ua is not None and ta is not None, f'missing U/WSS at {t:g}'
    U=vtk_to_numpy(ua).astype(np.float32,copy=True)
    # Native field is m^2/s^2 (kinematic WSS); density applied once here -> Pa.
    Tau=vtk_to_numpy(ta).astype(np.float32,copy=True)*rho
    assert np.isfinite(U).all() and np.isfinite(Tau).all()
    if mesh0 is None:
        mesh0=vtk.vtkUnstructuredGrid();mesh0.DeepCopy(mesh)
        wall0=vtk.vtkPolyData();wall0.DeepCopy(patches['aorta_wall'])
        inlet=vtk.vtkPolyData();inlet.DeepCopy(patches['aorta_inlet'])
        centres.SetInputData(wall0);centres.Update();wall_centres=vtk_to_numpy(centres.GetOutput().GetPoints().GetData()).astype(float)
    else:
        assert mesh.GetNumberOfCells()==mesh0.GetNumberOfCells() and Tau.shape[0]==wall0.GetNumberOfCells()
    Uall.append(U);Tauall.append(Tau)
Uall=np.asarray(Uall,dtype=np.float32);Tauall=np.asarray(Tauall,dtype=np.float32)
Wmag=np.linalg.norm(Tauall,axis=2);measured_max=float(Wmag.max())
# One scale from the global maximum over all displayed computed snapshots; unchanged per frame.
scale_max=max(.1,math.ceil(measured_max*10-1e-10)/10)

# Identical orthographic projection, scale and view basis in each 960x1080 panel.
wp=vtk_to_numpy(wall0.GetPoints().GetData()).astype(float);az,el=np.deg2rad([-65.,8.])
right=np.array([-np.sin(az),np.cos(az),0]);up=np.array([-np.sin(el)*np.cos(az),-np.sin(el)*np.sin(az),np.cos(el)])
center=(wp.min(axis=0)+wp.max(axis=0))/2
projected=np.column_stack(((wall_centres-center)@right,(wall_centres-center)@up))
PW,H=960,1080;scale=min(700/max(np.ptp(projected[:,0]),1e-12),770/max(np.ptp(projected[:,1]),1e-12))
def project(x,panel):
    q=np.asarray(x)-center
    return np.column_stack((panel*PW+PW*.5+scale*(q@right),565-scale*(q@up)))
wallxy=np.rint(project(wall_centres,1)).astype(int)

# Inlet-weighted seeding and exact-snapshot Euler advection: no temporal field interpolation.
triangulate=vtk.vtkTriangleFilter();triangulate.SetInputData(inlet);triangulate.Update();tri=triangulate.GetOutput()
ip=vtk_to_numpy(tri.GetPoints().GetData());ids=np.array([[tri.GetCell(i).GetPointId(k) for k in range(3)] for i in range(tri.GetNumberOfCells())]);xyz=ip[ids]
weights=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1);weights/=weights.sum()
rng=np.random.default_rng(20261018);N=1400
def inject(n):
    v=xyz[rng.choice(len(xyz),n,p=weights)];s=np.sqrt(rng.random(n));b=rng.random(n)
    p=(1-s)[:,None]*v[:,0]+(s*(1-b))[:,None]*v[:,1]+(s*b)[:,None]*v[:,2];p[:,2]-=.0006;return p
pos=inject(N)
grid=vtk.vtkUnstructuredGrid();grid.DeepCopy(mesh0);grid.GetCellData().RemoveArray('U')
pts=vtk.vtkPoints();pts.SetDataTypeToDouble();cloud=vtk.vtkPolyData();cloud.SetPoints(pts)
probe=vtk.vtkProbeFilter();probe.SetInputData(cloud);probe.SetSourceData(grid);probe.SetComputeTolerance(False);probe.SetTolerance(1e-8)
def sample(U,x):
    arr=numpy_to_vtk(np.ascontiguousarray(U),deep=True);arr.SetName('U');grid.GetCellData().RemoveArray('U');grid.GetCellData().AddArray(arr);grid.Modified()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(x,dtype=np.float64),deep=True));pts.Modified();cloud.Modified();probe.Update()
    pd=probe.GetOutput().GetPointData();return vtk_to_numpy(pd.GetArray('U')).copy(),vtk_to_numpy(pd.GetArray('vtkValidPointMask')).astype(bool)

stops=np.array([[50,95,210],[0,195,225],[72,214,140],[245,198,61],[244,61,57]],dtype=np.float32)
def cmap(v,vmax):
    f=np.clip(v/max(vmax,1e-12),0,1)*4;k=np.minimum(f.astype(int),3);a=(f-k)[:,None]
    return (stops[k]*(1-a)+stops[k+1]*a).astype(np.uint8)
def scatter(img,xy,rgb,radius=1):
    x=xy[:,0];y=xy[:,1];ok=(x>=radius)&(x<PW*2-radius)&(y>=radius)&(y<H-radius);x=x[ok];y=y[ok];c=rgb[ok]
    for dy in range(-radius,radius+1):
      for dx in range(-radius,radius+1):
        if dx*dx+dy*dy<=radius*radius+.25:img[y+dy,x+dx]=c

# Fixed colorbar raster and fixed scale; frame composition stays in memory and is piped to FFmpeg.
OUT.mkdir(parents=True,exist_ok=True);W,H=1920,1080
movie_tmp=MOVIE.with_suffix('.partial.mp4')
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
shared_time="Simulation time\\: %{pts\\:hms} s"
filters=(f"drawbox=x=958:y=0:w=4:h=1080:color=0x71869AFF:t=fill,"
 f"drawtext=fontfile={font}:text='Exploratory transient CFD':fontcolor=white:fontsize=31:x=(w-text_w)/2:y=24:box=1:boxcolor=0x081422DD:boxborderw=8,"
 f"drawtext=fontfile={font}:text='Flow / particles - color = speed (m/s)':fontcolor=white:fontsize=21:x=35:y=102:box=1:boxcolor=0x081422CC:boxborderw=6,"
 f"drawtext=fontfile={font}:text='Wall shear stress — unvalidated coarse-mesh results':fontcolor=0xFFD0B0:fontsize=21:x=995:y=102:box=1:boxcolor=0x081422CC:boxborderw=6,"
 f"drawtext=fontfile={font}:text='{shared_time}':fontcolor=white:fontsize=25:x=(w-text_w)/2:y=70:box=1:boxcolor=0x081422EE:boxborderw=7,"
 f"drawtext=fontfile={font}:text='10x slowed playback | 300 actual computed snapshots | no replay or unsaved-field interpolation':fontcolor=0xD4E8F5:fontsize=17:x=(w-text_w)/2:y=1036:box=1:boxcolor=0x081422DD:boxborderw=5,"
 f"drawtext=fontfile={font}:text='Instantaneous WSS (Pa) | fixed scale':fontcolor=white:fontsize=17:x=1100:y=930,"
 f"drawtext=fontfile={font}:text='0':fontcolor=white:fontsize=16:x=1102:y=979,"
 f"drawtext=fontfile={font}:text='{scale_max/2:.2f}':fontcolor=white:fontsize=16:x=1431:y=979,"
 f"drawtext=fontfile={font}:text='{scale_max:.1f} Pa':fontcolor=white:fontsize=16:x=1740:y=979,"
 "setpts=(PTS-1)*10")
# Source frames arrive at 100 fps so their presentation timestamps equal simulated time.
# Draw the time label from those timestamps, then slow playback tenfold to 10 fps.
cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','100','-i','-','-vf','setpts=PTS+1,'+filters,'-fps_mode','vfr','-an','-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(movie_tmp)]
enc_log=(OUT/'encoding.log').open('wb');enc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=enc_log);valid_counts=[]
try:
  for i,(t,U,Tau) in enumerate(zip(times,Uall,Tauall)):
    frame=np.empty((H,W,3),dtype=np.uint8);frame[:]=[8,19,32]
    # faint identical vessel silhouette on left; instantaneous WSS points on right.
    leftxy=np.rint(project(wall_centres,0)).astype(int);shell=np.empty((len(leftxy),3),dtype=np.uint8);shell[:]=[52,102,130]
    scatter(frame,leftxy,shell,1)
    wxy=wallxy;scatter(frame,wxy,cmap(np.linalg.norm(Tau,axis=1),scale_max),2)
    # Fixed 0..scale_max Pa colorbar with tick marks, generated in memory per frame.
    bx0,bx1,by0,by1=1115,1805,958,974
    barx=np.arange(bx0,bx1)
    barvals=np.linspace(0,scale_max,len(barx),dtype=np.float32)
    frame[by0:by1,bx0:bx1]=cmap(barvals,scale_max)[None,:,:]
    for tick in (bx0,bx0+(bx1-bx0)//2,bx1-1):
      frame[by0-3:by1+3,tick-1:tick+1]=[255,255,255]
    vel,valid=sample(U,pos);valid_counts.append(int(valid.sum()))
    if i==0 and valid.sum()<N*.5:raise RuntimeError(f'Only {valid.sum()} of {N} particles sample inside the domain')
    pxy=np.rint(project(pos,0)).astype(int);scatter(frame,pxy[valid],cmap(np.linalg.norm(vel,axis=1)[valid],1.),2)
    enc.stdin.write(frame.tobytes())
    pos=pos+vel.astype(float)*.01
    out=(~valid)|(pos[:,2]<-.4199)
    if out.any():pos[out]=inject(int(out.sum()))
    if i%50==0:print(f'frame {i+1}/300; simulation t={t:.2f}s; WSS scale 0-{scale_max:.1f} Pa; particles={valid.sum()}',flush=True)
  enc.stdin.close();rc=enc.wait()
  if rc:raise RuntimeError(f'ffmpeg exited {rc}')
finally:
  if enc.poll() is None:enc.kill();enc.wait()
  enc_log.close()
# Validate stream before atomically promoting to the final durable path.
probe_result=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height,r_frame_rate,avg_frame_rate,nb_frames','-show_entries','format=duration','-of','json',str(movie_tmp)],capture_output=True,text=True,check=True)
meta=json.loads(probe_result.stdout);stream=next(x for x in meta['streams'] if x['codec_type']=='video')
avg_num,avg_den=map(int,stream['avg_frame_rate'].split('/'))
assert (int(stream['width']),int(stream['height']),int(stream['nb_frames']))==(1920,1080,300)
assert abs(avg_num/avg_den-10)<.05, f"unexpected encoded frame rate {stream['avg_frame_rate']}"
assert abs(float(meta['format']['duration'])-30)<.1
# Full decode validation.
subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie_tmp),'-f','null','-'],check=True)
movie_tmp.replace(MOVIE)
report={'status':'PASS','output':str(MOVIE),'resolution':[1920,1080],'nominal_playback_fps':10,'frames':300,'duration_s':float(meta['format']['duration']),'simulation_times_s':[.01,3.0],'playback':'10x slowed over the .01-to-3.00 s snapshot span; 0.01 s computed snapshot per frame','cycle_replay':'none','field_interpolation':'none; each frame samples computed snapshot at the same time; particle positions advanced using that snapshot over 0.01 s','camera':'same orthographic projection and basis for both panels','WSS_native_dimensions':'[0 2 -2 0 0 0 0] m2/s2 (kinematic)','density_kg_m3':rho,'density_conversion':'multiplied exactly once to Pa','fixed_color_scale_Pa':[0,scale_max],'observed_global_max_WSS_Pa':measured_max,'right_panel_label':'Wall shear stress — unvalidated coarse-mesh results','video_label':'Exploratory transient CFD','minimum_valid_particles':min(valid_counts),'ffprobe':meta}
(OUT/'render_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
