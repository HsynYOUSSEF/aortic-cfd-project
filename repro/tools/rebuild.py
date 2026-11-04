"""New portable driver around recovered sources; not the historical controller."""
import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2]


def command(args, log):
    with log.open('w') as stream:
        result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}); inspect {log}')


def prepare(work):
    if work.exists():
        raise FileExistsError(f'Refusing to overwrite {work}')
    work.mkdir(parents=True)
    for folder in ['src', 'geometry', 'data/repaired', 'reports', 'results', 'logs']:
        (work / folder).mkdir(parents=True, exist_ok=True)
    for file in (PACKAGE / 'repro/recovered').glob('*.py'):
        shutil.copy2(file, work / 'src' / file.name)
    for name in ['REPAIRED_surface_RAS_mm.vtp']:
        shutil.copy2(PACKAGE / 'geometry' / name, work / 'geometry' / name)
    shutil.copy2(PACKAGE / 'data/repaired/GREEN_REPAIRED_RESEARCH.nrrd',
                 work / 'data/repaired/GREEN_REPAIRED_RESEARCH.nrrd')
    template = work / 'src/_dictionary_template.py'
    template.write_text(template.read_text().replace(
        'results/pilot/surface_smooth10_RAS_mm.vtp', 'geometry/REPAIRED_surface_RAS_mm.vtp'))
    config = dict(case_name='aorta', end_time_s=3.0, base_cell_mm=2.0,
                  write_interval_s=0.01, density_kg_m3=1060, viscosity_Pa_s=0.0035,
                  cycle_period_s=1.0, inlet_Q_m3_s='5e-5 + 3.5e-5*sin(2*pi*t)',
                  outlet_model='Two independent zero kinematic gauge pressure outlets',
                  provenance='New reconstruction of setup from recovered source; not exact historical replay')
    (work / 'run_config.json').write_text(json.dumps(config, indent=2))
    command([sys.executable, str(work / 'src/prepare_case.py')], work / 'logs/prepare.log')
    case = work / 'cfd/aorta'
    path = case / 'system/snappyHexMeshDict'
    text = path.read_text().replace('snap true', 'snap false').replace('addLayers true', 'addLayers false')
    text = text.replace('refinementRegions {};',
                        'refinementRegions {aorta {mode inside;levels ((1e15 1));}};')
    path.write_text(text)
    path = case / 'system/controlDict'
    text = path.read_text()
    for key, value in {'maxDeltaT': '0.0002', 'deltaT': '0.0002', 'maxCo': '0.7'}.items():
        text, count = re.subn(r'\b' + key + r'\s+[^;]+;', key + ' ' + value + ';', text)
        if count != 1:
            raise RuntimeError(f'Ambiguous dictionary entry {key}')
    path.write_text(text)
    # A portable copy of the renderer retains the actual-field and unit checks.
    render = (PACKAGE / 'runs/runtime_optimization_20261018_01/src/render_side_by_side.py').read_text()
    render = re.sub(r"WORK=Path\([^\n]+", "WORK=Path(__file__).resolve().parents[1]; CASE=WORK/'cfd/aorta'", render, count=1)
    render = re.sub(r"OUT=Path\([^\n]+", "OUT=WORK/'video'", render, count=1)
    (work / 'src/render_side_by_side.py').write_text(render)
    import numpy, scipy, vtk
    files = {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(work.rglob('*')) if p.is_file()}
    (work / 'reports/preparation.json').write_text(json.dumps({
        'status': 'PREPARED_NOT_MESHED_OR_SOLVED',
        'python': sys.version, 'platform': platform.platform(),
        'numpy': numpy.__version__, 'scipy': scipy.__version__, 'vtk': vtk.vtkVersion.GetVTKVersion(),
        'input_and_setup_sha256': files,
        'warning': 'Mesh cell count and fields may differ from the published demonstration.'}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['prepare', 'mesh', 'solve', 'analyze', 'video'])
    ap.add_argument('work', type=Path, help='New run root, e.g. /home/user/aortic-runs/my_run_01')
    a = ap.parse_args(); work = a.work.resolve(); case = work / 'cfd/aorta'
    if a.stage == 'prepare':
        prepare(work)
    else:
        if not (work / 'reports/preparation.json').is_file():
            raise RuntimeError('Prepare this run first')
        if a.stage == 'mesh':
            if (case / 'constant/polyMesh').exists():
                raise RuntimeError('Existing mesh preserved; prepare a new run to remesh')
            for exe, extra in [('blockMesh', []), ('snappyHexMesh', ['-overwrite']),
                               ('checkMesh', ['-allTopology', '-allGeometry'])]:
                command([exe, '-case', str(case), *extra], work / 'logs' / (exe + '.log'))
            command([sys.executable, str(work / 'src/check_mesh_gate.py'),
                     str(work / 'logs/checkMesh.log')], work / 'logs/mesh_gate.log')
        elif a.stage == 'solve':
            gate = json.loads((work / 'reports/mesh_check.json').read_text())
            if gate['status'] != 'PASS':
                raise RuntimeError('Mesh gate failed')
            if (work / 'logs/pimpleFoam.log').exists():
                raise RuntimeError('A solve was already attempted. Preserve it; use a fresh run.')
            command(['pimpleFoam', '-case', str(case)], work / 'logs/pimpleFoam.log')
            if not (case / '3/U').is_file():
                raise RuntimeError('Final 3 s velocity field is missing')
            command(['pimpleFoam', '-case', str(case), '-postProcess', '-func',
                     'wallShearStress', '-time', '0.01:3'], work / 'logs/wallShearStress.log')
        elif a.stage == 'analyze':
            if (work / 'results/aorta').exists():
                raise RuntimeError('Existing analysis preserved; use a fresh run')
            command([sys.executable, str(work / 'src/analyze_results.py')], work / 'logs/analysis.log')
            command([sys.executable, str(PACKAGE / 'repro/tools/check_periodicity.py'), str(work)],
                    work / 'logs/phase_periodicity.log')
        elif a.stage == 'video':
            (work / 'video').mkdir(exist_ok=True)
            command([sys.executable, str(work / 'src/render_side_by_side.py')], work / 'logs/video.log')
    print(f'Completed {a.stage}: {work}')


if __name__ == '__main__':
    main()
