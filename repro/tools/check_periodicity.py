"""New phase-resolved L2 check, with fixed 5% gate; static mesh only."""
import json
import sys
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def main(work):
    sys.path.insert(0, str(work / 'src'))
    import analyze_results as analysis
    case = work / 'cfd/aorta'; reader = analysis.reader(case)
    available = vtk_to_numpy(reader.GetTimeValues()).astype(float)
    current = np.round(np.arange(2.01, 3.0001, .01), 8)
    for time in np.concatenate([current, current - 1]):
        if not np.any(np.isclose(available, time, atol=1e-7, rtol=0)):
            raise RuntimeError(f'Missing phase {time}')
    def sample(time):
        mesh, patches = analysis.fields(reader, time)
        wall = patches['aorta_wall']
        size = vtk.vtkCellSizeFilter(); size.SetInputData(mesh); size.Update()
        volume = vtk_to_numpy(size.GetOutput().GetCellData().GetArray('Volume')).copy()
        area = analysis.areas(wall).copy()
        values = {'U': vtk_to_numpy(mesh.GetCellData().GetArray('U')).astype(float, copy=True),
                  'p': vtk_to_numpy(mesh.GetCellData().GetArray('p')).astype(float, copy=True),
                  'WSS': vtk_to_numpy(wall.GetCellData().GetArray('wallShearStress')).astype(float, copy=True)}
        if not all(np.isfinite(v).all() for v in values.values()) or np.any(volume <= 0) or np.any(area <= 0):
            raise RuntimeError('Invalid fields or weights')
        return values, {'U': volume, 'p': volume, 'WSS': area}
    sums = {key: [0., 0.] for key in ['U', 'p', 'WSS']}
    for time in current:
        previous, weights = sample(float(time - 1)); values, newweights = sample(float(time))
        for key in sums:
            if previous[key].shape != values[key].shape or not np.allclose(weights[key], newweights[key]):
                raise RuntimeError('Static-mesh assumption failed')
            diff = (values[key] - previous[key]) ** 2; ref = previous[key] ** 2
            if diff.ndim == 2:
                diff = diff.sum(axis=1); ref = ref.sum(axis=1)
            sums[key][0] += float(weights[key] @ diff)
            sums[key][1] += float(weights[key] @ ref)
    changes = {key: float(np.sqrt(n / d)) if d > 0 else None for key, (n, d) in sums.items()}
    report = {'status': 'PASS' if all(v is not None and v < .05 for v in changes.values()) else 'FAIL',
              'relative_L2_changes': changes, 'threshold': .05, 'matched_phases': len(current),
              'definition': 'sqrt(sum_phase,cell(weight*|current-previous|^2)/sum_phase,cell(weight*|previous|^2))',
              'weights': 'Cell volumes for U/p; wall face areas for WSS; equal time spacing.',
              'windows_s': [[1.01, 2.0], [2.01, 3.0]],
              'limitations': 'New checker, not recovered historical controller. A pass does not establish mesh independence or anatomical accuracy.'}
    (work / 'results/aorta/phase_periodicity.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
