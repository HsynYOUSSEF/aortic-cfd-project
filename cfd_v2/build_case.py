"""Build an OpenFOAM (v1912) aneurysm case with a wall-resolving mesh.

Changes compared with the pilot runs:
  * flow extensions on the inlet and every outlet (length = k x equivalent diameter)
  * snappyHexMesh with snapping ON and prism layers on the vessel wall
  * inflow waveform read from a CSV file (one cardiac cycle), repeated for N cycles
  * outlet flow split set explicitly (Murray's law by default) instead of two
    zero-pressure outlets whose split is uncontrolled

Input surface: closed STL/VTP in RAS millimetres (as exported from 3D Slicer).
The vessel is cut by two planes normal to z: one inlet plane and one outlet plane
crossing both iliac arteries. Output: a new OpenFOAM case folder (never overwritten).

Example:
  python cfd_v2/build_case.py geometry/REPAIRED_surface_RAS_mm.vtp runs/v2_test/cfd \
      --inlet-z -240 --outlet-z -420 --cell-mm 1.2 --waveform cfd_v2/inflow_waveform.csv
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk, numpy_to_vtkIdTypeArray


# ---------------------------------------------------------------- geometry
def smooth_surface(poly, iterations, passband=0.1):
    """Windowed-sinc smoothing (volume-preserving, removes voxel staircase). 0 = off."""
    if iterations <= 0:
        return poly
    f = vtk.vtkWindowedSincPolyDataFilter()
    f.SetInputData(poly)
    f.SetNumberOfIterations(iterations)
    f.SetPassBand(passband)
    f.BoundarySmoothingOff()
    f.FeatureEdgeSmoothingOff()
    f.NonManifoldSmoothingOn()
    f.NormalizeCoordinatesOn()
    f.Update()
    out = vtk.vtkPolyData()
    out.DeepCopy(f.GetOutput())
    return out


def displacement_mm(before, after):
    a = vtk_to_numpy(before.GetPoints().GetData())
    b = vtk_to_numpy(after.GetPoints().GetData())
    d = np.linalg.norm(a - b, axis=1)
    return {'p50': float(np.percentile(d, 50)), 'p95': float(np.percentile(d, 95)), 'max': float(d.max())}


def read_surface(path):
    path = Path(path)
    reader = vtk.vtkSTLReader() if path.suffix.lower() == '.stl' else vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    conn = vtk.vtkPolyDataConnectivityFilter()
    conn.SetInputConnection(reader.GetOutputPort())
    conn.SetExtractionModeToLargestRegion()
    tri = vtk.vtkTriangleFilter()
    tri.SetInputConnection(conn.GetOutputPort())
    clean = vtk.vtkCleanPolyData()
    clean.SetInputConnection(tri.GetOutputPort())
    clean.Update()
    return clean.GetOutput()


def clip_and_cap(poly, z_in, z_out):
    planes = vtk.vtkPlaneCollection()
    for z, normal in [(z_out, (0, 0, 1)), (z_in, (0, 0, -1))]:
        plane = vtk.vtkPlane()
        plane.SetOrigin(0, 0, z)
        plane.SetNormal(*normal)
        planes.AddItem(plane)
    clip = vtk.vtkClipClosedSurface()
    clip.SetInputData(poly)
    clip.SetClippingPlanes(planes)
    clip.SetGenerateFaces(True)
    tri = vtk.vtkTriangleFilter()
    tri.SetInputConnection(clip.GetOutputPort())
    clean = vtk.vtkCleanPolyData()
    clean.SetInputConnection(tri.GetOutputPort())
    clean.SetTolerance(0)
    clean.Update()
    out = clean.GetOutput()
    pts = vtk_to_numpy(out.GetPoints().GetData()).astype(float)
    faces = vtk_to_numpy(out.GetPolys().GetData()).reshape(-1, 4)[:, 1:].astype(np.int64)
    return pts, faces


def face_groups(faces, ids):
    """Split a set of triangles into edge/vertex-connected groups."""
    parent = {int(i): int(i) for i in ids}
    owner = {}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in ids:
        for p in faces[i]:
            p = int(p)
            if p in owner:
                parent[find(int(i))] = find(owner[p])
            else:
                owner[p] = int(i)
    groups = {}
    for i in ids:
        groups.setdefault(find(int(i)), []).append(int(i))
    return list(groups.values())


def tri_areas(pts, faces):
    xyz = pts[faces]
    return np.linalg.norm(np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0]), axis=1) / 2


def extrude_cap(pts, faces, labels, cap_ids, direction, length, cap_label, side_label):
    """Move a planar cap by `length` along `direction`; join it to the vessel with a tube."""
    cap = faces[cap_ids]
    edges = {}
    for a, b, c in cap:
        for e in [(a, b), (b, c), (c, a)]:
            key = tuple(sorted(e))
            edges.setdefault(key, []).append(e)
    boundary = [v[0] for v in edges.values() if len(v) == 1]
    cap_vertices = np.unique(cap)
    new_index = {}
    new_pts = []
    for v in cap_vertices:
        new_index[int(v)] = len(pts) + len(new_pts)
        new_pts.append(pts[v] + direction * length)
    pts = np.vstack([pts, np.array(new_pts)])
    moved_cap = np.vectorize(lambda v: new_index[int(v)])(cap)
    side = []
    for a, b in boundary:
        a2, b2 = new_index[int(a)], new_index[int(b)]
        side += [(a, b, b2), (a, b2, a2)]
    keep = np.ones(len(faces), bool)
    keep[cap_ids] = False
    faces = np.vstack([faces[keep], moved_cap, np.array(side)])
    labels = np.concatenate([labels[keep], np.full(len(moved_cap), cap_label, dtype=labels.dtype),
                             np.full(len(side), side_label, dtype=labels.dtype)])
    return pts, faces, labels


def to_polydata(pts, faces, labels):
    poly = vtk.vtkPolyData()
    p = vtk.vtkPoints()
    p.SetData(numpy_to_vtk(pts, deep=True))
    poly.SetPoints(p)
    cells = np.hstack([np.full((len(faces), 1), 3), faces]).astype(np.int64).ravel()
    arr = vtk.vtkCellArray()
    arr.SetCells(len(faces), numpy_to_vtkIdTypeArray(cells, deep=True))
    poly.SetPolys(arr)
    names = sorted(set(labels))
    code = vtk.vtkIntArray()
    code.SetName('region')
    for lab in labels:
        code.InsertNextValue(names.index(lab))
    poly.GetCellData().AddArray(code)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.ComputeCellNormalsOn()
    normals.Update()
    out = normals.GetOutput()
    reg = vtk_to_numpy(out.GetCellData().GetArray('region'))
    f = vtk_to_numpy(out.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    return out, f, np.array([names[i] for i in reg])


def topology(poly):
    result = {}
    for name, boundary, nonmanifold in [('boundary_edges', True, False), ('nonmanifold_edges', False, True)]:
        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(poly)
        fe.FeatureEdgesOff()
        fe.ManifoldEdgesOff()
        fe.SetBoundaryEdges(boundary)
        fe.SetNonManifoldEdges(nonmanifold)
        fe.Update()
        result[name] = fe.GetOutput().GetNumberOfCells()
    return result


def inside(poly, point):
    pts = vtk.vtkPoints()
    pts.InsertNextPoint(*point)
    probe = vtk.vtkPolyData()
    probe.SetPoints(pts)
    sel = vtk.vtkSelectEnclosedPoints()
    sel.SetInputData(probe)
    sel.SetSurfaceData(poly)
    sel.SetTolerance(1e-6)
    sel.Update()
    return bool(sel.IsInside(0))


# ---------------------------------------------------------------- OpenFOAM files
def foam(path, body, cls='dictionary'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'FoamFile {{version 2.0; format ascii; class {cls}; object {path.name};}}\n' + body + '\n')


def read_waveform(path):
    t, q = [], []
    with open(path) as f:
        rows = [r for r in csv.reader(f) if r and not r[0].lstrip().startswith('#')]
    header = [h.strip() for h in rows[0]]
    if header[:2] != ['t_s', 'Q_mL_s']:
        raise ValueError('Waveform CSV must start with the columns t_s,Q_mL_s')
    for r in rows[1:]:
        t.append(float(r[0]))
        q.append(float(r[1]))
    t, q = np.array(t), np.array(q) * 1e-6
    if t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError('Waveform times must start at 0 and increase')
    return t, q


def write_stl(path, pts_m, faces, labels, order):
    path.parent.mkdir(parents=True, exist_ok=True)
    xyz = pts_m[faces]
    with path.open('w') as out:
        for name in order:
            out.write(f'solid {name}\n')
            for tri in xyz[labels == name]:
                n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                n = n / np.linalg.norm(n)
                out.write('facet normal ' + ' '.join(f'{v:.10g}' for v in n) + '\nouter loop\n')
                for p in tri:
                    out.write('vertex ' + ' '.join(f'{v:.10g}' for v in p) + '\n')
                out.write('endloop\nendfacet\n')
            out.write(f'endsolid {name}\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('surface', help='closed vessel surface, STL or VTP, RAS millimetres')
    ap.add_argument('case', type=Path, help='new case folder (must not exist)')
    ap.add_argument('--inlet-z', type=float, default=-240.0, help='inlet cut plane, mm')
    ap.add_argument('--outlet-z', type=float, default=-420.0, help='outlet cut plane, mm')
    ap.add_argument('--ext-inlet', type=float, default=3.0, help='inlet extension, x equivalent diameter')
    ap.add_argument('--ext-outlet', type=float, default=5.0, help='outlet extension, x equivalent diameter')
    ap.add_argument('--smooth', type=int, default=0,
                    help='extra windowed-sinc smoothing iterations before cutting (0 = none); a study variable')
    ap.add_argument('--cell-mm', type=float, default=1.2, help='background cell size; wall cells are half')
    ap.add_argument('--layers', type=int, default=5, help='prism layers on the wall')
    ap.add_argument('--waveform', default=str(Path(__file__).with_name('inflow_waveform_PLACEHOLDER.csv')))
    ap.add_argument('--allow-placeholder-waveform', action='store_true',
                    help='needed to build with the placeholder sine waveform (tests only)')
    ap.add_argument('--split', default='murray',
                    help="outlet1 share of the flow: 'murray' (Q ~ D^3), 'area', or a number 0-1")
    ap.add_argument('--cycles', type=int, default=6)
    ap.add_argument('--write-interval', type=float, default=0.01)
    ap.add_argument('--density', type=float, default=1060.0)
    ap.add_argument('--viscosity', type=float, default=0.0035)
    a = ap.parse_args()

    if a.case.exists():
        raise SystemExit(f'Refusing to overwrite {a.case}')
    if 'PLACEHOLDER' in Path(a.waveform).name and not a.allow_placeholder_waveform:
        raise SystemExit('The default waveform is a placeholder sine, not physiology. Digitise a measured '
                         'infrarenal waveform (see cfd_v2/README.md) or pass --allow-placeholder-waveform for a test.')

    # 1. clip, label, extend --------------------------------------------------
    raw = read_surface(a.surface)
    surface = smooth_surface(raw, a.smooth)
    moved = displacement_mm(raw, surface) if a.smooth > 0 else None
    pts, faces = clip_and_cap(surface, a.inlet_z, a.outlet_z)
    z = pts[faces][:, :, 2]
    up = np.flatnonzero(np.all(np.abs(z - a.inlet_z) < 1e-6, axis=1))
    lo = np.flatnonzero(np.all(np.abs(z - a.outlet_z) < 1e-6, axis=1))
    up_g, lo_g = face_groups(faces, up), face_groups(faces, lo)
    if len(up_g) != 1 or len(lo_g) != 2:
        raise SystemExit(f'Expected 1 inlet and 2 outlet caps, found {len(up_g)} and {len(lo_g)}. '
                         'Move the cut planes.')
    lo_g.sort(key=lambda ids: float(pts[faces[ids]][:, :, 0].mean()))
    labels = np.full(len(faces), 'wall', dtype='<U16')
    areas = tri_areas(pts, faces)
    caps = {'inlet': up_g[0], 'outlet1': lo_g[0], 'outlet2': lo_g[1]}
    diam = {k: float(np.sqrt(4 * areas[v].sum() / np.pi)) for k, v in caps.items()}
    for k, ids in caps.items():
        labels[ids] = k
    # extrude one cap at a time; ids shift after each extrusion, so re-find by label
    plan = [('inlet', np.array([0, 0, 1.0]), a.ext_inlet), ('outlet1', np.array([0, 0, -1.0]), a.ext_outlet),
            ('outlet2', np.array([0, 0, -1.0]), a.ext_outlet)]
    for name, direction, k in plan:
        ids = np.flatnonzero(labels == name)
        pts, faces, labels = extrude_cap(pts, faces, labels, ids, direction, k * diam[name], name, 'ext_' + name)
    poly, faces, labels = to_polydata(pts, faces, labels)
    pts = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    topo = topology(poly)
    if topo['boundary_edges'] or topo['nonmanifold_edges']:
        raise SystemExit(f'Surface is not closed and manifold after extension: {topo}')

    # 2. write geometry --------------------------------------------------------
    case = a.case
    pts_m = pts * 1e-3
    order = ['wall', 'ext_inlet', 'ext_outlet1', 'ext_outlet2', 'inlet', 'outlet1', 'outlet2']
    write_stl(case / 'constant/triSurface/aorta.stl', pts_m, faces, labels, order)
    inlet_ids = np.flatnonzero(labels == 'inlet')
    inlet_c = np.average(pts[faces[inlet_ids]].mean(1), axis=0, weights=tri_areas(pts, faces)[inlet_ids])
    seed = None
    for depth in [0.5, 1.0, 2.0, 4.0, 8.0]:  # mm below the inlet cap, inside the extension
        cand = inlet_c - np.array([0, 0, depth])
        if inside(poly, cand):
            seed = cand
            break
    if seed is None:
        raise SystemExit('Could not place the meshing seed inside the vessel')

    # 3. mesh dictionaries -----------------------------------------------------
    lo_b, hi_b = pts_m.min(0) - 0.004, pts_m.max(0) + 0.004
    n = np.ceil((hi_b - lo_b) / (a.cell_mm * 1e-3)).astype(int)
    v = [(lo_b[0], lo_b[1], lo_b[2]), (hi_b[0], lo_b[1], lo_b[2]), (hi_b[0], hi_b[1], lo_b[2]),
         (lo_b[0], hi_b[1], lo_b[2]), (lo_b[0], lo_b[1], hi_b[2]), (hi_b[0], lo_b[1], hi_b[2]),
         (hi_b[0], hi_b[1], hi_b[2]), (lo_b[0], hi_b[1], hi_b[2])]
    foam(case / 'system/blockMeshDict', 'convertToMeters 1;\nvertices (' + ' '.join(
        '(' + ' '.join(f'{c:.9g}' for c in p) + ')' for p in v) + ');\nblocks (hex (0 1 2 3 4 5 6 7) (' +
        ' '.join(map(str, n)) + ') simpleGrading (1 1 1));\nedges ();\nboundary (box {type patch; faces ('
        '(0 3 2 1)(4 5 6 7)(0 1 5 4)(3 7 6 2)(0 4 7 3)(1 2 6 5));});\nmergePatchPairs ();')
    regions = ' '.join(f'{r} {{level (1 1); patchInfo {{type {"wall" if r == "wall" or r.startswith("ext") else "patch"};}}}}'
                       for r in order)
    foam(case / 'system/snappyHexMeshDict', f'''castellatedMesh true;
snap true;
addLayers true;
geometry {{ aorta.stl {{ type triSurfaceMesh; name aorta; }} }}
castellatedMeshControls {{
  maxLocalCells 4000000; maxGlobalCells 8000000; minRefinementCells 0; maxLoadUnbalance 0.1;
  nCellsBetweenLevels 3; features ();
  refinementSurfaces {{ aorta {{ level (1 1); regions {{ {regions} }} }} }}
  resolveFeatureAngle 30; refinementRegions {{}};
  locationInMesh ({' '.join(f'{c:.9g}' for c in seed * 1e-3)}); allowFreeStandingZoneFaces true;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 10;
  implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false; }}
addLayersControls {{
  relativeSizes true;
  layers {{ "aorta_(wall|ext_.*)" {{ nSurfaceLayers {a.layers}; }} }}
  expansionRatio 1.2; finalLayerThickness 0.5; minThickness 0.05; nGrow 0;
  featureAngle 180; slipFeatureAngle 30; nRelaxIter 10; nSmoothSurfaceNormals 5; nSmoothNormals 5;
  nSmoothThickness 20; maxFaceThicknessRatio 0.8; maxThicknessToMedialRatio 0.6;
  minMedianAxisAngle 130; nBufferCellsNoExtrude 0; nLayerIter 50; nRelaxedIter 20;
}}
meshQualityControls {{ maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
  minVol 1e-15; minTetQuality 1e-15; minArea -1; minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.05;
  minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75; relaxed {{ maxNonOrtho 75; maxInternalSkewness 6; minTetQuality -1e30; }} }}
mergeTolerance 1e-6;''')

    # 4. physics ---------------------------------------------------------------
    t1, q1 = read_waveform(a.waveform)
    period = float(t1[-1])
    if a.split == 'murray':
        share = diam['outlet1'] ** 3 / (diam['outlet1'] ** 3 + diam['outlet2'] ** 3)
    elif a.split == 'area':
        share = diam['outlet1'] ** 2 / (diam['outlet1'] ** 2 + diam['outlet2'] ** 2)
    else:
        share = float(a.split)
    times = np.concatenate([t1[:-1] + k * period for k in range(a.cycles)] + [[a.cycles * period]])
    flows = np.concatenate([q1[:-1]] * a.cycles + [[q1[-1]]])
    inflow = '\n'.join(f'({t:.6f} {q:.10g})' for t, q in zip(times, flows))
    outflow = '\n'.join(f'({t:.6f} {share * q:.10g})' for t, q in zip(times, flows))
    walls = ' '.join(f'aorta_{w} {{type noSlip;}}' for w in ['wall', 'ext_inlet', 'ext_outlet1', 'ext_outlet2'])
    pwalls = ' '.join(f'aorta_{w} {{type zeroGradient;}}' for w in ['wall', 'ext_inlet', 'ext_outlet1', 'ext_outlet2'])
    foam(case / '0/U', f'''dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField {{
  {walls}
  aorta_inlet {{ type flowRateInletVelocity; extrapolateProfile no; volumetricFlowRate table ({inflow}); value uniform (0 0 0); }}
  aorta_outlet1 {{ type flowRateOutletVelocity; volumetricFlowRate table ({outflow}); value uniform (0 0 0); }}
  aorta_outlet2 {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
}}''', 'volVectorField')
    foam(case / '0/p', f'''dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField {{ {pwalls} aorta_inlet {{type zeroGradient;}} aorta_outlet1 {{type zeroGradient;}}
  aorta_outlet2 {{type fixedValue; value uniform 0;}} }}''', 'volScalarField')
    foam(case / 'constant/transportProperties',
         f'transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] {a.viscosity / a.density:.10g};')
    foam(case / 'constant/turbulenceProperties', 'simulationType laminar;')
    foam(case / 'system/controlDict', f'''application pimpleFoam; startFrom latestTime; startTime 0; stopAt endTime;
endTime {a.cycles * period:.6f}; deltaT 1e-4; writeControl adjustableRunTime; writeInterval {a.write_interval};
purgeWrite 0; writeFormat binary; writePrecision 8; writeCompression off; timeFormat general; timePrecision 8;
runTimeModifiable true; adjustTimeStep yes; maxCo 0.5; maxDeltaT 5e-4; functions {{}}''')
    foam(case / 'system/fvSchemes', '''ddtSchemes {default backward;} gradSchemes {default Gauss linear;}
divSchemes {default none; div(phi,U) Gauss linearUpwind grad(U); div((nuEff*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited corrected 0.5;} interpolationSchemes {default linear;}
snGradSchemes {default limited corrected 0.5;} wallDist {method meshWave;}''')
    foam(case / 'system/fvSolution', '''solvers {
  p {solver GAMG; tolerance 1e-7; relTol 0.01; smoother GaussSeidel;} pFinal {$p; relTol 0;}
  U {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0;} UFinal {$U; relTol 0;}
  "(Phi|potential)" {solver GAMG; tolerance 1e-7; relTol 0.01; smoother GaussSeidel;}
}
PIMPLE {nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 1; momentumPredictor yes;}
potentialFlow {nNonOrthogonalCorrectors 3;}''')
    foam(case / 'system/decomposeParDict', 'numberOfSubdomains 4; method simple; simpleCoeffs {n (1 1 4); delta 0.001;}')
    (case / 'aorta.foam').touch()

    info = {
        'status': 'PREPARED_NOT_MESHED',
        'surface': str(a.surface), 'cuts_RAS_mm': {'inlet_z': a.inlet_z, 'outlet_z': a.outlet_z},
        'equivalent_diameters_mm': diam,
        'extensions_mm': {'inlet': a.ext_inlet * diam['inlet'], 'outlet1': a.ext_outlet * diam['outlet1'],
                          'outlet2': a.ext_outlet * diam['outlet2']},
        'extra_smoothing_iterations': a.smooth, 'smoothing_displacement_mm': moved,
        'surface_topology': topo, 'seed_RAS_mm': seed.tolist(),
        'background_cell_mm': a.cell_mm, 'wall_cell_mm': a.cell_mm / 2, 'prism_layers': a.layers,
        'waveform_csv': str(a.waveform), 'period_s': period, 'cycles': a.cycles,
        'mean_inflow_mL_s': float(np.sum((q1[1:] + q1[:-1]) / 2 * np.diff(t1)) / period * 1e6),
        'outlet1_flow_share': share, 'split_rule': a.split,
        'outlet2': 'zero gauge pressure (reference level only; WSS does not depend on it in a rigid model)',
        'blood': {'density_kg_m3': a.density, 'viscosity_Pa_s': a.viscosity, 'model': 'Newtonian, laminar'},
        'wall': 'rigid, no slip',
        'analysis_region_RAS_mm': [a.outlet_z, a.inlet_z],
        'note': 'WSS on the extension patches (aorta_ext_*) is excluded from all results.'}
    (case / 'case_info.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
