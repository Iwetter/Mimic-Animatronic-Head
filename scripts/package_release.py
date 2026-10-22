"""Create final hash manifest and ZIP after all release verification is complete.
python scripts/package_release.py RELEASE_DIRECTORY OUTPUT_ZIP
Does not alter geometry or source inputs. Excludes interpreter cache files.
"""
from pathlib import Path
import sys,hashlib,zipfile,json
root=Path(sys.argv[1]).resolve();target=Path(sys.argv[2]).resolve()
if target.is_relative_to(root):raise SystemExit('ZIP must be outside release directory')
qa=json.loads((root/'validation/release_qa.json').read_text())
if not qa.get('digital_checks_passed'):raise SystemExit('Independent digital release QA has not passed')
files=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.blend1') and p.name!='SHA256SUMS.txt')
manifest=root/'SHA256SUMS.txt'
manifest.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix()+'\n' for p in files),encoding='utf-8')
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[manifest]:z.write(p,root.name+'/'+p.relative_to(root).as_posix())
with zipfile.ZipFile(target) as z:
    bad=z.testzip()
    if bad:raise RuntimeError('ZIP CRC failed: '+bad)
    for p in files:
        name=root.name+'/'+p.relative_to(root).as_posix()
        if hashlib.sha256(z.read(name)).hexdigest()!=hashlib.sha256(p.read_bytes()).hexdigest():raise RuntimeError(name)
print(json.dumps(dict(zip=str(target),files=len(files)+1,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),crc_and_extracted_hashes_passed=True),indent=2))
