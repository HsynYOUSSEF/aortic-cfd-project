"""Check the wall-shear-stress calculation of analyze_case.py on steady Poiseuille flow.

Builds a straight pipe (D = 10 mm, L = 300 mm) with the same snappyHexMesh settings style
(snapping + prism layers), solves steady laminar flow with OpenFOAM's simpleFoam, and
compares the computed WSS in the fully developed part with the exact value
tau = 4 mu Q / (pi R^3).

Usage (needs OpenFOAM v1912 binaries):  python cfd_v2/tests/pipe_wss_check.py /tmp/pipe_check
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_case  # noqa: E402

R, L, Q, MU, RHO = 0.005, 0.3, 2e-6, 0.0035, 1060.0  # m, m, m3/s, Pa s, kg/m3


def foam(path, body, cls='dictionary'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'FoamFile {{version 2.0; format ascii; class {cls}; object {path.name};}}\n{body}\n')


def stl(path, n=96, m=120):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    z = np.linspace(0, L, m)
    ring = lambda zz: np.c_[R * np.cos(th), R * np.sin(th), np.full(n, zz)]
    out = []

    def tri(name, a, b, c):
        nn = np.cross(b - a, c - a)
        nn /= np.linalg.norm(nn)
        out.append((name, nn, (a, b, c)))
    for k in range(m - 1):
        p, q = ring(z[k]), ring(z[k + 1])
        for i in range(n):
            j = (i + 1) % n
            tri('wall', p[i], p[j], q[j])
            tri('wall', p[i], q[j], q[i])
    for name, zz, sgn in [('inlet', 0.0, -1), ('outlet', L, 1)]:
        c, r = np.array([0, 0, zz]), ring(zz)
        for i in range(n):
            j = (i + 1) % n
            tri(name, c, r[j], r[i]) if sgn < 0 else tri(name, c, r[i], r[j])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for name in ['wall', 'inlet', 'outlet']:
            f.write(f'solid {name}\n')
            for nm, nn, ps in out:
                if nm == name:
                    f.write('facet normal %g %g %g\nouter loop\n' % tuple(nn))
                    for p in ps:
                        f.write('vertex %.9g %.9g %.9g\n' % tuple(p))
                    f.write('endloop\nendfacet\n')
            f.write(f'endsolid {name}\n')


def main(case):
    case = Path(case)
    if case.exists():
        raise SystemExit(f'{case} exists')
    stl(case / 'constant/triSurface/aorta.stl')
    h = 0.001
    lo, hi = np.array([-R - 0.001, -R - 0.001, -0.001]), np.array([R + 0.001, R + 0.001, L + 0.001])
    n = np.ceil((hi - lo) / h).astype(int)
    v = [(lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]), (hi[0], hi[1], lo[2]), (lo[0], hi[1], lo[2]),
         (lo[0], lo[1], hi[2]), (hi[0], lo[1], hi[2]), (hi[0], hi[1], hi[2]), (lo[0], hi[1], hi[2])]
    foam(case / 'system/blockMeshDict', 'convertToMeters 1; vertices (' + ' '.join('(%g %g %g)' % p for p in v) +
         '); blocks (hex (0 1 2 3 4 5 6 7) (%d %d %d) simpleGrading (1 1 1)); edges (); boundary (box {type patch; faces ((0 3 2 1)(4 5 6 7)(0 1 5 4)(3 7 6 2)(0 4 7 3)(1 2 6 5));}); mergePatchPairs ();' % tuple(n))
    # same snappy/layer style as build_case.py
    src = (HERE.parent / 'build_case.py').read_text()
    start = src.index("castellatedMesh true;")
    template = src[start:src.index("mergeTolerance 1e-6;") + len("mergeTolerance 1e-6;")]
    regions = 'wall {level (1 1); patchInfo {type wall;}} inlet {level (1 1); patchInfo {type patch;}} outlet {level (1 1); patchInfo {type patch;}}'
    sn = (template.replace('{{', '{').replace('}}', '}').replace('{regions}', regions)
          .replace('{a.layers}', '5').replace('"aorta_(wall|ext_.*)"', 'aorta_wall'))
    sn = sn.replace("{' '.join(f'{c:.9g}' for c in seed * 1e-3)}", f'0 0 {L / 2}')
    foam(case / 'system/snappyHexMeshDict', sn)
    U = Q / (np.pi * R ** 2)
    foam(case / '0/U', f'dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0); boundaryField {{ aorta_wall {{type noSlip;}} aorta_inlet {{type flowRateInletVelocity; volumetricFlowRate constant {Q}; value uniform (0 0 {U});}} aorta_outlet {{type zeroGradient;}} }}', 'volVectorField')
    foam(case / '0/p', 'dimensions [0 2 -2 0 0 0 0]; internalField uniform 0; boundaryField { aorta_wall {type zeroGradient;} aorta_inlet {type zeroGradient;} aorta_outlet {type fixedValue; value uniform 0;} }', 'volScalarField')
    foam(case / 'constant/transportProperties', f'transportModel Newtonian; nu [0 2 -1 0 0 0 0] {MU / RHO};')
    foam(case / 'constant/turbulenceProperties', 'simulationType laminar;')
    foam(case / 'system/controlDict', 'application simpleFoam; startFrom latestTime; startTime 0; stopAt endTime; endTime 2000; deltaT 1; writeControl timeStep; writeInterval 2000; writeFormat binary; functions {}')
    foam(case / 'system/fvSchemes', 'ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none; div(phi,U) bounded Gauss linearUpwind grad(U); div((nuEff*dev2(T(grad(U))))) Gauss linear;} laplacianSchemes {default Gauss linear limited corrected 0.5;} interpolationSchemes {default linear;} snGradSchemes {default limited corrected 0.5;}')
    foam(case / 'system/fvSolution', 'solvers { p {solver GAMG; tolerance 1e-9; relTol 0.05; smoother GaussSeidel;} U {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0.1;} } SIMPLE {nNonOrthogonalCorrectors 1; consistent yes; residualControl {p 1e-6; U 1e-7;}} relaxationFactors {equations {U 0.9;} fields {p 1;}}')
    env = dict(os.environ, WM_PROJECT_DIR=os.environ.get('WM_PROJECT_DIR', '/usr/share/openfoam'))
    env.setdefault('FOAM_ETC', env['WM_PROJECT_DIR'] + '/etc')
    for cmd in [['blockMesh'], ['snappyHexMesh', '-overwrite'], ['simpleFoam']]:
        with open(case / f'log.{cmd[0]}', 'w') as log:
            subprocess.run(cmd, cwd=case, stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
    last = max((p for p in case.iterdir() if p.is_dir() and p.name.replace('.', '').isdigit() and p.name != '0'),
               key=lambda p: float(p.name))
    wall = analyze_case.Wall(case)
    tau = np.linalg.norm(wall.wss(analyze_case.read_internal_vector(last / 'U'), MU), axis=1)
    zc = wall.cf[:, 2]
    dev = (zc > 0.5 * L) & (zc < 0.9 * L)  # developed region, away from the outlet
    exact = 4 * MU * Q / (np.pi * R ** 3)
    mean = float(np.average(tau[dev], weights=wall.area[dev]))
    report = {'exact_Pa': exact, 'computed_mean_Pa': mean, 'error_pct': 100 * (mean - exact) / exact,
              'computed_p5_p95_Pa': [float(np.percentile(tau[dev], 5)), float(np.percentile(tau[dev], 95))],
              'median_wall_cell_distance_mm': float(np.median(wall.d[dev]) * 1000),
              'Re': RHO * Q / (np.pi * R ** 2) * 2 * R / MU, 'solver_iterations_dir': last.name}
    (case / 'pipe_check.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/pipe_check')
