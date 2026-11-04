"""Grid convergence index (Roache / Celik et al. 2008) for TAWSS from three meshes.

Give the three results/summary.json files from fine to coarse with their background cell sizes.

Example:
  python cfd_v2/gci.py runs/ms/m3/results/summary.json:0.8 \
                       runs/ms/m2/results/summary.json:1.1 runs/ms/m1/results/summary.json:1.6
"""
import json
import math
import sys


def gci(f1, f2, f3, h1, h2, h3, fs=1.25):
    """f1 = fine. Returns observed order p, GCI_fine (fraction), extrapolated value."""
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0 or e32 / e21 <= 0:
        return {'status': 'oscillatory or converged; GCI not defined', 'e21': e21, 'e32': e32}
    s = math.copysign(1, e32 / e21)
    p = 1.0
    for _ in range(100):  # fixed-point iteration for unequal refinement ratios
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
    ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
    rel = abs((f1 - f2) / f1) if f1 else float('inf')
    return {'status': 'ok', 'order_p': p, 'GCI_fine_pct': 100 * fs * rel / (r21 ** p - 1),
            'extrapolated': ext, 'fine': f1, 'medium': f2, 'coarse': f3}


def main(args):
    if len(args) != 3:
        raise SystemExit(__doc__)
    runs = []
    for arg in args:
        path, h = arg.rsplit(':', 1)
        runs.append((json.load(open(path)), float(h)))
    (s1, h1), (s2, h2), (s3, h3) = runs
    if not h1 < h2 < h3:
        raise SystemExit('List the meshes from fine to coarse')
    report = {'mean_TAWSS': gci(s1['mean_TAWSS_Pa'], s2['mean_TAWSS_Pa'], s3['mean_TAWSS_Pa'], h1, h2, h3), 'bands': []}
    for b1, b2, b3 in zip(s1['bands'], s2['bands'], s3['bands']):
        if b1['z_mm'] != b2['z_mm'] or b1['z_mm'] != b3['z_mm']:
            raise SystemExit('Band definitions differ between runs; use the same --bands')
        g = gci(b1['TAWSS_Pa'], b2['TAWSS_Pa'], b3['TAWSS_Pa'], h1, h2, h3)
        g['z_mm'] = b1['z_mm']
        report['bands'].append(g)
    ok = [b for b in report['bands'] if b['status'] == 'ok']
    report['verdict'] = ('PASS' if ok and len(ok) == len(report['bands']) and
                         all(b['GCI_fine_pct'] < 5 for b in ok) else 'FAIL or not converged')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
