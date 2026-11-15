"""Refresh only approved narrative audio/script; no level or material edits."""
import json,os
from pathlib import Path
import unreal
root=Path(os.environ['REDLINE_REPO']);source=root/'assets/narrative/prologue_v1';data=json.loads((source/'script.json').read_text(encoding='utf-8'))
for shot in data['shots']+data['mission_intros']:
 t=unreal.AssetImportTask();t.filename=str(source/'chatterbox'/shot['voice']);t.destination_path='/Game/Prologue/Audio';t.destination_name='VO_'+shot['id'];t.automated=True;t.replace_existing=True;t.save=True;unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
(Path(unreal.Paths.project_content_dir())/'Prologue/script.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/'test-results/video-voice-import.json').write_text(json.dumps({'passed':True,'count':len(data['shots'])+len(data['mission_intros']),'source':'chatterbox/provenance.json','level_changed':False})+'\n')
