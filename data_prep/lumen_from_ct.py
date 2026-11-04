"""Split an aorta mask into blood lumen and thrombus using the CT intensities.

TotalSegmentator's aorta label (and the AortaSeg-60 masks made with it) follow the
outer aortic wall, so in an aneurysm they include intraluminal thrombus. Blood flows
only in the contrast-filled lumen, so CFD must use the lumen.

Method (a candidate for review, not ground truth):
  1. inside the aorta mask, voxels brighter than --hu (contrast blood) form the lumen
  2. fill holes slice by slice, remove specks, keep the largest connected component
  3. thrombus = aorta mask minus lumen
Always check the result in 3D Slicer and correct it by hand before using it for CFD.

Example:
  python data_prep/lumen_from_ct.py Anev_01_image.nii.gz Anev_01_aorta.nii.gz out/Anev_01 --hu 180
"""
import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi


def largest_component(mask):
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


def split(ct, aorta, hu, spacing, min_speck_mm3=20.0):
    lumen = aorta & (ct >= hu)
    # fill enclosed holes in every axial slice (calcium shadows, noise)
    for k in range(lumen.shape[2]):
        lumen[:, :, k] = ndi.binary_fill_holes(lumen[:, :, k])
    lumen = ndi.binary_opening(lumen, structure=ndi.generate_binary_structure(3, 1))
    voxel = float(np.prod(spacing))
    lab, n = ndi.label(lumen)
    if n:
        sizes = ndi.sum(lumen, lab, range(1, n + 1)) * voxel
        lumen = np.isin(lab, 1 + np.flatnonzero(sizes >= min_speck_mm3))
    lumen = largest_component(lumen) & aorta
    return lumen, aorta & ~lumen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ct', type=Path, help='CT image, NIfTI, Hounsfield units')
    ap.add_argument('aorta', type=Path, help='aorta mask on the same grid, NIfTI')
    ap.add_argument('out', type=Path, help='output prefix')
    ap.add_argument('--hu', type=float, default=180.0,
                    help='lumen threshold, HU (contrast blood is usually far above thrombus; check the histogram)')
    a = ap.parse_args()
    ct_img, m_img = nib.load(str(a.ct)), nib.load(str(a.aorta))
    if ct_img.shape != m_img.shape or not np.allclose(ct_img.affine, m_img.affine, atol=1e-3):
        raise SystemExit('CT and mask are not on the same grid/affine. Fix the orientation first '
                         '(see the data check in the report) instead of forcing them together.')
    ct = np.asarray(ct_img.dataobj, dtype=np.float32)
    aorta = np.asarray(m_img.dataobj) > 0
    spacing = ct_img.header.get_zooms()[:3]
    lumen, thrombus = split(ct, aorta, a.hu, spacing)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    for name, arr in [('lumen', lumen), ('thrombus', thrombus)]:
        nib.save(nib.Nifti1Image(arr.astype(np.uint8), ct_img.affine, ct_img.header),
                 str(a.out) + f'_{name}.nii.gz')
    v = float(np.prod(spacing)) / 1000.0  # mL per voxel
    inside = ct[aorta]
    report = {'threshold_HU': a.hu, 'aorta_mL': float(aorta.sum() * v), 'lumen_mL': float(lumen.sum() * v),
              'thrombus_mL': float(thrombus.sum() * v),
              'thrombus_fraction_pct': float(100 * thrombus.sum() / max(aorta.sum(), 1)),
              'HU_inside_mask_percentiles_5_25_50_75_95': [float(x) for x in np.percentile(inside, [5, 25, 50, 75, 95])],
              'status': 'CANDIDATE - review and correct in 3D Slicer before CFD'}
    Path(str(a.out) + '_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
