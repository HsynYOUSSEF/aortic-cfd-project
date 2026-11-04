from pathlib import Path
import json,re,sys
from analyze_results import ROOT
log=Path(sys.argv[1]);text=log.read_text(errors='replace');cfg=json.loads((ROOT/'run_config.json').read_text());case=ROOT/'cfd'/cfg['case_name'];boundary=(case/'constant/polyMesh/boundary').read_text(errors='replace')
required=['aorta_wall','aorta_inlet','aorta_outlet1','aorta_outlet2'];counts={}
for name in required:
 m=re.search(r'\b'+name+r'\s*\{([^}]*)\}',boundary,re.S);assert m,f'Missing patch {name}';n=re.search(r'\bnFaces\s+(\d+)',m[1]);assert n;counts[name]=int(n[1]);assert counts[name]>0,f'Empty patch {name}'
box=re.search(r'\bbox\s*\{([^}]*)\}',boundary,re.S)
if box:
 n=re.search(r'\bnFaces\s+(\d+)',box[1]);assert n and int(n[1])==0,'Retained outer-box faces: mesh may be outside the vessel'
passed='Mesh OK.' in text and not re.search(r'Failed\s+[1-9]\d*\s+mesh checks|FOAM FATAL',text,re.I)
report={'status':'PASS' if passed else 'FAIL','checkMesh_log':str(log),'patch_faces':counts,'interpretation':'Mesh checks do not establish grid-converged WSS or anatomical accuracy.'};(ROOT/'reports/mesh_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if passed else 1)
