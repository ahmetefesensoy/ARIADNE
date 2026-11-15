"""Read-only Unreal inspection for the saved narrative rooms and voice assets.

Run after prepare_prologue_scene.py with REDLINE_REPO set. This loads the saved
level and reads assets/files; it never saves content, starts play, moves actors,
or sends ROS commands. It writes only test-results/command-rooms-verification.json.
Rendered readability, door motion, audio routing and acting still require live QA.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import traceback
import wave

import unreal


ROOT = Path(os.environ['REDLINE_REPO']).resolve()
DEST = '/Game/Prologue'
REPORT = {
    'schema': 'redline.command-rooms.inspection.v1',
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'SCENARIO', 'passed': False,
    'scope': 'saved map/asset/source inspection only; no gameplay, pressure, audio-device or rendered-look acceptance',
    'engine': unreal.SystemLibrary.get_engine_version(),
    'checks': [], 'voices': [], 'sources': [],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    REPORT['sources'].append({'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                              'sha256': digest(path)})
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check(name, passed, **details):
    REPORT['checks'].append({'name': name, 'passed': bool(passed), **details})
    return bool(passed)


def xyz(vector):
    return [float(vector.x), float(vector.y), float(vector.z)]


def distance_xy(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def inspect_pcm(path):
    with wave.open(str(path), 'rb') as stream:
        channels, width, sample_rate, frames = (stream.getnchannels(), stream.getsampwidth(),
                                                stream.getframerate(), stream.getnframes())
        if stream.getcomptype() != 'NONE' or width not in (1, 2, 3, 4):
            raise ValueError('Expected an uncompressed integer PCM narration source')
        data = stream.readframes(frames)
    if not channels or not sample_rate or not frames or len(data) != frames*channels*width:
        raise ValueError('Truncated/empty narration PCM')
    if width == 1:
        values = ((value-128)/128 for value in data)
    elif width == 2:
        values = (value[0]/32768 for value in struct.iter_unpack('<h', data))
    elif width == 4:
        values = (value[0]/2147483648 for value in struct.iter_unpack('<i', data))
    else:
        values = (int.from_bytes(data[index:index+3], 'little', signed=True)/8388608
                  for index in range(0, len(data), 3))
    total_squared, peak, count, clipped = 0., 0., 0, 0
    for value in values:
        if not math.isfinite(value): raise ValueError('Non-finite decoded PCM sample')
        magnitude = abs(value)
        total_squared += value*value
        peak = max(peak, magnitude)
        count += 1
        clipped += magnitude >= .999
    rms = math.sqrt(total_squared/count)
    return {'duration_s': frames/sample_rate, 'sample_rate_hz': sample_rate,
            'channels': channels, 'sample_width_bytes': width, 'sample_count': count,
            'finite': math.isfinite(rms) and math.isfinite(peak),
            'peak': peak, 'rms': rms, 'full_scale_samples': clipped}


try:
    profile = read_json(ROOT/'data/engines/BXW/eva-runtime-v1.json')
    import_report = read_json(ROOT/'test-results/prologue-import.json')
    source_script_path = ROOT/'assets/narrative/prologue_v1/script.json'
    source_script = read_json(source_script_path)
    runtime_script_path = Path(unreal.Paths.project_content_dir())/'Prologue/script.json'
    runtime_script = json.loads(runtime_script_path.read_text(encoding='utf-8-sig'))
    REPORT['runtime_script_sha256'] = digest(runtime_script_path)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/EVAFixtures/BXW_EVA'):
        raise RuntimeError('Could not load saved BXW_EVA map')
    actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    tagged = {}
    for actor in actors:
        for tag in actor.tags: tagged.setdefault(str(tag), []).append(actor)

    def unique(tag):
        found = tagged.get(tag, [])
        check('unique actor: '+tag, len(found) == 1,
              matches=[actor.get_path_name() for actor in found])
        return found[0] if len(found) == 1 else None

    rooms = {name: unique('prologue_room_'+name) for name in ('command', 'rest', 'lab')}
    for name in ('command','lab'):
        actor=unique('prologue_room_visual_'+name)
        component=actor.get_component_by_class(unreal.StaticMeshComponent) if actor else None
        mesh=component.get_editor_property('static_mesh') if component else None
        check('dedicated Tripo room with human query collision: '+name,mesh is not None and mesh.get_name()=='SM_prologue_'+name and component.get_collision_enabled()==unreal.CollisionEnabled.QUERY_ONLY)
    corridor=unique('prologue_corridor_visual')
    check('dedicated Tripo connection corridor',corridor is not None and corridor.static_mesh_component.get_editor_property('static_mesh').get_name()=='SM_prologue_corridor')
    door_actors = {name: unique('prologue_room_door_'+name) for name in ('command', 'rest', 'lab')}
    doors = [actor for actor in door_actors.values() if actor]
    airlock_doors=[unique('prologue_room_door_airlock'),unique('prologue_room_door_exit')]
    shell=unique('prologue_airlock_visual')
    check('separate Tripo airlock with two independent door actors',shell is not None and all(airlock_doors) and len({a.get_path_name() for a in airlock_doors if a})==2)
    anchors=read_json(ROOT/'data/engines/prologue-tripo-v1/anchors.json')
    check('derived airlock has two open end portals',all(axis in anchors['airlock']['open_cardinal_axes'] for axis in ('+Y','-Y')))
    check('three independent room door actors', len(doors) == 3 and len({a.get_path_name() for a in doors}) == 3,
          locations_cm={name: xyz(a.get_actor_location()) for name, a in door_actors.items() if a})
    for name, actor in door_actors.items():
        if not actor: continue
        mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
        check('room door movable visual: '+name,
              mesh and mesh.get_editor_property('mobility') == unreal.ComponentMobility.MOVABLE and
              mesh.get_editor_property('static_mesh') and not mesh.is_simulating_physics(),
              collision=str(mesh.get_collision_enabled()) if mesh else None)

    for shot_id in ('mission_traverse', 'mission_science', 'mission_return', 'mission_debrief'):
        first = unique('prologue_cam_'+shot_id+'_start')
        last = unique('prologue_cam_'+shot_id+'_end')
        if first and last:
            points = xyz(first.get_actor_location())+xyz(last.get_actor_location())
            check('finite independent camera pair: '+shot_id,
                  all(math.isfinite(value) for value in points) and
                  first.get_path_name() != last.get_path_name(),
                  start_cm=points[:3], end_cm=points[3:])

    screen = unique('prologue_command_screen')
    material = unreal.load_asset(DEST+'/Materials/M_LiveDataDisplay')
    if screen:
        component = screen.get_component_by_class(unreal.StaticMeshComponent)
        assigned = component.get_material(0) if component else None
        check('command screen uses live display material', material and assigned == material,
              assigned=assigned.get_path_name() if assigned else None)
    if material:
        scalar_names = [str(name) for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)]
        texture_names = [str(name) for name in unreal.MaterialEditingLibrary.get_texture_parameter_names(material)]
        check('live display supports freshness blanking', 'DataFresh' in scalar_names and 'DisplayMap' in texture_names,
              scalar_parameters=scalar_names, texture_parameters=texture_names)
    else:
        check('live display material exists', False)
    board = unique('prologue_mission_board')
    text_material = unreal.load_asset(DEST+'/Materials/M_CabinText')
    if board:
        component = board.get_component_by_class(unreal.TextRenderComponent)
        assigned = component.get_editor_property('text_material') if component else None
        check('mission board has readable text material', text_material and assigned == text_material,
              assigned=assigned.get_path_name() if assigned else None)

    starts = [actor for actor in actors if isinstance(actor, unreal.PlayerStart)]
    check('one PlayerStart', len(starts) == 1, count=len(starts))
    if len(starts) == 1 and rooms['command']:
        start = xyz(starts[0].get_actor_location())
        room_marker = xyz(rooms['command'].get_actor_location())
        # The command marker is local (90,-600,0), a floor-space anchor.
        room_center = [room_marker[0]-90, room_marker[1], room_marker[2]]
        feet_z = start[2]-94  # current EV1 capsule half-height, centimetres.
        inside = (abs(start[0]-room_center[0]) <= 270 and abs(start[1]-room_center[1]) <= 150 and
                  abs(feet_z-room_center[2]) <= 20)
        check('PlayerStart inside command room above floor', inside,
              start_ue_cm=start, inferred_room_center_ue_cm=room_center,
              capsule_half_height_cm=94, feet_above_deck_cm=feet_z-room_center[2])
        point_map = [start[0]/100, -start[1]/100]
        briefing = profile['intro']['briefing_xy_m']
        radius = float(profile['intro'].get('interaction_radius_m', 4.))
        distance = distance_xy(point_map, briefing)
        check('PlayerStart near ROS briefing goal', math.isfinite(distance) and distance <= radius,
              start_map_xy_m=point_map, briefing_xy_m=briefing, distance_m=distance, interaction_radius_m=radius)

    # Hidden plain floor proxies avoid a second visible surface at the Tripo
    # floor while retaining a simple capsule collision plane.
    for name in ('command', 'lab'):
        floors = [a for a in actors if a.get_actor_label() == 'SCENARIO_Prologue_room_floor_'+name]
        expected_hidden=bool(anchors[name]['floor']['point'])
        check('one room floor matching generated-floor availability: '+name, len(floors) == 1 and floors[0].get_editor_property('hidden')==expected_hidden,
              actor_paths=[a.get_path_name() for a in floors])
    probes = import_report.get('command_rooms', {}).get('terrain_clearance_probes', [])
    clearances = [probe.get('deck_above_ground_cm') for probe in probes]
    check('pre-build room terrain probes clear the deck', len(clearances) == 10 and
          all(value is not None and math.isfinite(value) and value >= 10 for value in clearances),
          minimum_clearance_cm=min((v for v in clearances if v is not None and math.isfinite(v)), default=None),
          count=len(clearances), required_clearance_cm=10)

    expected_ids = {'landing', 'rest', 'data', 'airlock', 'ready',
                    'mission_traverse', 'mission_science', 'mission_return', 'mission_debrief'}
    shots = runtime_script.get('shots', [])+runtime_script.get('mission_intros', [])
    source_shots = source_script.get('shots', [])+source_script.get('mission_intros', [])
    check('nine unique runtime voice/script entries', len(shots) == 9 and
          {shot['id'] for shot in shots} == expected_ids and
          {shot['id'] for shot in source_shots} == expected_ids,
          ids=[shot.get('id') for shot in shots])
    phase_map = {shot.get('id'): shot.get('phase') for shot in runtime_script.get('mission_intros', [])}
    check('mission intros use existing ROS phases', phase_map == {
        'mission_traverse': 2, 'mission_science': 3, 'mission_return': 4, 'mission_debrief': 6}, phases=phase_map)
    imported_audio = {entry['path'].rsplit('.', 1)[-1]: entry for entry in import_report.get('audio', [])}
    source_hashes = {entry['path'].replace('\\', '/'): entry['sha256'] for entry in import_report.get('sources', [])}
    voice_provenance_path = ROOT/'assets/narrative/prologue_v1/chatterbox/provenance.json'
    voice_provenance = read_json(voice_provenance_path)
    provenance_clips = {clip['shot_id']: clip for clip in voice_provenance.get('clips', [])}
    check('voice provenance matches current nine-entry script',
          voice_provenance.get('input_script_sha256') == digest(source_script_path) and
          set(provenance_clips) == expected_ids,
          recorded_script_sha256=voice_provenance.get('input_script_sha256'),
          actual_script_sha256=digest(source_script_path))
    for shot in shots:
        name = 'VO_'+shot['id']
        asset = unreal.load_asset(DEST+'/Audio/'+name)
        imported = imported_audio.get(name)
        record = {'id': shot['id'], 'asset': asset.get_path_name() if asset else None,
                  'planned_duration_s': shot.get('duration_s'), 'passed': False}
        REPORT['voices'].append(record)
        if not asset or not isinstance(asset, unreal.SoundWave) or not imported:
            record['error'] = 'Missing imported SoundWave or import source record'
            continue
        source = (ROOT/imported['source']).resolve()
        if not source.is_relative_to(ROOT) or source.suffix.lower() != '.wav':
            record['error'] = 'Narration source path escaped the repository or is not WAV'
            continue
        record.update(source=source.relative_to(ROOT).as_posix(), sha256=digest(source),
                      pcm=inspect_pcm(source), asset_duration_s=float(asset.duration))
        clip = provenance_clips.get(shot['id'], {})
        planned = float(shot['duration_s'])
        record['source_hash_matches_import'] = source_hashes.get(record['source']) == record['sha256']
        record['source_hash_matches_voice_provenance'] = clip.get('sha256') == record['sha256']
        record['passed'] = (record['source_hash_matches_import'] and record['source_hash_matches_voice_provenance'] and
                            record['pcm']['finite'] and record['pcm']['rms'] > .001 and
                            record['pcm']['full_scale_samples'] == 0 and math.isfinite(record['asset_duration_s']) and
                            0 < record['asset_duration_s'] <= planned and
                            abs(record['asset_duration_s']-record['pcm']['duration_s']) < .1 and
                            0 < planned <= 60)
    check('all nine narration assets fit and have finite unclipped PCM sources',
          len(REPORT['voices']) == 9 and all(record['passed'] for record in REPORT['voices']))
    REPORT['passed'] = all(item['passed'] for item in REPORT['checks'])
except Exception as error:
    REPORT.update(error=repr(error), traceback=traceback.format_exc())
finally:
    output = ROOT/'test-results/command-rooms-verification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    unreal.log('REDLINE_COMMAND_ROOMS_VERIFY '+json.dumps(REPORT, ensure_ascii=False, allow_nan=False))
if not REPORT['passed']:
    raise RuntimeError(REPORT.get('error', 'Command-room inspection failed; see command-rooms-verification.json'))
