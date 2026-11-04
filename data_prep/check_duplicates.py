"""Find byte-identical files in an extracted dataset (for example AortaSeg-60/Anev).

Hashes every file (SHA-256) and lists groups with the same content. In our pilot,
the Anev_03 and Anev_05 masks were identical, so the aneurysm group may hold
fewer than 10 different patients.

Example:
  python data_prep/check_duplicates.py ~/data/AortaSeg-60/Anev --out reports/duplicates.json
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(block), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder', type=Path)
    ap.add_argument('--pattern', default='*.nii*', help='which files to hash (default: NIfTI)')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    groups = defaultdict(list)
    files = sorted(p for p in a.folder.rglob(a.pattern) if p.is_file())
    for p in files:
        groups[sha256(p)].append(str(p.relative_to(a.folder)))
    dup = {h: v for h, v in groups.items() if len(v) > 1}
    report = {'folder': str(a.folder), 'files_hashed': len(files), 'unique_contents': len(groups),
              'duplicate_groups': list(dup.values()),
              'verdict': 'no duplicates' if not dup else f'{len(dup)} duplicate group(s): drop all but one of each'}
    text = json.dumps(report, indent=2)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)


if __name__ == '__main__':
    main()
