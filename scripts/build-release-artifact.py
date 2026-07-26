#!/usr/bin/env python3
from __future__ import annotations
import argparse, fnmatch, zipfile
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',default='.'); ap.add_argument('--output',required=True); ns=ap.parse_args()
    repo=Path(ns.repo).resolve(); out=(repo/ns.output).resolve()
    patterns=[]
    ignore=repo/'.not_to_zip'
    if ignore.is_file():
        patterns=[(x.strip()[2:] if x.strip().startswith('./') else x.strip()) for x in ignore.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    def excluded(rel:str)->bool:
        return rel==out.relative_to(repo).as_posix() or any(fnmatch.fnmatch(rel,p.rstrip('/')) or fnmatch.fnmatch(rel,p.rstrip('/')+'/*') for p in patterns)
    files=sorted(p for p in repo.rglob('*') if p.is_file() and not excluded(p.relative_to(repo).as_posix()))
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            rel=p.relative_to(repo).as_posix(); info=zipfile.ZipInfo(rel); info.date_time=(2020,1,1,0,0,0); mode = 0o100755 if (p.stat().st_mode & 0o111) else 0o100644; info.external_attr=mode<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
    return 0
if __name__=='__main__': raise SystemExit(main())
