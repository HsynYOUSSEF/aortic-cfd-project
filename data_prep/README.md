# data_prep: from public CT to a reviewed lumen

These steps run on your own computer (they need the CT, which is not in this repository).

## 1. Download and check the cases

Download the aneurysm group of [AortaSeg-60](https://zenodo.org/records/18147026) (`Anev.zip`), extract it, then:

```bash
python data_prep/check_duplicates.py ~/data/AortaSeg-60/Anev --out reports/aortaseg60_duplicates.json
```

In the pilot, Anev_03 and Anev_05 had identical masks. Keep one case per duplicate group.

## 2. Confirm the CT orientation

The Anev_01 CT and mask have the same grid but z origins about 651 mm apart. Open both in 3D Slicer and check axial, sagittal and coronal views. Do not force them together in code; ask the dataset authors if the metadata are wrong. `lumen_from_ct.py` refuses CT/mask pairs whose grids differ.

## 3. Run the AI segmentation yourself

```bash
pip install TotalSegmentator
TotalSegmentator -i Anev_01_image.nii.gz -o seg_Anev_01 --roi_subset aorta
```

Record the TotalSegmentator version. Compare `seg_Anev_01/aorta.nii.gz` with the dataset mask (Dice, surface distance) in Slicer's Segment Comparison or with `repro/tools/reconstruct_mask.py`.

## 4. Separate the blood lumen from thrombus

TotalSegmentator's aorta follows the outer wall, so an aneurysm mask includes thrombus. CFD needs the lumen only:

```bash
python data_prep/lumen_from_ct.py Anev_01_image.nii.gz seg_Anev_01/aorta.nii.gz out/Anev_01 --hu 180
```

It writes `out/Anev_01_lumen.nii.gz`, `out/Anev_01_thrombus.nii.gz` and a report with volumes and the CT values inside the mask. Choose `--hu` from those values (contrast blood is far brighter than thrombus). The result is a **candidate**: correct it in 3D Slicer, save the edit log, and have it reviewed before CFD. Then export the lumen as a closed surface (STL, RAS millimetres) for `cfd_v2/build_case.py`.

Tested here on a synthetic tube with thrombus (Dice 0.996 against the true lumen); not yet run on a real CT.
