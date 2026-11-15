"""SCENARIO lighting/look pass over the existing sand preview, not Mars weather data.

Engine atmosphere, dust haze and material roughness are visual art parameters.
Terrain coordinates, archive textures, ROS control and Gazebo physics stay intact.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import traceback
import unreal

repo=Path(os.environ['REDLINE_REPO'])
report={'observed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'SCENARIO','passed':False,
    'map':'/Game/VisualShowcase/BXW_Atmosphere_Autonomy',
    'scope':'engine atmosphere/lighting and original rover material derivatives; not measured Mars atmosphere'}
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/VisualShowcase/BXW_Sand_Autonomy')
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world=editor.get_editor_world()
    location=unreal.Vector(14500,28900,-359897)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label()=='Preview_Existing_Engine_Sky':actors.destroy_actor(actor)
    atmosphere=actors.spawn_actor_from_class(unreal.SkyAtmosphere,location)
    atmosphere.set_actor_label('SCENARIO_Mars_Dust_Atmosphere')
    component=atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent)
    component.set_editor_property('transform_mode',unreal.SkyAtmosphereTransformMode.PLANET_TOP_AT_COMPONENT_TRANSFORM)
    component.set_editor_property('bottom_radius',3396.19)
    component.set_editor_property('atmosphere_height',40.)
    component.set_editor_property('rayleigh_scattering_scale',.25)
    component.set_editor_property('rayleigh_exponential_distribution',8.)
    component.set_editor_property('mie_scattering',unreal.LinearColor(.008,.005,.0025,1))
    component.set_editor_property('mie_scattering_scale',1.0)
    component.set_editor_property('mie_absorption',unreal.LinearColor(.002,.0025,.003,1))
    component.set_editor_property('mie_absorption_scale',.5)
    component.set_editor_property('mie_anisotropy',.72)
    component.set_editor_property('mie_exponential_distribution',5.)
    component.set_editor_property('other_absorption_scale',0.)
    component.set_editor_property('trace_sample_count_scale',2.)
    fog=actors.spawn_actor_from_class(unreal.ExponentialHeightFog,location)
    fog.set_actor_label('SCENARIO_Distant_Dust_Haze')
    fog_component=fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_component.set_editor_property('fog_density',.001)
    fog_component.set_editor_property('fog_height_falloff',.2)
    fog_component.set_editor_property('start_distance',10000.)
    fog_component.set_editor_property('fog_max_opacity',.55)
    # Luminance is in the same physical exposure range as the sun, not an LDR
    # RGB swatch. This keeps distant dust gold instead of a dark veil.
    fog_component.set_editor_property('fog_inscattering_luminance',unreal.LinearColor(250.,110.,35.,1))
    # Reserve the dust veil for distant relief; keep navigation/rover readable.
    fog_component.set_editor_property('enable_volumetric_fog',False)
    # Physical lux needs a physical exposure. The source preview used a 5-lux
    # sun; relying on its default camera exposure clips the 12,000-lux scene.
    # ISO 100, f/4, 1/125 s => EV100 10.97 (see engine eye-adaptation code).
    exposure = unreal.PostProcessSettings()
    for name, value in {
        'auto_exposure_method': unreal.AutoExposureMethod.AEM_MANUAL,
        'auto_exposure_apply_physical_camera_exposure': True,
        'auto_exposure_bias': .6,
        'camera_iso': 100.,
        'camera_shutter_speed': 125.,
        'depth_of_field_fstop': 4.,
        'bloom_intensity': .18,
        'lens_flare_intensity': .08,
    }.items():
        exposure.set_editor_property('override_' + name, True)
        exposure.set_editor_property(name, value)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, location)
    post.set_actor_label('SCENARIO_Fixed_Daylight_Exposure')
    post.set_editor_property('unbound', True)
    post.set_editor_property('priority', 100.)
    post.set_editor_property('settings', exposure)
    for actor in actors.get_all_level_actors():
        if isinstance(actor, unreal.CameraActor):
            actor.camera_component.set_editor_property('post_process_settings', exposure)
            actor.camera_component.set_editor_property('post_process_blend_weight', 1.)
            actor.set_actor_relative_transform(unreal.Transform(
                location=unreal.Vector(-900,-650,360),
                rotation=unreal.Rotator(pitch=-5,yaw=35,roll=0)),False,False)
            actor.camera_component.set_field_of_view(75)
    for actor in actors.get_all_level_actors():
        if isinstance(actor,unreal.DirectionalLight):
            # ROS yaw -90 degrees becomes UE yaw +90: aim the visible sun to
            # the left of the follow camera, accounting for that handedness.
            actor.set_actor_rotation(unreal.Rotator(pitch=-12,yaw=-70,roll=0),False)
            light=actor.light_component
            light.set_editor_property('atmosphere_sun_light',True)
            light.set_editor_property('forward_shading_priority',1)
            light.set_editor_property('light_source_angle',.7)
            light.set_editor_property('contact_shadow_length',.12)
            light.set_intensity(12000.)
            light.set_light_color(unreal.LinearColor(1.,.83,.63,1.))
        if isinstance(actor,unreal.SkyLight):
            # Existing engine HDR supplies readable metal reflections in this
            # non-Lumen preview; it is an art reference, not Mars observations.
            cube = unreal.load_asset('/Engine/MapTemplates/Sky/SunsetAmbientCubemap')
            if not cube: raise RuntimeError('Missing engine sunset reflection cube')
            actor.light_component.set_editor_property('real_time_capture',False)
            actor.light_component.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
            actor.light_component.set_cubemap(cube)
            actor.light_component.set_intensity(150.)
            actor.light_component.set_editor_property('lower_hemisphere_is_black',False)
    # A restrained, unshadowed fill approximates diffuse dust/ground bounce in
    # this non-Lumen preview. It is art direction, not a second physical sun.
    fill = actors.spawn_actor_from_class(unreal.DirectionalLight,location,
        unreal.Rotator(pitch=-50,yaw=125,roll=0))
    fill.set_actor_label('SCENARIO_Diffuse_Dust_Bounce_Fill')
    fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill.light_component.set_editor_property('atmosphere_sun_light',False)
    fill.light_component.set_editor_property('forward_shading_priority',0)
    fill.light_component.set_editor_property('cast_shadows',False)
    fill.light_component.set_intensity(4000.)
    fill.light_component.set_light_color(unreal.LinearColor(.95,.77,.55,1.))
    lib=unreal.MaterialEditingLibrary
    derivatives={}
    for name,roughness in [('MAT_NASA_Curiosity_Atlas',.38),('MAT_NASA_solid',.32),('MAT_NASA_gold',.23),('MAT_NASA_parts_AO',.42)]:
        target='/Game/VisualShowcase/Materials/'+name+'_Sunlit'
        material=unreal.load_asset(target)
        if not material:material=unreal.EditorAssetLibrary.duplicate_asset('/Game/DerivedPreview/Materials/'+name,target)
        rough=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_ROUGHNESS)
        rough.set_editor_property('r',roughness)
        spec=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_SPECULAR)
        if not spec:spec=lib.create_material_expression(material,unreal.MaterialExpressionConstant)
        spec.r=.5
        lib.connect_material_property(spec,'',unreal.MaterialProperty.MP_SPECULAR)
        lib.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        derivatives[name]=material
    for actor in actors.get_all_level_actors():
        if not actor.get_actor_label().startswith('LIVE_'):continue
        comp=actor.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(comp.get_num_materials()):
            current=comp.get_material(i)
            name=current.get_name() if current else ''
            if name in derivatives:comp.set_material(i,derivatives[name])
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,report['map']):raise RuntimeError('Atmosphere map save failed')
    report.update(passed=True,sun_intensity_lux=12000.,sun_pitch_deg=-12.,sun_yaw_deg=-70.,fog_density=.001,
        fog_start_distance_m=100.,volumetric_fog=False,skylight_intensity=150.,
        reflection_cube='/Engine/MapTemplates/Sky/SunsetAmbientCubemap',
        diffuse_scenario_fill_lux=4000.,
        exposure={'method':'manual','iso':100,'fstop':4,'shutter_speed':125,'ev100':10.965784,'bias':.6},
        roughness={'atlas':.38,'paint':.32,'gold':.23},physical_atmosphere_validation=False,
        render_verified=False)
except Exception as error:
    report['error']=repr(error);report['traceback']=traceback.format_exc()
finally:
    (repo/'test-results/t4-atmosphere-import.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('REDLINE_ATMOSPHERE '+json.dumps(report))
if not report['passed']:raise RuntimeError(report.get('error','Atmosphere pass failed'))
