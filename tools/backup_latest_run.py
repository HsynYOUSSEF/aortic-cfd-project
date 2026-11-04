"""Create and read-back verify a new ZIP of a full run. Never deletes source files."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run_root', type=Path)
    ap.add_argument('output_zip', type=Path)
    a = ap.parse_args()
    root = a.run_root.resolve(strict=True)
    dest = a.output_zip.resolve()
    if root == dest or root in dest.parents:
        ap.error('Output must be outside the source run.')
    if dest.exists() or dest.with_suffix(dest.suffix+'.partial').exists():
        ap.error('Output already exists; choose another name.')
    required = ['cfd/aorta/constant/polyMesh/'+x for x in ['points','faces','owner','neighbour','boundary']]
    required += ['cfd/aorta/system/'+x for x in ['controlDict','fvSchemes','fvSolution']]
    required += ['run_config.json']
    missing = [p for p in required if not (root/p).is_file()]
    if missing:
        ap.error('Not a complete run root; missing: '+', '.join(missing))
    entries = sorted(root.rglob('*'))
    if any(p.is_symlink() for p in entries):
        ap.error('Symlinks detected; resolve their intended data into a separate complete copy first.')
    files = [p for p in entries if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(dest.parent).free < size*1.05+100*1024*1024:
        ap.error('Insufficient conservative space allowance; use an external drive.')
    expected = {str(p.relative_to(root)).replace('\\','/'):sha(p) for p in files}
    partial = dest.with_suffix(dest.suffix+'.partial')
    with zipfile.ZipFile(partial,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for p in files:
            z.write(p,'full_run/'+p.relative_to(root).as_posix())
        z.writestr('BACKUP_SHA256.json',json.dumps(expected,indent=2))
    with zipfile.ZipFile(partial) as z:
        for rel, digest in expected.items():
            h=hashlib.sha256()
            with z.open('full_run/'+rel) as stream:
                for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
            if h.hexdigest()!=digest:
                raise RuntimeError('Archive mismatch: '+rel)
    if {str(p.relative_to(root)).replace('\\','/'):sha(p) for p in root.rglob('*') if p.is_file()} != expected:
        raise RuntimeError('Source changed during backup; stop solver and try again with a new output.')
    partial.rename(dest)
    digest=sha(dest)
    dest.with_suffix(dest.suffix+'.sha256').write_text(digest+'  '+dest.name+'\n')
    print(f'VERIFIED archive: {dest}; {len(files)} files; SHA256 {digest}')
    print('No source files deleted. Verify a separate storage copy before deleting any local data.')
if __name__=='__main__':main()
