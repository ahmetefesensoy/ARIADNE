"""Modular SCENARIO rooms for the REDLINE narrative preview.

Called by prepare_prologue_scene.py after the original prologue setup. This
helper reuses the approved Tripo lounge mesh and existing cabin materials;
it never generates a model, modifies a source asset, or commands ROS/Gazebo.
The rooms/doors are set staging, not a pressure-vessel or flight-system model.
"""
from __future__ import annotations

import hashlib
import json

import unreal


def extend_command_rooms(ROOT, DEST, REPORT, actors, world, origin, mats,
                         tripo, material, solid, marker):
    """Add command and sample-preparation rooms to the existing lounge annex.

    Coordinates are local Unreal centimetres relative to the annex origin.
    All three pavilion openings face +X into the 3 m wide shared corridor.
    Collision uses plain floor/wall proxies; Tripo visuals stay non-physical.
    The caller owns saving the level/assets and wiring live board values.
    """
    report = {
        'status': 'SCENARIO',
        'purpose': 'command wall, crew lounge, sample-preparation room and shared access corridor',
        'physics': 'human query collision only; no pressure simulation or robot authority',
        'room_floor_height_local_cm': 0,
        'room_door_clear_opening_cm': [210, 240],
        'rooms': [], 'markers': [], 'lights': [], 'removed_actors': [],
        'terrain_clearance_probes': [],
    }
    REPORT['command_rooms'] = report
    helper_path = ROOT/'scripts/prepare_command_rooms.py'
    REPORT.setdefault('sources', []).append({
        'path': 'scripts/prepare_command_rooms.py',
        'sha256': hashlib.sha256(helper_path.read_bytes()).hexdigest(),
    })
    runtime_path = ROOT/'data/engines/BXW/eva-runtime-v1.json'
    runtime = json.loads(runtime_path.read_text(encoding='utf-8'))
    text_material = unreal.load_asset(DEST+'/Materials/M_CabinText')
    screen_material = unreal.load_asset(DEST+'/Materials/M_LiveDataDisplay')
    if not text_material or not screen_material or not tripo.get('lounge'):
        raise RuntimeError('Command rooms require the prepared cabin text, live display and Tripo lounge')
    plane = unreal.load_asset('/Engine/BasicShapes/Plane.Plane')
    cylinder = unreal.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
    lounge_box = tripo['lounge'].get_bounding_box()
    lounge_size = lounge_box.max-lounge_box.min
    if min(lounge_size.x, lounge_size.y, lounge_size.z) <= 0:
        raise RuntimeError('Invalid approved lounge dimensions')
    lounge_floor_anchor = float(REPORT['visual_layout']['floor_anchor_cm'])
    visual_anchors=json.loads((ROOT/'data/engines/prologue-tripo-v1/anchors.json').read_text())

    def point(local):
        return origin+unreal.Vector(*local)

    # Probe before adding room/corridor collision. The shared trace helper hits
    # Visibility surfaces, so probing after construction would measure the new
    # ceiling rather than the terrain below the deck.
    for name, room_y in (('command', -600), ('lab', 600)):
        for dx, dy in ((0, 0), (-260, -140), (-260, 140), (260, -140), (260, 140)):
            ue = point((dx, room_y+dy, 0))
            map_point = unreal.Vector(ue.x/100, -ue.y/100, ue.z/100)
            ground = unreal.RedlineCoords.trace_terrain_height(world, map_point, 100)
            report['terrain_clearance_probes'].append({
                'room': name, 'local_xy_cm': [dx, room_y+dy],
                'ground_map_z_m': ground.z if isinstance(ground, unreal.Vector) else None,
                'deck_above_ground_cm': origin.z-ground.z*100 if isinstance(ground, unreal.Vector) else None,
                'trace_stage': 'before new room/corridor collision',
            })

    def add_marker(tag, local, look=None):
        marker(tag, local, look)
        report['markers'].append({'tag': tag, 'local_cm': list(local),
                                  'look_at_local_cm': list(look) if look else None})

    def text(name, local, content, size=10, yaw=0, color=(.87, .91, .93), tag=None):
        actor = actors.spawn_actor_from_class(
            unreal.TextRenderActor, point(local),
            unreal.Rotator(pitch=0, yaw=yaw, roll=0))
        actor.set_actor_label('SCENARIO_Prologue_'+name)
        actor.set_editor_property('tags', [unreal.Name(tag or 'prologue_'+name)])
        component = actor.get_component_by_class(unreal.TextRenderComponent)
        # EVerticalTextAligment::EVRTA_TextTop (UE 5.8 header) anchors the
        # first glyph row here; later lines must descend into the board.
        component.set_editor_property('vertical_alignment', unreal.VerticalTextAligment.EVRTA_TEXT_TOP)
        component.set_text(content)
        component.set_world_size(size)
        component.set_text_material(text_material)
        component.set_text_render_color(unreal.Color(*(int(v*255) for v in color), 255))
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        return actor

    def lamp(name, local, intensity=16000, color=(1., .79, .54), radius=420):
        actor = actors.spawn_actor_from_class(unreal.PointLight, point(local))
        actor.set_actor_label('SCENARIO_Prologue_'+name)
        actor.set_editor_property('tags', [unreal.Name('prologue_'+name)])
        actor.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        actor.light_component.set_intensity(float(intensity))
        actor.light_component.set_light_color(unreal.LinearColor(*color, 1))
        actor.light_component.set_editor_property('attenuation_radius', float(radius))
        report['lights'].append({'name': name, 'local_cm': list(local),
                                 'intensity_lm': intensity, 'radius_cm': radius})

    def hidden_wall(name, local, size):
        actor = solid(name, local, size, 'wall')
        actor.set_actor_hidden_in_game(True)
        return actor

    def static_visual(name, mesh, local, yaw=0, scale=None):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, point(local))
        actor.set_actor_label('SCENARIO_Prologue_'+name)
        actor.set_editor_property('tags', [unreal.Name('prologue_'+name)])
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_simulate_physics(False)
        architecture=mesh in [tripo.get(key) for key in ('command','lab','corridor')]
        if architecture:actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY if architecture else unreal.CollisionEnabled.NO_COLLISION)
        actor.set_actor_rotation(unreal.Rotator(pitch=0, yaw=yaw, roll=0), False)
        if scale: actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    # Proxies must bound the usable interior, not the outer Tripo shell. Its
    # measured inside rear wall/side wall/ceiling are approximately -260,
    # +/-154 and 240 cm after the approved room fit. This also keeps a follow
    # camera from entering the visible wall before it reaches outer collision.
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        if label == 'SCENARIO_Prologue_lounge_back':
            actor.set_actor_location(point((-266, 0, 140)), False, False)
        elif label == 'SCENARIO_Prologue_lounge_ceiling':
            actor.set_actor_location(point((0, 0, 246)), False, False)
        elif label in ('SCENARIO_Prologue_lounge_wall_-186', 'SCENARIO_Prologue_lounge_wall_186'):
            side = -160 if label.endswith('-186') else 160
            actor.set_actor_location(point((0, side, 140)), False, False)
    report['proxy_interior'] = {'back_inner_face_x_cm': -260,
                                'side_inner_face_y_cm': [-154, 154],
                                'ceiling_lower_face_z_cm': 240}

    # The original short lock becomes the centre of a shared corridor. Remove
    # only its four named pieces; preserve doors, marker poses and source assets.
    remove_labels = {'SCENARIO_Prologue_lock_floor', 'SCENARIO_Prologue_lock_ceiling',
                     'SCENARIO_Prologue_lock_wall_-126', 'SCENARIO_Prologue_lock_wall_126'}
    for actor in list(actors.get_all_level_actors()):
        if actor.get_actor_label() in remove_labels:
            report['removed_actors'].append(actor.get_actor_label())
            actors.destroy_actor(actor)
        elif 'prologue_inner_door' in [str(tag) for tag in actor.tags]:
            # Retain the original cinematic tag and add a separate runtime
            # proximity-door tag so the lounge is part of the room network.
            tags = list(actor.tags)
            tags.append(unreal.Name('prologue_room_door_rest'))
            actor.set_editor_property('tags', tags)

    # 15.6 m corridor with 2.4 m pavilion openings. Flat floors are continuous at
    # x=300, so the capsule need not climb a decorative doorway threshold.
    solid('shared_corridor_floor', (450, 0, -6), (300, 1560, 12), 'floor')
    solid('shared_corridor_ceiling', (450, 0, 286), (300, 1560, 12), 'wall')
    solid('shared_corridor_foundation', (450, 0, -60), (312, 1572, 108), 'frame')
    for y in (-786, 786):
        solid('corridor_end_'+str(y), (450, y, 140), (312, 12, 280), 'wall')
    # Front wall keeps the original central EVA door, whose opening is +/-120.
    for y in (-450, 450):
        solid('corridor_front_'+str(y), (606, y, 140), (12, 660, 280), 'wall')
    for y, length in ((-750, 60), (-300, 360), (300, 360), (750, 60)):
        solid('corridor_back_'+str(y), (306, y, 140), (12, length, 280), 'frame')
    for y in (-600, 0, 600):
        solid('corridor_wayfinding_'+str(y), (590, y, 265), (8, 180, 4), 'blue')
        lamp('corridor_light_'+str(y), (450, y, 232), 12500, (1., .82, .61), 390)
    corridor_mesh=tripo['corridor'];box=corridor_mesh.get_bounding_box();cs=box.max-box.min
    long_x=cs.x>=cs.y
    corridor_scale=(1560/cs.x,600/cs.y,435/cs.z) if long_x else (600/cs.x,1560/cs.y,435/cs.z)
    floor_anchor=visual_anchors['corridor']['floor']['point'][2]*100*corridor_scale[2]
    static_visual('corridor_visual',corridor_mesh,(450,0,-floor_anchor),yaw=90 if long_x else 0,scale=corridor_scale)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(('SCENARIO_Prologue_shared_corridor_','SCENARIO_Prologue_corridor_front_','SCENARIO_Prologue_corridor_back_','SCENARIO_Prologue_corridor_end_')):
            actor.set_actor_hidden_in_game(True)
    report['corridor_visual']={'source':'prologue_corridor','scale':list(corridor_scale),'yaw':90 if long_x else 0,'floor_anchor_cm':floor_anchor,'outer_dimensions_cm':[600,1560,435],'inner_passage_target_cm':[300,1560,240]}
    text('room_name_rest', (318, 112, 263), '02  /  MÜRETTEBAT', 11.5, yaw=0,
         color=(.91, .79, .51))
    text('room_subtitle_rest', (317, 110, 245), 'DİNLENME  ·  PLAK KOLEKSİYONU', 5.1, yaw=0,
         color=(.59, .80, .84))
    add_marker('prologue_room_rest', (90, 0, 0))
    report['rooms'].append({'id': 'rest', 'title': '02 / MÜRETTEBAT',
                            'center_local_cm': [0, 0, 0], 'dimensions_cm': [600, 360, 280],
                            'existing_room': True, 'door_tag': 'prologue_room_door_rest'})

    mats['command_amber'] = material('M_CommandAmber', (.78, .39, .10), .38, 0, 1000)
    mats['command_cyan'] = material('M_CommandCyan', (.025, .24, .29), .32, 0, 1000)
    mats['board_dark'] = material('M_CommandBoardDark',(.012,.019,.025),.95,0,40)
    mats['board_dark'].set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    unreal.MaterialEditingLibrary.recompile_material(mats['board_dark'])

    room_definitions = (
        ('command', -600, '01  /  ANA KOMUTA', 'GÖREV DUVARI  ·  HARİTA  ·  EKİP'),
        ('lab', 600, '03  /  BİLİM HAZIRLIK', 'NUMUNE KABUL  ·  ALET HAZIRLIĞI'),
    )
    for name, y, title, subtitle in room_definitions:
        mesh=tripo[name];box=mesh.get_bounding_box();size=box.max-box.min
        outer_height=335. if name=='command' else 280.
        floor_point=visual_anchors[name]['floor']['point']
        anchor=floor_point[2]*100*(outer_height/size.z) if floor_point else 0.
        static_visual('room_visual_'+name,mesh,(0,y,-anchor),yaw=90,scale=(360/size.x,600/size.y,outer_height/size.z))
        # Visual walls have an open +X front; proxy walls close the other three
        # sides and stop the player walking through the non-colliding art.
        floor = solid('room_floor_'+name, (0, y, -6), (600, 360, 12), 'floor')
        floor.set_actor_hidden_in_game(bool(floor_point))  # Missing generated floor uses the authored deck.
        solid('room_foundation_'+name, (0, y, -65), (612, 372, 118), 'frame')
        hidden_wall('room_back_proxy_'+name, (-266, y, 120), (12, 320, 240))
        hidden_wall('room_ceiling_proxy_'+name, (0, y, 246), (600, 320, 12))
        for side in (-160, 160):
            hidden_wall('room_side_proxy_'+name+'_'+str(side), (0, y+side, 120), (540, 12, 240))
        for side in (-150, 150):
            solid('room_portal_'+name+'_'+str(side), (300, y+side, 140), (20, 60, 280), 'frame')
        solid('room_portal_lintel_'+name, (300, y, 262), (20, 240, 36), 'frame')
        door = solid('room_door_'+name, (300, y, 120), (10, 210, 240), 'door',
                     tag='prologue_room_door_'+name, movable=True)
        door.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        # A small lighted threshold and high-mounted name make the room readable
        # from the corridor without blocking the central 2.1 m walking path.
        solid('room_portal_light_'+name, (311, y, 245), (4, 188, 4), 'command_cyan')
        text('room_name_'+name, (318, y+112, 263), title, 11.5, yaw=0,
             color=(.91, .79, .51))
        text('room_subtitle_'+name, (317, y+110, 245), subtitle, 5.1, yaw=0,
             color=(.59, .80, .84))
        lamp('room_light_'+name+'_front', (95, y, 205), 13000, (1., .85, .72), 430)
        lamp('room_light_'+name+'_rear', (-110, y, 190), 10000, (1., .88, .77), 360)
        add_marker('prologue_room_'+name, (90, y, 0))
        report['rooms'].append({'id': name, 'title': title,
                                'center_local_cm': [0, y, 0],
                                'dimensions_cm': [600, 360, outer_height],
                                'source_visual': 'prologue_'+name+' (dedicated Tripo interior)',
                                'door_tag': 'prologue_room_door_'+name})

    # Command room hero wall. A large live field plane sits beside a text block
    # updated from ROS at runtime; initial content refuses to invent mission data.
    solid('command_wall_frame', (-251, -600, 145), (13, 292, 180), 'frame')
    solid('command_wall_backing', (-242, -600, 145), (4, 284, 170), 'board_dark')
    solid('command_wall_header', (-237, -600, 228), (3, 274, 3), 'command_amber')
    solid('command_wall_footer', (-237, -600, 66), (3, 274, 2), 'command_cyan')
    screen = solid('command_screen', (-237, -670, 140), (125, 116, 1), 'frame',
                   plane, 'prologue_command_screen')
    screen.set_actor_rotation(unreal.Rotator(pitch=0, yaw=90, roll=90), False)
    screen.static_mesh_component.set_material(0, screen_material)
    screen.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    text('command_wall_title', (-235, -463, 222), 'REDLINE  /  GÖREV DUVARI', 12.0, yaw=0,
         color=(.94, .77, .40))
    # TextRender's horizontal glyph direction is local -Y. Start the status
    # block at the right edge so it grows into the right-hand panel, not map.
    board = text('mission_board', (-234, -463, 191),
         'CANLI GÖREV\nROS verisi bekleniyor\n\n[J] Görev günlüğü\nBXW / EVA provası',
         9.0, yaw=0, tag='prologue_mission_board')
    board.get_component_by_class(unreal.TextRenderComponent).set_x_scale(.84)
    text('command_map_title', (-234, -607, 207), 'DÖNÜŞ ALANI', 7.2, yaw=0,
         color=(.50, .80, .84))
    text('command_data_credit', (-234, -463, 87),
         'Türetilmiş arazi / Senaryo ekip\nEski veri görev onayı değildir', 5.0, yaw=0,
         color=(.60, .71, .74))
    report['mission_wall'] = {
        'frame_top_local_z_cm': 235, 'room_ceiling_inner_z_cm': 240,
        'frame_front_local_x_cm': -244.5, 'live_plane_local_x_cm': -237,
        'text_local_x_cm': -234, 'faces_world_positive_x': True,
        'status_glyph_height_cm': 9, 'status_horizontal_scale': .84,
        'layout_note': 'Title/header fit below ceiling; map and status occupy separate halves; text grows local -Y',
    }
    # The generated rear wall has protruding upholstery/porthole geometry.
    # Keep the full board in front of that measured silhouette, not behind it.
    board_labels={'command_wall_frame','command_wall_backing','command_wall_header','command_wall_footer',
                  'command_screen','command_wall_title','mission_board','command_map_title','command_data_credit'}
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label() in {'SCENARIO_Prologue_'+name for name in board_labels}:
            actor.set_actor_location(actor.get_actor_location()+unreal.Vector(100,0,0),False,False)
    report['mission_wall']['front_offset_from_initial_cm']=100
    # Low, uncluttered map-table furniture leaves 1.0+ m access around the hero wall.
    solid('command_table_top', (-35, -600, 79), (150, 102, 8), 'frame')
    for y in (-633, -567):
        solid('command_table_leg_'+str(y), (-35, y, 37), (18, 12, 74), 'frame')
    solid('command_table_inset', (-35, -600, 84), (128, 80, 2), 'floor')
    solid('command_table_edge_light', (28, -600, 85), (2, 74, 1), 'command_cyan')
    text('command_table_label', (43, -550, 89), 'EVA PLANLAMA', 6.0, yaw=0,
         color=(.64, .83, .85))
    add_marker('prologue_command_operator', (110, -600, 0))

    # Sample room tells the preparation story without fabricating assay results,
    # a sample identity or robotic instrument execution.
    solid('lab_bench_top', (-40, 702, 85), (235, 66, 9), 'door')
    for x in (-133, 53):
        solid('lab_bench_leg_'+str(x), (x, 702, 40), (12, 53, 80), 'frame')
    solid('lab_sample_tray', (-62, 702, 91), (100, 44, 3), 'frame')
    for index, x in enumerate((-94, -62, -30)):
        solid('lab_empty_container_'+str(index), (x, 702, 103), (14, 14, 22), 'door', cylinder)
        solid('lab_container_cap_'+str(index), (x, 702, 115), (16, 16, 3), 'frame', cylinder)
    solid('lab_instrument_case', (40, 701, 99), (38, 41, 20), 'frame')
    text('lab_wall_title', (-231, 744, 206), 'BİLİM HAZIRLIK', 12, yaw=0,
         color=(.56, .82, .85))
    text('lab_wall_note', (-231, 742, 184),
         'Bağlam → Kayıt → Kap → Analiz\nYeni ölçüm henüz yok\nKöken ve analiz yeri ayrı tutulur',
         7, yaw=0, color=(.82, .87, .89))
    add_marker('prologue_lab_operator', (60, 600, 0))
    # Dedicated Tripo laboratory already contains its benches and equipment.
    # Remove the former primitive furniture; retain the truthful lab sign.
    obsolete=('SCENARIO_Prologue_lab_bench_','SCENARIO_Prologue_lab_sample_tray','SCENARIO_Prologue_lab_empty_container_',
              'SCENARIO_Prologue_lab_container_cap_','SCENARIO_Prologue_lab_instrument_case')
    for actor in list(actors.get_all_level_actors()):
        if actor.get_actor_label().startswith(obsolete):actors.destroy_actor(actor)

    # Separate Tripo chamber beyond the shared corridor, two independent doors.
    if tripo.get('airlock'):
        anchors=json.loads((ROOT/'data/engines/prologue-tripo-v1/anchors.json').read_text())['airlock']
        if '+Y' not in anchors['open_cardinal_axes'] or '-Y' not in anchors['open_cardinal_axes']:
            raise RuntimeError('Airlock derivative must have two open end portals')
        box=tripo['airlock'].get_bounding_box();size=box.max-box.min
        floor_anchor=anchors['floor']['point'][2]*100*(280/size.z)
        static_visual('airlock_visual',tripo['airlock'],(750,0,-floor_anchor),yaw=90,
                      scale=(240/size.x,300/size.y,280/size.z))
        floor=solid('airlock_floor_proxy',(750,0,-6),(300,210,12),'floor');floor.set_actor_hidden_in_game(True)
        for side in (-101,101):hidden_wall('airlock_side_proxy_'+str(side),(750,side,119),(300,12,238))
        hidden_wall('airlock_ceiling_proxy',(750,0,222),(300,210,12))
        inner=solid('airlock_inner_door',(600,0,112),(10,94,224),'door',tag='prologue_room_door_airlock',movable=True)
        inner.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        for actor in actors.get_all_level_actors():
            if 'prologue_outer_door' in [str(t) for t in actor.tags]:
                actor.set_actor_location(point((900,0,112)),False,False)
                actor.set_actor_scale3d(unreal.Vector(.1,.94,2.24));actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
                actor.set_editor_property('tags',list(actor.tags)+[unreal.Name('prologue_room_door_exit')])
            if 'prologue_stand' in [str(t) for t in actor.tags]:actor.set_actor_location(point((755,50,0)),False,False)
        lamp('airlock_lamp',(750,0,207),22000,(1,.86,.65),370)
        text('airlock_label',(615,88,218),'04 / AIRLOCK',9,yaw=180,color=(.96,.74,.37))
        text('airlock_panel',(742,-91,154),'EVA\nKAPI / HAZIR',5,yaw=90,color=(.57,.85,.87))
        # Move original staged camera actors instead of creating duplicate tags.
        for tag,local,look in [
            ('prologue_cam_airlock_start',(625,-55,170),(885,0,125)),('prologue_cam_airlock_end',(650,-50,165),(885,0,125)),
            ('prologue_cam_ready_start',(930,-60,150),(1350,20,120)),('prologue_cam_ready_end',(1000,-40,155),(1350,20,120))]:
            actor=next(a for a in actors.get_all_level_actors() if tag in [str(t) for t in a.tags])
            actor.set_actor_location(point(local),False,False);actor.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(point(local),point(look)),False)
        REPORT['airlock']={'extent_end_x_cm':900,'source':'Tripo prologue_airlock','floor_anchor_cm':floor_anchor,
            'dimensions_cm':[300,240,280],'minimum_portal_width_cm':94,'pressure_simulation':False}

    # Skippable per-phase camera anchors. Traverse/debrief use the command wall;
    # the science introduction can look at the actual SCENARIO station location.
    for name, start, end, target in (
        ('mission_traverse', (192, -685, 166), (160, -665, 160), (-226, -600, 151)),
        ('mission_return', (540, -80, 168), (515, -65, 162), (295, 0, 133)),
        ('mission_debrief', (185, -640, 158), (145, -620, 154), (-232, -600, 157)),
    ):
        add_marker('prologue_cam_'+name+'_start', start, target)
        add_marker('prologue_cam_'+name+'_end', end, target)
    station_x, station_y = runtime['intro']['station_xy_m']
    ground = unreal.RedlineCoords.trace_terrain_height(
        world, unreal.Vector(station_x, station_y, runtime['spawn_map_xyz_m'][2]), 100)
    if not isinstance(ground, unreal.Vector):
        raise RuntimeError('No terrain under the SCENARIO science-story station')
    station_local = ((station_x*100-origin.x), (-station_y*100-origin.y), (ground.z*100-origin.z))
    add_marker('prologue_cam_mission_science_start',
               (station_local[0]+320, station_local[1]-290, station_local[2]+185),
               (station_local[0], station_local[1], station_local[2]+95))
    add_marker('prologue_cam_mission_science_end',
               (station_local[0]+265, station_local[1]-240, station_local[2]+162),
               (station_local[0], station_local[1], station_local[2]+95))
    add_marker('prologue_station_story_actor', station_local)
    report['station_story_location_map_m'] = [station_x, station_y, ground.z]
    report['live_bindings'] = {'field_texture_tag': 'prologue_command_screen',
                               'mission_text_tag': 'prologue_mission_board',
                               'freshness_scalar': 'DataFresh', 'texture_parameter': 'DisplayMap'}
    return report
