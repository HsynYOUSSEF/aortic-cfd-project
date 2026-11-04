"""Compute TAWSS, OSI and RRT on the vessel wall of a solved cfd_v2 case.

Wall shear stress (WSS) is taken from OpenFOAM's wallShearStress field when it was written,
otherwise computed here from the velocity in the wall cells:

    tau_w = mu * U_t / d      (U_t: velocity of the wall cell tangential to the wall,
                               d: distance from the wall face to that cell's centre)

This is the same one-sided wall gradient OpenFOAM uses, and it avoids the 'sha1' crash of the
wallShearStress function object in Ubuntu's OpenFOAM v1912 package. Prism layers on the wall
make this accurate; on a staircase mesh without layers it is not.

Only the patch aorta_wall is analysed (the flow extensions are excluded).
Outputs in CASE/results/:
  wall_metrics.vtp   wall surface with TAWSS_Pa, OSI, RRT_Pa_inv (open in ParaView)
  summary.json       area-weighted means per z band, area below 0.4 Pa, cycle-to-cycle change

Example:
  python cfd_v2/analyze_case.py runs/ms/fine --bands 30
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray


# ------------------------------------------------------------- OpenFOAM file reading
def _header(data):
    end = data.index(b'}', data.index(b'FoamFile')) + 1
    head = data[:end].decode('latin-1')
    binary = re.search(r'format\s+binary', head) is not None
    arch = re.search(r'label=(\d+)', head)
    label = np.int64 if arch and arch[1] == '64' else np.int32
    return end, binary, label


def _read_list(data, pos, binary, dtype, ncomp):
    """Read 'N ( ... )' starting at byte pos; returns (array, position after ')')."""
    m = re.compile(rb'\s*(\d+)\s*\(').match(data, pos)
    if not m:
        raise ValueError('list not found')
    n, start = int(m[1]), m.end()
    if binary:
        size = np.dtype(dtype).itemsize * ncomp * n
        arr = np.frombuffer(data, dtype=dtype, count=n * ncomp, offset=start).copy()
        end = data.index(b')', start + size) + 1
    else:
        end = start
        depth = 1
        while depth:
            c = data[end:end + 1]
            depth += (c == b'(') - (c == b')')
            end += 1
        arr = np.array(re.findall(rb'[-+0-9.eE]+', data[start:end - 1]), dtype=float).astype(dtype)
    return arr.reshape(n, ncomp) if ncomp > 1 else arr, end


def read_poly_list(path, dtype_kind, ncomp=1):
    data = Path(path).read_bytes()
    pos, binary, label = _header(data)
    dtype = label if dtype_kind == 'label' else np.float64
    # skip comment lines after the header
    m = re.compile(rb'(?:\s|//[^\n]*\n|/\*.*?\*/)*', re.S).match(data, pos)
    return _read_list(data, m.end(), binary, dtype, ncomp), binary, label, data


def read_faces(path):
    (offsets, pos), binary, label, data = read_poly_list(path, 'label')
    labels, _ = _read_list(data, pos, binary, label, 1)
    return offsets, labels


def read_boundary(path):
    text = Path(path).read_text(errors='replace')
    out = {}
    for name, body in re.findall(r'\n\s*(\w+)\s*\{([^}]*)\}', text):
        s, n = re.search(r'startFace\s+(\d+)', body), re.search(r'nFaces\s+(\d+)', body)
        if s and n:
            out[name] = (int(s[1]), int(n[1]))
    return out


def read_internal_vector(path):
    data = Path(path).read_bytes()
    pos, binary, _ = _header(data)
    m = re.compile(rb'internalField\s+nonuniform\s+List<vector>').search(data, pos)
    if not m:
        raise ValueError(f'{path}: no nonuniform internalField')
    return _read_list(data, m.end(), binary, np.float64, 3)[0]


def read_patch_vector(path, patch):
    data = Path(path).read_bytes()
    pos, binary, _ = _header(data)
    i = data.index(patch.encode(), data.index(b'boundaryField', pos))
    m = re.compile(rb'value\s+nonuniform\s+List<vector>').search(data, i)
    return _read_list(data, m.end(), binary, np.float64, 3)[0]


# ------------------------------------------------------------- wall geometry
class Wall:
    def __init__(self, case, patch='aorta_wall'):
        mesh = case / 'constant/polyMesh'
        self.points = read_poly_list(mesh / 'points', 'scalar', 3)[0][0]
        offsets, labels = read_faces(mesh / 'faces')
        owner = read_poly_list(mesh / 'owner', 'label')[0][0]
        neighbour = read_poly_list(mesh / 'neighbour', 'label')[0][0]
        start, n = read_boundary(mesh / 'boundary')[patch]
        self.faces = [labels[offsets[f]:offsets[f + 1]] for f in range(start, start + n)]
        self.cells = owner[start:start + n]
        # face centroids and area vectors (triangle fan around the vertex mean, as OpenFOAM)
        cf, sf = np.zeros((n, 3)), np.zeros((n, 3))
        for k, f in enumerate(self.faces):
            p = self.points[f]
            c0 = p.mean(0)
            q = np.roll(p, -1, axis=0)
            tri_n = np.cross(p - c0, q - c0) / 2
            tri_c = (p + q + c0) / 3
            a = np.linalg.norm(tri_n, axis=1)
            sf[k] = tri_n.sum(0)
            cf[k] = (tri_c * a[:, None]).sum(0) / a.sum() if a.sum() > 0 else c0
        self.cf, self.area = cf, np.linalg.norm(sf, axis=1)
        self.normal = sf / self.area[:, None]  # outward (out of the fluid)
        # wall-cell centres: mean of the cell's vertices
        wanted = np.zeros(owner.max() + 1, bool)
        wanted[self.cells] = True
        nint = len(neighbour)
        cell_pts = {}
        for f in np.flatnonzero(wanted[owner]):
            cell_pts.setdefault(int(owner[f]), set()).update(labels[offsets[f]:offsets[f + 1]].tolist())
        for f in np.flatnonzero(wanted[neighbour]):
            cell_pts.setdefault(int(neighbour[f]), set()).update(labels[offsets[f]:offsets[f + 1]].tolist())
        cc = np.array([self.points[list(cell_pts[int(c)])].mean(0) for c in self.cells])
        self.d = np.einsum('ij,ij->i', self.normal, self.cf - cc)
        if np.any(self.d <= 0):
            raise RuntimeError('Wall cell centre outside its face: mesh orientation problem')
        self.nint = nint

    def polydata(self):
        poly = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.SetData(numpy_to_vtk(self.points, deep=True))
        poly.SetPoints(pts)
        conn = np.concatenate([np.concatenate([[len(f)], f]) for f in self.faces]).astype(np.int64)
        arr = vtk.vtkCellArray()
        arr.SetCells(len(self.faces), numpy_to_vtkIdTypeArray(conn, deep=True))
        poly.SetPolys(arr)
        clean = vtk.vtkCleanPolyData()  # drop unused points
        clean.SetInputData(poly)
        clean.PointMergingOff()
        clean.Update()
        return clean.GetOutput()

    def wss(self, U, mu):
        u = U[self.cells]
        ut = u - np.einsum('ij,ij->i', u, self.normal)[:, None] * self.normal
        return mu * ut / self.d[:, None]  # Pa, stress the fluid exerts on the wall (flow direction)


# ------------------------------------------------------------- metrics
def integrate(t, x):
    dt = np.diff(t)
    shape = (-1,) + (1,) * (x.ndim - 1)
    return np.sum((x[1:] + x[:-1]) / 2 * dt.reshape(shape), axis=0)


def metrics(t, tau):
    T = t[-1] - t[0]
    tawss = integrate(t, np.linalg.norm(tau, axis=2)) / T
    mean_vec = np.linalg.norm(integrate(t, tau), axis=1) / T
    with np.errstate(divide='ignore', invalid='ignore'):
        osi = np.where(tawss > 0, 0.5 * (1 - mean_vec / tawss), np.nan)
        rrt = np.where(mean_vec > 0, 1 / mean_vec, np.inf)
    return tawss, np.clip(osi, 0, 0.5), rrt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case', type=Path)
    ap.add_argument('--period', type=float, default=None, help='cycle length, s (default: from case_info.json)')
    ap.add_argument('--bands', type=float, default=30.0, help='height of the z bands, mm')
    ap.add_argument('--low', type=float, default=0.4, help='low-TAWSS threshold, Pa (Bappoo et al. 2021)')
    a = ap.parse_args()
    case = a.case.resolve()
    info = json.loads((case / 'case_info.json').read_text())
    rho, mu = info['blood']['density_kg_m3'], info['blood']['viscosity_Pa_s']
    period = a.period or info['period_s']
    times = sorted((float(p.name), p) for p in case.iterdir()
                   if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+', p.name) and float(p.name) > 0
                   and (p / 'U').is_file())
    if not times:
        raise SystemExit('No saved velocity fields found')
    t_all = np.array([t for t, _ in times])
    end = t_all[-1]
    last = [x for x in times if x[0] >= end - period - 1e-9]
    prev = [x for x in times if end - 2 * period - 1e-9 <= x[0] <= end - period + 1e-9]
    if len(last) < 10 or abs(last[0][0] - (end - period)) > 1e-6:
        raise SystemExit(f'Need saved fields over the whole last cycle {end - period:.4f}-{end:.4f} s '
                         f'(at least 10 samples); found {len(last)}')
    wall = Wall(case)
    source = {'n': 0}

    def tau_at(folder):
        f = folder / 'wallShearStress'
        if f.is_file():
            source['n'] += 1
            return read_patch_vector(f, 'aorta_wall') * rho  # kinematic m2/s2 -> Pa, once
        return wall.wss(read_internal_vector(folder / 'U'), mu)

    def cycle(sel):
        ts = np.array([t for t, _ in sel])
        return metrics(ts, np.array([tau_at(p) for _, p in sel]))

    tawss, osi, rrt = cycle(last)
    area = wall.area
    change = None
    if len(prev) == len(last):
        tawss_prev = cycle(prev)[0]
        change = float(np.sqrt(np.average((tawss - tawss_prev) ** 2, weights=area) /
                               np.average(tawss ** 2, weights=area)))

    z = wall.cf[:, 2] * 1000  # mm
    lo, hi = info['analysis_region_RAS_mm']
    edges = np.arange(lo, hi + 1e-9, a.bands)
    if edges[-1] < hi:
        edges = np.append(edges, hi)
    bands = []
    for z0, z1 in zip(edges[:-1], edges[1:]):
        sel = (z >= z0) & (z < z1)
        if sel.any():
            bands.append({'z_mm': [float(z0), float(z1)], 'area_mm2': float(area[sel].sum() * 1e6),
                          'TAWSS_Pa': float(np.average(tawss[sel], weights=area[sel])),
                          'OSI': float(np.average(osi[sel], weights=area[sel])),
                          'area_below_low_pct': float(100 * area[sel][tawss[sel] < a.low].sum() / area[sel].sum())})

    poly = wall.polydata()
    for name, values in [('TAWSS_Pa', tawss), ('OSI', osi), ('RRT_Pa_inv', rrt),
                         ('wall_cell_distance_m', wall.d)]:
        arr = numpy_to_vtk(np.asarray(values, float), deep=True)
        arr.SetName(name)
        poly.GetCellData().AddArray(arr)
    out = case / 'results'
    out.mkdir(exist_ok=True)
    w = vtk.vtkXMLPolyDataWriter()
    w.SetFileName(str(out / 'wall_metrics.vtp'))
    w.SetInputData(poly)
    w.Write()
    samples = len(last) + (len(prev) if change is not None else 0)
    summary = {
        'case': str(case), 'cycle_s': [last[0][0], last[-1][0]], 'samples': len(last),
        'wss_source': 'OpenFOAM wallShearStress' if source['n'] == samples else
                      ('velocity of wall cells (mu * U_t / d)' if source['n'] == 0 else 'mixed'),
        'wall_faces': len(wall.faces), 'wall_area_mm2': float(area.sum() * 1e6),
        'median_wall_cell_distance_mm': float(np.median(wall.d) * 1000),
        'mean_TAWSS_Pa': float(np.average(tawss, weights=area)),
        'p95_TAWSS_Pa': float(np.percentile(tawss, 95)),
        'mean_OSI': float(np.average(osi, weights=area)),
        f'area_below_{a.low}_Pa_pct': float(100 * area[tawss < a.low].sum() / area.sum()),
        'TAWSS_cycle_change_relL2': change,
        'bands': bands,
        'notes': 'Area-weighted. Extensions excluded. Rigid wall, Newtonian blood.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
