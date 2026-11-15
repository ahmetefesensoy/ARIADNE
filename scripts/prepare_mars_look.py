"""Mars look pass for the playable EVA map (user request 2026-11-15; Codex closed, this session owns it).

SCENARIO presentation only: terrain heights, HiRISE colours, ROS state and robot physics are unchanged.
- Sand (M_ScenarioSand_ops/_context): the HiRISE colour atlas stays the base. Detail is three octaves of
  smooth value noise (grains ~4 cm, pebbles ~25 cm, patches ~6 m) faded by distance, a 40 m macro
  variation that breaks the far blur, darker bedrock tone on steep faces, and a normal built from the
  noise gradient plus the existing ripples. The wheel depression (MPC_WheelContacts) is kept.
- Boot prints: /Game/MarsLook/M_Footprint deferred decal (procedural sole + heel + tread lines).
- Metal: rover sunlit materials get lower roughness / metallic foil so edges catch the sun.
- Air: the EVA map's height fog starts closer and thicker near the ground, with light volumetric fog.

Run in the Unreal editor of the build snapshot:
  UnrealEditor-Cmd.exe <Redline.uproject> -ExecutePythonScript=<this file> -unattended -nosplash
"""
import json
import unreal

lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {"status": "SCENARIO presentation", "materials": {}, "map": "/Game/EVAFixtures/BXW_EVA"}


def custom(mat, code, kind, sources):
    node = lib.create_material_expression(mat, unreal.MaterialExpressionCustom)
    node.set_editor_property("code", code)
    node.set_editor_property("output_type", kind)
    inputs = []
    for name in sources:
        value = unreal.CustomInput()
        value.set_editor_property("input_name", name)
        inputs.append(value)
    node.set_editor_property("inputs", inputs)
    for name, (source, output) in sources.items():
        if not lib.connect_material_expressions(source, output, node, name):
            raise RuntimeError(f"custom input {name} not connected")
    return node


def constant(mat, number):
    node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
    node.r = number
    return node


NOISE = """
#ifndef REDLINE_VN
#define REDLINE_VN 1
#define H(p) frac(sin(dot(p,float2(127.1,311.7)))*43758.5453)
#define VN(p) lerp(lerp(H(floor(p)),H(floor(p)+float2(1,0)),smoothstep(0,1,frac(p).x)),lerp(H(floor(p)+float2(0,1)),H(floor(p)+float2(1,1)),smoothstep(0,1,frac(p).x)),smoothstep(0,1,frac(p).y))
#endif
"""

SAND_COLOR = NOISE + """
float2 q=P.xy/100.0; float d=length(P-Cam);
float n1=VN(q*25.0), n2=VN(q*4.0+17.3), n3=VN(q*0.16+3.1), n4=VN(q*0.025+9.7);
float f1=saturate(1-d/1500.0), f2=saturate(1-d/6000.0);
float3 c=C*lerp(1,0.93+0.12*n1,f1)*lerp(1,0.95+0.09*n2,f2)*(0.94+0.12*n3)*(0.92+0.15*n4);
c*=float3(1+0.05*(n3-0.5),1,1-0.05*(n3-0.5));
float rock=saturate((0.93-N.z)*6.0);
c=lerp(c,c*float3(0.74,0.70,0.68),rock*0.55);
return c;
"""

SAND_NORMAL = NOISE + """
float2 q=P.xy/100.0; float d=length(P-Cam); float e=0.35;
float2 a=q*25.0, b=q*4.0+17.3;
float2 g1=float2(VN(a+float2(e,0))-VN(a-float2(e,0)),VN(a+float2(0,e))-VN(a-float2(0,e)));
float2 g2=float2(VN(b+float2(e,0))-VN(b-float2(e,0)),VN(b+float2(0,e))-VN(b-float2(0,e)));
float phase=q.x*41.0+sin(q.y*9.0)*2.1;
float2 ripple=float2(.04*cos(phase),.012*cos(phase)*cos(q.y*9.0));
float f1=saturate(1-d/1500.0), f2=saturate(1-d/6000.0), fr=saturate(1-d/2200.0);
float2 tilt=g1*0.10*f1+g2*0.16*f2+ripple*fr;
return normalize(N-float3(tilt,0));
"""

SAND_ROUGH = NOISE + """
float2 q=P.xy/100.0; return 0.88+0.09*VN(q*4.0+5.1);
"""


def rebuild_sand(kind):
    path = "/Game/VisualShowcase/Materials/M_ScenarioSand_" + kind
    mat = unreal.load_asset(path)
    texture = unreal.load_asset("/Game/DerivedPreview/Textures/atlas_" + kind)
    collection = unreal.load_asset("/Game/VisualShowcase/MPC_WheelContacts")
    if not (mat and texture and collection):
        raise RuntimeError(f"missing sand inputs for {kind}")
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property("tangent_space_normal", False)
    sample = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample)
    sample.texture = texture
    position = lib.create_material_expression(mat, unreal.MaterialExpressionWorldPosition)
    camera = lib.create_material_expression(mat, unreal.MaterialExpressionCameraPositionWS)
    normal = lib.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS)
    color = custom(mat, SAND_COLOR, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                   {"P": (position, ""), "C": (sample, "RGB"), "Cam": (camera, ""), "N": (normal, "")})
    lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    bump = custom(mat, SAND_NORMAL, unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                  {"P": (position, ""), "N": (normal, ""), "Cam": (camera, "")})
    lib.connect_material_property(bump, "", unreal.MaterialProperty.MP_NORMAL)
    rough = custom(mat, SAND_ROUGH, unreal.CustomMaterialOutputType.CMOT_FLOAT1, {"P": (position, "")})
    lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.connect_material_property(constant(mat, .18), "", unreal.MaterialProperty.MP_SPECULAR)
    sources = {"P": (position, "")}
    for i in range(6):  # rover wheel depression, unchanged from the T4 showcase
        param = lib.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter)
        param.set_editor_property("collection", collection)
        param.set_editor_property("parameter_name", "Wheel" + str(i))
        sources["W" + str(i)] = (param, "")
    depression = custom(mat, """
float d=0; float3 ws[6]={W0.xyz,W1.xyz,W2.xyz,W3.xyz,W4.xyz,W5.xyz};
[unroll] for(int i=0;i<6;i++){float r=length(P.xy-ws[i].xy);d=max(d,saturate(1-r/31));}
return float3(0,0,-2*d*d);
""", unreal.CustomMaterialOutputType.CMOT_FLOAT3, sources)
    lib.connect_material_property(depression, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    REPORT["materials"][path] = "rebuilt"


def footprint_material():
    path = "/Game/MarsLook/M_Footprint"
    mat = unreal.load_asset(path)
    if mat:
        lib.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("M_Footprint", "/Game/MarsLook", unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    uv = lib.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate)
    shape = custom(mat, """
float2 p=UV.xy;
float sole=saturate((1-length((p-float2(0.5,0.34))/float2(0.46,0.32)))*5);
float heel=saturate((1-length((p-float2(0.5,0.80))/float2(0.40,0.17)))*5);
float tread=step(0.45,frac(p.y*11.0));
return max(sole,heel)*lerp(0.42,0.78,tread);
""", unreal.CustomMaterialOutputType.CMOT_FLOAT1, {"UV": (uv, "")})
    color = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
    color.constant = unreal.LinearColor(.10, .045, .02, 1)
    lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(shape, "", unreal.MaterialProperty.MP_OPACITY)
    lib.connect_material_property(constant(mat, .98), "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    REPORT["materials"][path] = "created"


def metal_shine():
    # Lower roughness lets the low sun glint on edges (Fresnel); MLI foil is metal.
    for name, roughness, metallic in (("MAT_NASA_solid", .22, .6), ("MAT_NASA_gold", .14, 1.0),
                                      ("MAT_NASA_Curiosity_Atlas", .30, None)):
        path = "/Game/VisualShowcase/Materials/" + name + "_Sunlit"
        mat = unreal.load_asset(path)
        if not mat:
            REPORT["materials"][path] = "missing"
            continue
        rough = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_ROUGHNESS)
        if rough and isinstance(rough, unreal.MaterialExpressionConstant):
            rough.set_editor_property("r", roughness)
        if metallic is not None:
            metal = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_METALLIC)
            if not isinstance(metal, unreal.MaterialExpressionConstant):
                metal = constant(mat, metallic)
                lib.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
            metal.set_editor_property("r", metallic)
        spec = lib.get_material_property_input_node(mat, unreal.MaterialProperty.MP_SPECULAR)
        if isinstance(spec, unreal.MaterialExpressionConstant):
            spec.r = .65
        lib.recompile_material(mat)
        unreal.EditorAssetLibrary.save_loaded_asset(mat)
        REPORT["materials"][path] = f"roughness {roughness}, metallic {metallic}"


def air():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.load_level(REPORT["map"])
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    fogs = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.ExponentialHeightFog)]
    if not fogs:
        raise RuntimeError("EVA map has no height fog to tune")
    fog = fogs[0].get_component_by_class(unreal.ExponentialHeightFogComponent)
    for name, value in (("fog_density", .006), ("fog_height_falloff", .35), ("start_distance", 1500.),
                        ("fog_max_opacity", .62), ("enable_volumetric_fog", True),
                        ("volumetric_fog_scattering_distribution", .55),
                        ("volumetric_fog_albedo", unreal.Color(r=230, g=170, b=120, a=255)),
                        ("volumetric_fog_extinction_scale", .35), ("volumetric_fog_distance", 6000.)):
        try:
            fog.set_editor_property(name, value)
        except Exception as error:  # property names drift between engine versions
            REPORT.setdefault("fog_skipped", []).append(f"{name}: {error}")
    REPORT["fog"] = "near-ground haze from 15 m, light volumetric fog to 60 m"
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, REPORT["map"]):
        raise RuntimeError("EVA map save failed")


for kind in ("ops", "context"):
    rebuild_sand(kind)
footprint_material()
metal_shine()
air()
unreal.log("REDLINE_MARS_LOOK " + json.dumps(REPORT))
