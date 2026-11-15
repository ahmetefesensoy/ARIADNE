"""Freeze only T3 perception's core inputs in the ASCII runtime workspace."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

root,workspace=map(Path,sys.argv[1:]);destination=workspace/'core/redline_core'
destination.mkdir(parents=True,exist_ok=False);records=[]
for name in ('__init__.py','ground.py'):
    source=root/'python/redline_core/src/redline_core'/name
    target=destination/name;shutil.copyfile(source,target)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Core snapshot mismatch')
    records.append({'source':str(source),'snapshot':str(target),'sha256':digest})
(workspace/'t3-core-inputs.json').write_text(json.dumps(records,indent=2)+'\n')
