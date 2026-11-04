"""New conservative mask-repair baseline, NOT the original repair algorithm.

Accepts a scalar uint8, gzip/raw NRRD in orthogonal RAS-mm coordinates.
Retains the input grid. No CT alignment or automatic CT segmentation is done.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import vtk
from vtk.util.numpy_support import numpy_to_vtk


def read_mask(path):
    raw = path.read_bytes()
    header, payload = re.split(b'\r?\n\r?\n', raw, maxsplit=1)
    text = header.decode()
    def value(key):
        match = re.search(r'^' + re.escape(key) + r':\s*(.*)$', text, re.M)
        if not match:
            raise ValueError(f'Missing NRRD field: {key}')
        return match[1].strip()
    if value('dimension') != '3' or value('type') not in ['unsigned char', 'uint8', 'uchar']:
        raise ValueError('Only scalar 3-D uint8 NRRD is supported')
    if value('space') != 'right-anterior-superior':
        raise ValueError('Requires explicit RAS coordinates; no implicit orientation conversion')
    sizes = tuple(map(int, value('sizes').split()))
    matrix = np.array([list(map(float, s.split(','))) for s in
                       re.findall(r'\(([^)]+)\)', value('space directions'))]).T
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError('Invalid direction matrix')
    spacing = np.linalg.norm(matrix, axis=0)
    if np.any(spacing <= 0) or not np.allclose(matrix.T @ matrix, np.diag(spacing**2), atol=1e-7):
        raise ValueError('Nonorthogonal grid is unsupported')
    origin = np.fromstring(value('space origin').strip('()'), sep=',')
    if origin.size != 3 or not np.isfinite(origin).all():
        raise ValueError('Invalid origin')
    encoding = value('encoding')
    if encoding == 'gzip':
        payload = gzip.decompress(payload)
    elif encoding != 'raw':
        raise ValueError('Unsupported encoding')
    if len(payload) != int(np.prod(sizes)):
        raise ValueError('Payload size mismatch')
    mask = np.frombuffer(payload, np.uint8).reshape(sizes[::-1])
    if not np.isin(mask, [0, 1]).all() or not mask.any():
        raise ValueError('Requires a nonempty binary mask, not a multilabel segmentation')
    return mask.astype(bool), text, matrix, origin


def major_components(mask):
    labels, count = ndi.label(mask)
    sizes = np.bincount(labels.ravel())[1:]
    return labels, [i + 1 for i, size in enumerate(sizes) if size >= max(8, .05 * mask.sum())]


def repair(source, spacing, sigma_mm):
    filled = np.array([ndi.binary_fill_holes(s) for s in source])
    # Pad to make the outside of the image explicit, without discarding end slices.
    pad = max(2, int(np.ceil(4 * sigma_mm / min(spacing))))
    padded = np.pad(filled, pad)
    sdf = ndi.distance_transform_edt(padded, sampling=spacing) - ndi.distance_transform_edt(~padded, sampling=spacing)
    candidate = ndi.gaussian_filter(sdf, sigma=np.asarray([sigma_mm] * 3) / spacing) > 0
    candidate = candidate[pad:-pad, pad:-pad, pad:-pad]
    restored = []
    # Protect source cross-section components from disappearance or merger.
    # This is a conservative safeguard, not an anatomical validation.
    for z in range(len(source)):
        old, ids = major_components(source[z]); new, _ = ndi.label(candidate[z]); matches = []
        for label in ids:
            sel = old == label
            overlap = new[sel]; overlap = overlap[overlap != 0]
            matches.append(int(np.bincount(overlap).argmax()) if overlap.size else 0)
        lost = any(np.count_nonzero(candidate[z] & (old == i)) < .8 * np.count_nonzero(old == i) for i in ids)
        if lost or 0 in matches or len(set(matches)) != len(matches):
            candidate[z] = source[z]; restored.append(z)
    labels, count = ndi.label(candidate)
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    candidate = labels == int(sizes.argmax())
    return candidate, restored


def surface(mask, matrix, origin, path):
    # Marching cubes in voxel coordinates, then transform into the original RAS grid.
    padded = np.pad(mask.astype(np.uint8), 1)
    image = vtk.vtkImageData(); image.SetDimensions(*padded.shape[::-1]); image.SetOrigin(-1, -1, -1)
    image.GetPointData().SetScalars(numpy_to_vtk(padded.ravel(), deep=True))
    contour = vtk.vtkFlyingEdges3D(); contour.SetInputData(image); contour.SetValue(0, .5); contour.Update()
    transform = vtk.vtkTransform(); m = vtk.vtkMatrix4x4()
    for i in range(3):
        for j in range(3):
            m.SetElement(i, j, float(matrix[i, j]))
        m.SetElement(i, 3, float(origin[i]))
    transform.SetMatrix(m)
    filt = vtk.vtkTransformPolyDataFilter(); filt.SetInputConnection(contour.GetOutputPort()); filt.SetTransform(transform)
    normals = vtk.vtkPolyDataNormals(); normals.SetInputConnection(filt.GetOutputPort()); normals.ConsistencyOn(); normals.AutoOrientNormalsOn(); normals.SplittingOff(); normals.Update()
    writer = vtk.vtkXMLPolyDataWriter(); writer.SetFileName(str(path)); writer.SetInputConnection(normals.GetOutputPort())
    if writer.Write() != 1:
        raise RuntimeError('Surface export failed')
    edges = vtk.vtkFeatureEdges(); edges.SetInputConnection(normals.GetOutputPort()); edges.FeatureEdgesOff(); edges.ManifoldEdgesOff(); edges.BoundaryEdgesOn(); edges.NonManifoldEdgesOn(); edges.Update()
    return {'triangles': normals.GetOutput().GetNumberOfCells(), 'boundary_or_nonmanifold_edges': edges.GetOutput().GetNumberOfCells()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path); ap.add_argument('output', type=Path)
    ap.add_argument('--sigma-mm', type=float, default=.65)
    ap.add_argument('--reference', type=Path, help='Optional published repaired mask, for comparison only')
    a = ap.parse_args()
    if not np.isfinite(a.sigma_mm) or not 0 <= a.sigma_mm <= 2:
        raise ValueError('sigma-mm must be finite and between 0 and 2')
    if a.output.exists():
        raise FileExistsError(a.output)
    source, header, matrix, origin = read_mask(a.source)
    repaired, restored = repair(source, np.linalg.norm(matrix, axis=0)[::-1], a.sigma_mm)
    a.output.mkdir(parents=True)
    header = re.sub(r'^encoding:.*$', 'encoding: gzip', header, flags=re.M)
    out = a.output / 'RECONSTRUCTED_BASELINE.nrrd'
    out.write_bytes(header.encode() + b'\n\n' + gzip.compress(repaired.astype(np.uint8).tobytes(), mtime=0))
    major_retention = []
    merged_slices = []
    for z in range(len(source)):
        old, ids = major_components(source[z]); new, _ = ndi.label(repaired[z]); matches = []
        for label in ids:
            sel = old == label
            major_retention.append(float((repaired[z] & sel).sum() / sel.sum()))
            overlap = new[sel]; overlap = overlap[overlap != 0]
            matches.append(int(np.bincount(overlap).argmax()) if overlap.size else 0)
        if len(set(matches)) != len(matches) or 0 in matches:
            merged_slices.append(z)
    report = {'method': 'NEW baseline v1: axial hole fill, physical signed-distance smoothing, slice safeguard, largest 3D component',
              'status': 'RESEARCH_CANDIDATE_NOT_ANATOMICALLY_VALIDATED', 'sigma_mm': a.sigma_mm,
              'source_sha256': hashlib.sha256(a.source.read_bytes()).hexdigest(),
              'output_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
              'source_voxels': int(source.sum()), 'output_voxels': int(repaired.sum()),
              'added_voxels': int((repaired & ~source).sum()), 'removed_voxels': int((source & ~repaired).sum()),
              'net_volume_change_percent': float(100 * (repaired.sum() / source.sum() - 1)),
              'restored_source_slices': restored, 'components_3d': int(ndi.label(repaired)[1]),
              'minimum_major_source_component_retention': min(major_retention, default=0),
              'merged_or_missing_major_component_slices': merged_slices,
              'component_retention_gate': min(major_retention, default=0) >= .8 and not merged_slices,
              'voxel_volume_mm3': float(abs(np.linalg.det(matrix))),
              'surface': surface(repaired, matrix, origin, a.output / 'RECONSTRUCTED_BASELINE_RAS_mm.vtp'),
              'limitations': ['Not the original repair program', 'No CT segmentation or alignment',
                              'No anatomical, self-intersection or CFD accuracy validation',
                              'Does not replace the published geometry or regenerate its exact CFD results']}
    if a.reference:
        ref, _, rm, ro = read_mask(a.reference)
        if ref.shape != source.shape or not np.allclose(rm, matrix) or not np.allclose(ro, origin):
            raise ValueError('Reference grid mismatch')
        report['comparison_to_published_repair'] = {'dice': float(2 * (repaired & ref).sum() / (repaired.sum() + ref.sum())),
                                                    'different_voxels': int((repaired != ref).sum())}
    (a.output / 'repair_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
