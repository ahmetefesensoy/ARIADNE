"""SCENARIO prologue: Tripo visuals, authored staging and independent audio.

Raw Tripo, NASA geometry, source character/animations and ROS authority remain
unchanged. Primitive proxies provide human query collision and sliding doors.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import traceback
import sys
import unreal

ROOT = Path(os.environ['REDLINE_REPO'])
sys.path.insert(0,str(ROOT/'scripts'))
from prologue_tripo_import import import_visual,texture_material
from prepare_command_rooms import extend_command_rooms
DEST = '/Game/Prologue'
REPORT = {'created_at_utc':datetime.now(timezone.utc).isoformat(),'passed':False,'status':'SCENARIO',
          'scope':'skippable presentation opening + optional record-player rest; no flight hardware or science data claim',
          'sources':[],'audio':[],'actors':[]}
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.MaterialEditingLibrary


def source(relative):
    p = ROOT/relative
    REPORT['sources'].append({'path':relative,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return p


def material(name, color, rough=.6, metal=0., emission=0.):
    m = unreal.load_asset(DEST+'/Materials/'+name)
    if not m: m = TOOLS.create_asset(name,DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    c = LIB.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
    c.set_editor_property('constant',unreal.LinearColor(*color,1))
    LIB.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for prop,value in ((unreal.MaterialProperty.MP_ROUGHNESS,rough),(unreal.MaterialProperty.MP_METALLIC,metal)):
        n = LIB.create_material_expression(m,unreal.MaterialExpressionConstant)
        n.r = value
        LIB.connect_material_property(n,'',prop)
    if emission:
        e = LIB.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
        e.set_editor_property('constant',unreal.LinearColor(*(v*emission for v in color),1))
        LIB.connect_material_property(e,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m,False)
    return m


try:
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    tripo = {name:import_visual(ROOT,'prologue_'+name,DEST,REPORT) for name in ('turntable','lounge','lander','airlock','command','lab','corridor')}
    runtime = json.loads(source('data/engines/BXW/eva-runtime-v1.json').read_text())
    script = json.loads(source('assets/narrative/prologue_v1/script.json').read_text(encoding='utf-8'))
    audio_dir = ROOT/'assets/narrative/prologue_v1'
    voice_shots = script['shots']+script.get('mission_intros',[])
    voice_ids = {s['id'] for s in voice_shots}
    candidate = audio_dir/'chatterbox/provenance.json'
    voice_dir,voice_method = audio_dir,'Microsoft Tolga local synthetic Turkish voice (fallback)'
    if candidate.exists():
        metadata = json.loads(candidate.read_text(encoding='utf-8'))
        clips = metadata.get('clips',[])
        ready = len(clips)==len(voice_shots) and {c['shot_id'] for c in clips}==voice_ids
        ready = ready and metadata.get('input_script_sha256')==hashlib.sha256((audio_dir/'script.json').read_bytes()).hexdigest()
        for clip in clips:
            path = ROOT/clip['path']
            ready = ready and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==clip['sha256'] and clip['output_stats']['finite'] and clip['output_stats']['clipping_samples']==0
        if ready:
            voice_dir,voice_method = audio_dir/'chatterbox','Chatterbox Multilingual V3 local CUDA synthetic Turkish voice'
            source('assets/narrative/prologue_v1/chatterbox/provenance.json')
    for meta in ('voice_provenance.json','audio_provenance.json'): source('assets/narrative/prologue_v1/'+meta)
    for wav in sorted(audio_dir.glob('*.wav')):
        relative = str(wav.relative_to(ROOT)).replace('\\','/')
        source(relative)
        name = ('VO_' if wav.stem in voice_ids else 'SFX_')+wav.stem
        t = unreal.AssetImportTask()
        chosen = voice_dir/wav.name if name.startswith('VO_') else wav
        if chosen!=wav:source(str(chosen.relative_to(ROOT)).replace('\\','/'))
        t.filename,t.destination_path,t.destination_name = str(chosen),DEST+'/Audio',name
        t.automated = t.replace_existing = True
        t.save = False
        TOOLS.import_asset_tasks([t])
        sound = next(a for a in t.get_objects() if isinstance(a,unreal.SoundWave))
        sound.set_editor_property('looping',wav.stem == 'vardiya_arasi_jazz')
        unreal.EditorAssetLibrary.save_loaded_asset(sound,False)
        REPORT['audio'].append({'path':sound.get_path_name(),'source':str(chosen.relative_to(ROOT)),'duration_s':sound.duration,'looping':wav.stem == 'vardiya_arasi_jazz'})
        if name.startswith('VO_'):
            shot = next(s for s in voice_shots if s['id']==wav.stem)
            if sound.duration>shot['duration_s']-.25:shot['duration_s']=round(sound.duration+.5,2)
    mesh = unreal.load_asset('/Game/EVAFixtures/Astronaut/SK_Astronaut')
    # Duplicate the approved idle; a derived seated pose keeps the original untouched.
    seated_path = DEST+'/AN_SeatedIdle'
    if unreal.EditorAssetLibrary.does_asset_exist(seated_path):
        old = unreal.load_asset(seated_path)
        # Reuse the destination; the native helper resets it from the source
        # clip before authoring the deterministic pose (no repeated root drift).
        seated = old
    else:
        seated = unreal.EditorAssetLibrary.duplicate_asset('/Game/EVAFixtures/Astronaut/AN_Idle',seated_path)
    source_idle = unreal.load_asset('/Game/EVAFixtures/Astronaut/AN_Idle')
    if not unreal.RedlineEVAImportLibrary.make_seated_idle(mesh,source_idle,seated): raise RuntimeError('Existing rig could not form the seated pose')
    unreal.EditorAssetLibrary.save_loaded_asset(seated,False)
    REPORT['seated_animation'] = seated.get_path_name()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/EVAFixtures/BXW_EVA')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for a in list(actors.get_all_level_actors()):
        if isinstance(a,unreal.PlayerStart):continue
        if any(str(tag).startswith('prologue_') for tag in a.tags) or a.get_actor_label() in ('INTRO_habitat','INTRO_map_table'): actors.destroy_actor(a)
    hx,hy = runtime['intro'].get('habitat_xy_m',runtime['spawn_map_xyz_m'][:2])
    # A separate scenario annex near the habitat, not a NASA interior reconstruction.
    ox,oy = hx-6,hy-8
    ground = unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(ox,oy,runtime['spawn_map_xyz_m'][2]),100)
    if not isinstance(ground,unreal.Vector): raise RuntimeError('No terrain under the scenario annex')
    origin = unreal.Vector(ox*100,-oy*100,ground.z*100+60)
    ground_samples = []
    for px in (-310,0,450,750,1000):
        for py in (-790,-600,0,600,790):
            sample = unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(ox+px/100,oy-py/100,runtime['spawn_map_xyz_m'][2]),100)
            if not isinstance(sample,unreal.Vector):raise RuntimeError('No terrain under expanded habitat')
            ground_samples.append(sample.z*100)
    origin.z = max(origin.z,max(ground_samples)+40)
    REPORT['deck_terrain_clearance'] = {'sample_count':len(ground_samples),'minimum_sampled_clearance_cm':origin.z-max(ground_samples),'deck_map_z_m':origin.z/100}
    cube = unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    cylinder = unreal.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
    mats = {
        'wall':material('M_WarmCabin',(.42,.44,.46),.78),
        'floor':material('M_CabinFloor',(.11,.13,.15),.84),
        'frame':material('M_GraphiteFrame',(.035,.045,.055),.42,.5),
        'door':material('M_AirlockPaint',(.58,.62,.65),.38),
        'red':material('M_RedSafety',(.34,.035,.02),.5),
        'wood':material('M_RecordWalnut',(.14,.045,.018),.4),
        'vinyl':material('M_Vinyl',(.012,.014,.018),.23),
        'label':material('M_RecordLabel',(.7,.39,.12),.7),
        'cushion':material('M_SeatFabric',(.035,.075,.1),.92),
        'light':material('M_WarmPractical',(.95,.6,.26),.3,0,1200),
        'blue':material('M_BluePractical',(.03,.32,.42),.3,0,1300),
    }
    def point(local): return origin+unreal.Vector(*local)
    def solid(name,local,size,mat='wall',shape=None,tag=None,movable=False):
        a = actors.spawn_actor_from_class(unreal.StaticMeshActor,point(local))
        a.set_actor_label('SCENARIO_Prologue_'+name)
        a.set_editor_property('tags',[unreal.Name(tag or 'prologue_'+name)])
        c = a.static_mesh_component
        c.set_static_mesh(shape or cube)
        c.set_material(0,mats[mat])
        c.set_simulate_physics(False)
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION if movable or mat in ('light','blue') else unreal.CollisionEnabled.QUERY_ONLY)
        if movable:c.set_mobility(unreal.ComponentMobility.MOVABLE)
        a.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)))
        REPORT['actors'].append({'name':name,'tag':tag,'local_cm':local,'size_cm':size})
        return a
    def visual(name,local,movable=False):
        a = actors.spawn_actor_from_class(unreal.StaticMeshActor,point(local))
        a.set_actor_label('SCENARIO_Tripo_'+name);a.set_editor_property('tags',[unreal.Name('prologue_'+name)])
        c = a.static_mesh_component;c.set_static_mesh(tripo[name]);c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);c.set_simulate_physics(False)
        if movable:c.set_mobility(unreal.ComponentMobility.MOVABLE)
        return a
    solid('foundation',(150,0,-40),(930,390,70),'frame')
    solid('lounge_floor',(0,0,-6),(600,360,12),'floor')
    solid('lounge_ceiling',(0,0,286),(600,360,12))
    solid('lounge_back',(-306,0,140),(12,360,280))
    for y in (-186,186):
        solid('lounge_wall_'+str(y),(0,y,140),(600,12,280))
        for x in (-270,-150,-30,90,210):
            solid('rib_'+str(x)+'_'+str(y),(x,y*.95,140),(5,7,280),'frame')
    solid('lock_floor',(450,0,-6),(300,240,12),'floor')
    solid('lock_ceiling',(450,0,286),(300,240,12))
    for y in (-126,126):solid('lock_wall_'+str(y),(450,y,140),(300,12,280))
    for x,label in ((300,'inner'),(600,'outer')):
        for y in (-150,150):solid(label+'_frame_'+str(y),(x,y,140),(20,60,280),'frame')
        solid(label+'_lintel',(x,0,262),(20,240,36),'frame')
        solid(label+'_door',(x,0,120),(10,210,240),'door',tag='prologue_'+label+'_door',movable=True)
        # Safety stripes are attached to sliding doors by the scene hierarchy.
    # Comfortable suited-height chair; actor marker is a floor-space rig origin.
    for x in (-128,-70):
        for y in (-112,-48):solid('chair_leg_'+str(x)+'_'+str(y),(x,y,23),(6,6,46),'frame')
    solid('chair_seat',(-100,-80,49),(72,84,14),'cushion')
    solid('chair_back',(-138,-80,101),(14,84,100),'cushion')
    for y in (-125,-35):solid('chair_arm_'+str(y),(-100,y,76),(78,8,10),'frame')
    # Tripo owns visual architecture/console; clean authored proxies own human
    # collision. Keep proxies hidden so there is only one visible wall surface.
    for a in actors.get_all_level_actors():
        label = a.get_actor_label()
        if label.startswith('SCENARIO_Prologue_lounge_') or label.startswith('SCENARIO_Prologue_rib_'):
            a.set_actor_hidden_in_game(True)
    lounge = visual('lounge',(0,0,0))
    lounge.set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False)
    lb = tripo['lounge'].get_bounding_box();ls = lb.max-lb.min
    lounge.set_actor_scale3d(unreal.Vector(360/ls.x,600/ls.y,280/ls.z))
    probes = json.loads(source('data/engines/prologue-tripo-v1/anchors.json').read_text())
    lounge_floor = probes['lounge']['floor']['point'][2]*100*(280/ls.z)
    lounge.set_actor_location(point((0,0,-lounge_floor)),False,False)
    table = visual('turntable',(-90,65,0))
    table.set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False)
    REPORT['visual_layout'] = {'lounge_dimensions_cm':[600,360,280],'lounge_scale':'explicit nonuniform scenario set fit',
        'floor_anchor_cm':lounge_floor,'front_review':'Blender +Y front becomes UE -Y in FBX handedness conversion; actor yaw +90 faces world +X'}
    table_top = tripo['turntable'].get_bounding_box().max.z
    disc_z = probes['turntable']['top']['point'][2]*100+.2
    disc = solid('record',(-90,65,disc_z),(30,30,.35),'vinyl',cylinder,'prologue_record',True)
    plane = unreal.load_asset('/Engine/BasicShapes/Plane.Plane')
    label_mat = texture_material(ROOT,DEST,'ChetBakerLabel',source('assets/narrative/prologue_v1/chet_baker_label.png'),True)
    label = solid('record_label',(-90,65,disc_z+.3),(9,9,1),'label',plane,movable=True)
    label.static_mesh_component.set_material(0,label_mat)
    label.attach_to_actor(disc,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    sleeve_mat = texture_material(ROOT,DEST,'ChetBakerSleeve',source('assets/narrative/prologue_v1/chet_baker_sleeve.png'),True)
    solid('sleeve_stand',(-101,119,21.5),(18,36,43),'wood')
    sleeve = solid('chet_baker_sleeve',(-101,119,59),(32,32,1),'label',plane)
    sleeve.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=90),False)
    sleeve.static_mesh_component.set_material(0,sleeve_mat)
    # Two data displays: one consumes the real FieldTile at runtime.
    for y in (-90,90):solid('screen_frame_'+str(y),(282,y,160),(12,156,110),'frame')
    screen_mat = unreal.load_asset(DEST+'/Materials/M_LiveDataDisplay')
    if not screen_mat:screen_mat = TOOLS.create_asset('M_LiveDataDisplay',DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(screen_mat)
    tex = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionTextureSampleParameter2D)
    tex.set_editor_property('parameter_name','DisplayMap')
    tex.texture = unreal.load_asset('/Engine/EngineResources/DefaultTexture.DefaultTexture')
    screen_mat.set_editor_property('two_sided',True)
    coords = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionTextureCoordinate)
    mul = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionMultiply)
    amount = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionConstant)
    amount.r = 800.
    LIB.connect_material_expressions(tex,'RGB',mul,'A');LIB.connect_material_expressions(amount,'',mul,'B')
    fresh = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionScalarParameter);fresh.set_editor_property('parameter_name','DataFresh');fresh.set_editor_property('default_value',0.)
    fresh_mul = LIB.create_material_expression(screen_mat,unreal.MaterialExpressionMultiply)
    LIB.connect_material_expressions(mul,'',fresh_mul,'A');LIB.connect_material_expressions(fresh,'',fresh_mul,'B')
    LIB.connect_material_property(fresh_mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(screen_mat);unreal.EditorAssetLibrary.save_loaded_asset(screen_mat,False)
    # A plane's XY spans the display, rotated to face the lounge. World axes
    # orientation is for this narrative display only, not the authoritative map.
    plane = unreal.load_asset('/Engine/BasicShapes/Plane.Plane')
    panel = solid('data_screen',(274,-90,160),(140,95,1),'frame',plane,'prologue_data_screen')
    panel.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=90),False)
    panel.static_mesh_component.set_material(0,screen_mat)
    # Re-derive from the engine font graph so brightness never accumulates.
    text_path=DEST+'/Materials/M_CabinText'
    if unreal.EditorAssetLibrary.does_asset_exist(text_path):
        if not unreal.EditorAssetLibrary.delete_asset(text_path):raise RuntimeError('Cannot rebuild derived font material')
    textmat=unreal.EditorAssetLibrary.duplicate_asset('/Engine/EngineMaterials/DefaultTextMaterialOpaque',text_path)
    old=LIB.get_material_property_input_node(textmat,unreal.MaterialProperty.MP_EMISSIVE_COLOR) or LIB.get_material_property_input_node(textmat,unreal.MaterialProperty.MP_BASE_COLOR)
    if not old:raise RuntimeError('Engine font colour graph unavailable')
    # Preserve the engine font's glyph/opacity graph; make its colour readable
    # at the physically exposed Mars scene brightness without lighting the room.
    textmat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    textmat.set_editor_property('two_sided',True)
    gain=LIB.create_material_expression(textmat,unreal.MaterialExpressionMultiply)
    amount=LIB.create_material_expression(textmat,unreal.MaterialExpressionConstant);amount.r=700.
    LIB.connect_material_expressions(old,'',gain,'A');LIB.connect_material_expressions(amount,'',gain,'B')
    LIB.connect_material_property(gain,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(textmat);unreal.EditorAssetLibrary.save_loaded_asset(textmat,False)
    values = actors.spawn_actor_from_class(unreal.TextRenderActor,point((271,150,198)),unreal.Rotator(pitch=0,yaw=180,roll=0))
    values.set_actor_label('SCENARIO_Prologue_LiveValues');values.set_editor_property('tags',[unreal.Name('prologue_data_text')])
    component = values.get_component_by_class(unreal.TextRenderComponent)
    component.set_text('BXW / CANLI VERI\nVeri bekleniyor')
    component.set_world_size(9)
    component.set_text_material(textmat)
    # Practical ceiling strips and local, motivated light sources.
    for x in (-160,80,440):
        solid('ceiling_strip_'+str(x),(x,0,275),(110,10,3),'light')
        lamp = actors.spawn_actor_from_class(unreal.PointLight,point((x,0,230)))
        lamp.set_actor_label('SCENARIO_Prologue_Practical_'+str(x));lamp.set_editor_property('tags',[unreal.Name('prologue_lamp_'+str(x))])
        lamp.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        lamp.light_component.set_intensity(18000.)
        lamp.light_component.set_light_color(unreal.LinearColor(1,.78,.5,1))
        lamp.light_component.set_editor_property('attenuation_radius',450.)
    solid('airlock_status',(590,-112,155),(10,5,60),'blue')
    def marker(name,local,look=None):
        p = point(local)
        rot = unreal.MathLibrary.find_look_at_rotation(p,point(look)) if look else unreal.Rotator(pitch=0,yaw=0,roll=0)
        a = actors.spawn_actor_from_class(unreal.TargetPoint,p,rot)
        a.set_actor_label('SCENARIO_'+name);a.set_editor_property('tags',[unreal.Name(name)])
    marker('prologue_seat',(-100,-80,0))
    marker('prologue_stand',(500,60,0))
    # Landing is a fictional presentation set on the measured terrain. It never
    # sets robot physics poses, mission time or a flight-controller state.
    land_local = (1900,1600,0)
    land_x,land_y = ox+land_local[0]/100,oy-land_local[1]/100
    land_ground = unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(land_x,land_y,runtime['spawn_map_xyz_m'][2]),100)
    if not isinstance(land_ground,unreal.Vector):raise RuntimeError('No terrain under landing set')
    land_z = land_ground.z*100-origin.z+4
    visual('lander',(land_local[0],land_local[1],land_z),True)
    marker('prologue_landing_target',(land_local[0],land_local[1],land_z))
    marker('prologue_cam_landing_start',(land_local[0]+1600,land_local[1]-1500,land_z+1000),land_local)
    marker('prologue_cam_landing_end',(land_local[0]+1000,land_local[1]-1000,land_z+350),land_local)
    bounce = actors.spawn_actor_from_class(unreal.PointLight,point((land_local[0]+800,land_local[1]-700,land_z+700)))
    bounce.set_actor_label('SCENARIO_Prologue_LandingBounce');bounce.set_editor_property('tags',[unreal.Name('prologue_landing_bounce')])
    bounce.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);bounce.light_component.set_intensity(3000000.)
    bounce.light_component.set_light_color(unreal.LinearColor(1.,.83,.66,1));bounce.light_component.set_editor_property('attenuation_radius',2400.)
    dust = material('M_LandingDust',(.25,.08,.02),1)
    dust.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);dust.set_editor_property('two_sided',True)
    opacity = LIB.create_material_expression(dust,unreal.MaterialExpressionScalarParameter);opacity.set_editor_property('parameter_name','DustAmount');opacity.set_editor_property('default_value',0.)
    uv = LIB.create_material_expression(dust,unreal.MaterialExpressionTextureCoordinate)
    center = LIB.create_material_expression(dust,unreal.MaterialExpressionConstant2Vector);center.set_editor_property('r',.5);center.set_editor_property('g',.5)
    distance = LIB.create_material_expression(dust,unreal.MaterialExpressionDistance)
    LIB.connect_material_expressions(uv,'',distance,'A');LIB.connect_material_expressions(center,'',distance,'B')
    twice = LIB.create_material_expression(dust,unreal.MaterialExpressionMultiply);twice.set_editor_property('const_b',2.)
    LIB.connect_material_expressions(distance,'',twice,'A')
    inverse = LIB.create_material_expression(dust,unreal.MaterialExpressionOneMinus);LIB.connect_material_expressions(twice,'',inverse,'')
    clamp = LIB.create_material_expression(dust,unreal.MaterialExpressionClamp);LIB.connect_material_expressions(inverse,'',clamp,'')  # UE 5.8: primary pins are unnamed
    density = LIB.create_material_expression(dust,unreal.MaterialExpressionMultiply)
    LIB.connect_material_expressions(clamp,'',density,'A');LIB.connect_material_expressions(opacity,'',density,'B')
    LIB.connect_material_property(density,'',unreal.MaterialProperty.MP_OPACITY)
    LIB.recompile_material(dust);unreal.EditorAssetLibrary.save_loaded_asset(dust,False)
    for i in range(4):
        a = solid('dust_'+str(i),(land_local[0],land_local[1],land_z+40+i*45),(1100+i*200,1100+i*200,1),'floor',plane,'prologue_dust_'+str(i),True)
        a.static_mesh_component.set_material(0,dust)
    # A longer ramp follows the actual deck-to-terrain rise (<20 degrees), so
    # raising the base above the expanded terrain cannot strand the character.
    import math
    run = 260.
    for _ in range(4):
        end = unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(ox+(900+run)/100,oy,runtime['spawn_map_xyz_m'][2]),100)
        if not isinstance(end,unreal.Vector):raise RuntimeError('No terrain at habitat ramp endpoint')
        rise = origin.z-end.z*100
        run = max(260.,abs(rise)/math.tan(math.radians(17)))
    pitch = math.degrees(math.atan2(-rise,run))
    ramp = solid('entry_ramp',(900+run/2,0,-rise/2-6),(math.hypot(run,rise)+20,160,12),'floor')
    ramp.set_actor_rotation(unreal.Rotator(pitch=pitch,yaw=0,roll=0),False)
    REPORT['ramp'] = {'run_cm':run,'rise_cm':rise,'pitch_deg':pitch,'terrain_endpoint_map_z_m':end.z}
    for name,a,b,target in [
        ('rest',(150,-90,145),(130,-100,140),(-85,-10,80)),
        ('data',(-70,0,155),(-30,5,152),(278,0,160)),
        ('airlock',(330,-85,150),(365,-70,145),(525,0,140)),
        ('ready',(630,-60,150),(700,-40,155),(1050,20,120)),
    ]:
        marker('prologue_cam_'+name+'_start',a,target)
        marker('prologue_cam_'+name+'_end',b,target)
    extend_command_rooms(ROOT,DEST,REPORT,actors,world,origin,mats,tripo,material,solid,marker)
    # Begin in the real, traversable command room, facing the mission wall.
    starts = [a for a in actors.get_all_level_actors() if isinstance(a,unreal.PlayerStart)]
    start = starts[0] if starts else actors.spawn_actor_from_class(unreal.PlayerStart,point((110,-600,94)))
    start.set_actor_location(point((110,-600,94)),False,False);start.set_actor_rotation(unreal.Rotator(pitch=0,yaw=180,roll=0),False)
    start.set_editor_property('tags',[unreal.Name('prologue_player_start')])
    REPORT['player_start_map_xyz_m'] = [start.get_actor_location().x/100,-start.get_actor_location().y/100,(start.get_actor_location().z-94)/100]
    tagged = {str(tag):a for a in actors.get_all_level_actors() for tag in a.tags}
    for suffix in ('start','end'):
        dst = tagged['prologue_cam_data_'+suffix];src = tagged['prologue_cam_mission_traverse_'+suffix]
        dst.set_actor_location(src.get_actor_location(),False,False);dst.set_actor_rotation(src.get_actor_rotation(),False)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/EVAFixtures/BXW_EVA'):raise RuntimeError('Cannot save prologue map')
    if not unreal.EditorAssetLibrary.save_directory(DEST,False,True):raise RuntimeError('Cannot save all prologue dependencies')
    # Explicitly stage the small subtitle/timing script for runtime reads.
    content = Path(unreal.Paths.project_content_dir())/'Prologue'
    content.mkdir(parents=True,exist_ok=True)
    (content/'script.json').write_text(json.dumps(script,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    REPORT.update(passed=True,origin_map_xyz_m=[ox,oy,origin.z/100],map='/Game/EVAFixtures/BXW_EVA',
                  narrative_duration_s=sum(s['duration_s'] for s in script['shots']),narration_method=voice_method,
                  mission_intros=[{'id':s['id'],'phase':s['phase'],'duration_s':s['duration_s']} for s in script.get('mission_intros',[])],
                  jazz_method='original local procedural instrumental; 0 credits',flight_airlock_simulation=False)
except Exception as e:
    REPORT.update(error=repr(e),traceback=traceback.format_exc())
finally:
    (ROOT/'test-results/prologue-import.json').write_text(json.dumps(REPORT,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    unreal.log('REDLINE_PROLOGUE '+json.dumps(REPORT))
if not REPORT['passed']:raise RuntimeError(REPORT.get('error','Prologue preparation failed'))
