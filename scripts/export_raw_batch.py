"""Publish only recorded source takes; keep final edit decisions open."""
import subprocess,sys
from pathlib import Path
base=Path('/mnt/c/Users/USER/AppData/Local/Redline');out=Path('outputs/raw-takes');out.mkdir(exist_ok=True,parents=True)
shots=[('Clips/01_acilis-20261115T100003Z-0BB4395F','01_acilis_ilk_kayit'),('TaskClips/03_numune-20261115T101534Z-F6113D6F','03_numune'),('TaskClips/04_xrf-20261115T101709Z-436AE7FB','04_xrf'),('TaskClips/05_istasyon-20261115T101801Z-9B79FA3C','05_istasyon'),('TaskClips/06_sondaj-20261115T102616Z-03A64E2F','06_sondaj'),('TaskClips/08_numune_teslimi-20261115T104536Z-53589348','08_numune_teslimi')]
for folder,name in shots:
 target=out/(name+'.mp4')
 if target.exists():continue
 subprocess.run([sys.executable,'scripts/export_raw_take.py',str(base/folder),str(target)],check=True)
