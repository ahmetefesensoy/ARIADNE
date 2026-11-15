"""'How it works' explainer videos for the science tasks, rendered in Blender (user request 2026-11-15).

Usage (Windows):
  blender --background --python assets/production/explainer_videos.py -- drill [--preview]

Presentation only (proje.md §9.2 B5 for the drill): the shots show how the instrument works with the
project's own 3D packages; numbers on screen are the SCENARIO drill model's story (stall -> retract
-> lower feed -> percussive), not a measurement. Output: assets/explainers/<task>/ (MP4, poster PNG,
captions_tr.srt, captions_en.srt, explainer.json). No Unreal content is touched.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "incoming"
FPS = 30
FONT_BOLD = "C:/Windows/Fonts/seguisb.ttf"
FONT = "C:/Windows/Fonts/segoeui.ttf"
MARS_SKY = (0.62, 0.42, 0.27)
REGOLITH = (0.36, 0.17, 0.08)


# ----------------------------------------------------------------------------------------- scene
def reset_scene(frames: int, preview: bool):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.resolution_x, scene.render.resolution_y = (960, 540) if preview else (1920, 1080)
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    eevee = scene.eevee
    for name, value in (("taa_render_samples", 16 if preview else 64), ("use_shadows", True),
                        ("use_raytracing", not preview)):
        if hasattr(eevee, name):
            setattr(eevee, name, value)
    world = bpy.data.worlds.new("MarsSky")
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    bg = nodes["Background"]
    bg.inputs["Strength"].default_value = 0.6
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.80, 0.60, 0.42, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.45, (0.42, 0.26, 0.16, 1)
    links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg.inputs["Color"])
    return scene


def material(name, color, roughness=0.8, metallic=0.0, emission=None, strength=0.0, noise=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 40.0
        tex.inputs["Detail"].default_value = 8.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = tuple(c * (1 - noise) for c in color) + (1,)
        ramp.color_ramp.elements[1].color = tuple(min(1, c * (1 + noise)) for c in color) + (1,)
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.35
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def ground():
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "regolith"
    plane.data.materials.append(material("M_regolith", REGOLITH, 0.95, noise=0.35))
    return plane


def sun(angle_deg=28.0, azimuth_deg=-40.0, energy=4.5):
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
    light = bpy.context.object
    light.data.energy = energy
    light.data.color = (1.0, 0.93, 0.82)
    light.data.angle = math.radians(1.2)
    light.rotation_euler = (math.radians(90 - angle_deg), 0, math.radians(azimuth_deg))
    return light


def matte(obj, roughness=0.92):
    for slot in obj.material_slots:
        bsdf = slot.material.node_tree.nodes.get("Principled BSDF") if slot.material else None
        if bsdf:
            for name in ("Roughness", "Metallic"):
                for link in list(bsdf.inputs[name].links):
                    slot.material.node_tree.links.remove(link)
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = 0.0
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.2


def append_lod0(package: str) -> list:
    """Append the package's LOD0 meshes (with their materials and textures) from master.blend."""
    path = ASSETS / package / "master.blend"
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith("_LOD0") and not n.startswith("UCX_")]
    objects = []
    for obj in dst.objects:
        if obj is not None and obj.type == "MESH":
            bpy.context.scene.collection.objects.link(obj)
            obj.hide_render = obj.hide_viewport = False
            objects.append(obj)
    for image in bpy.data.images:  # textures are relative to the package's master.blend
        if image.filepath.startswith("//"):
            image.filepath = str((path.parent / image.filepath[2:]).resolve())
    return objects


def camera(location, target, lens=40):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.dof.use_dof = False
    aim = bpy.data.objects.new("cam_target", None)
    bpy.context.scene.collection.objects.link(aim)
    aim.location = target
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = aim, "TRACK_NEGATIVE_Z", "UP_Y"
    bpy.context.scene.camera = cam
    return cam, aim


def key(obj, path, frame, value, index=-1):
    setattr(obj, path, value) if index < 0 else getattr(obj, path).__setitem__(index, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def hud_text(cam, name, body, offset, size, color=(1, 1, 1), bold=False):
    """Text pinned 1 m in front of the camera. `offset` is in frame units (-1..1 across the 16:9 frame)
    and `size` a fraction of the frame height, so the overlay stays inside the picture."""
    depth = 0.15  # closer than any scenery, so rocks never hide the overlay
    half_w = cam.data.sensor_width / 2 / cam.data.lens * depth
    half_h = half_w * 9 / 16
    offset, size = (offset[0] * half_w, offset[1] * half_h), size * 2 * half_h
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = "LEFT"
    font_path = FONT_BOLD if bold else FONT
    if Path(font_path).exists():
        curve.font = bpy.data.fonts.load(font_path, check_existing=True)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = cam
    obj.location = Vector((offset[0], offset[1], -depth))
    obj.data.materials.append(material(f"M_{name}", color, emission=color, strength=2.5))
    return obj


# ------------------------------------------------------------------------------------------ drill
DRILL_BEATS = [  # (start s, end s, tr, en)
    (0.0, 3.5, "B5 · Sondaj ve arıza yönetimi", "B5 · Drilling with fault handling"),
    (3.5, 8.0, "Matkap kayaya iner, uç dönmeye başlar.", "The drill comes down to the rock and the bit spins up."),
    (8.0, 13.5, "Besleme kuvvetiyle uç kayaya girer; toz dışarı atılır.",
     "The feed force pushes the bit into the rock; the cuttings are thrown out."),
    (13.5, 16.5, "Sıkışma! Tork sınırı aşıldı: uç geri çekilir, besleme azalır.",
     "Stall! Torque over the limit: the bit retracts and the feed is lowered."),
    (16.5, 21.0, "Darbeli moda geçilir; 5 cm'e ulaşılır.", "It switches to percussive mode and reaches 5 cm."),
    (21.0, 25.0, "Toz numune tüpe alınır ve laboratuvara gider. (Simülasyon)",
     "The powder sample goes into a tube and on to the lab. (Simulation)"),
]


def drill_profile(t: float) -> tuple[float, float, str]:
    """(depth_mm, torque_Nm, mode) of the SCENARIO story at time t seconds."""
    if t < 8.0:
        return 0.0, 0.4 if t > 5.0 else 0.0, "HAZIR"
    if t < 13.5:
        f = (t - 8.0) / 5.5
        return 28.0 * f, 2.0 + 4.5 * f ** 2, "DÖNER"
    if t < 14.2:
        return 28.0, 9.6, "STALL"
    if t < 16.5:
        f = (t - 14.2) / 2.3
        return 28.0 - 10.0 * min(f * 2, 1.0), 1.0, "GERİ ÇEKİL"
    if t < 21.0:
        f = (t - 16.5) / 4.5
        return 18.0 + 32.0 * f, 3.2 + 0.6 * math.sin(t * 40), "DARBELİ"
    return 50.0 * max(0.0, 1 - (t - 21.0) / 1.5), 0.0, "TAMAM"


def build_drill(scene, preview: bool):
    frames = scene.frame_end
    ground()
    sun()
    rock_parts = append_lod0("rock_07")
    rock = rock_parts[0]
    rock.scale = (2.6, 2.6, 2.0)
    rock.location = (0.0, 0.0, 0.10)
    matte(rock)
    bpy.context.view_layer.update()
    hit, where, *_ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((0, 0, 5)), Vector((0, 0, -1)))
    surface_z = where.z if hit else 0.3  # rock top on the drill axis
    drill = append_lod0("tool_drill")
    rig = bpy.data.objects.new("drill_rig", None)
    scene.collection.objects.link(rig)
    for obj in drill:
        obj.parent = rig
    bit = next(o for o in drill if o.name.startswith("SM_tool_drill_bit_LOD0"))
    rig.location = (-0.02, 0.023, surface_z + 0.30)

    # hole: an animated cylinder subtracted from the rock
    bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=0.2, location=(0, 0, surface_z + 0.1))
    cutter = bpy.context.object
    cutter.name, cutter.hide_render, cutter.display_type = "hole_cutter", True, "WIRE"
    boolean = rock.modifiers.new("hole", "BOOLEAN")
    boolean.operation, boolean.object = "DIFFERENCE", cutter

    # powder: particles from the hole rim
    bpy.ops.mesh.primitive_circle_add(radius=0.03, fill_type="NGON", location=(0, 0, surface_z + 0.005))
    emitter = bpy.context.object
    emitter.name = "powder_emitter"
    ps = emitter.modifiers.new("powder", "PARTICLE_SYSTEM").particle_system.settings
    ps.count, ps.frame_start, ps.frame_end, ps.lifetime = 900, int(8 * FPS), int(21 * FPS), 22
    ps.normal_factor, ps.factor_random = 0.28, 0.25
    ps.effector_weights.gravity = 0.38  # Mars gravity relative to Earth's
    ps.render_type, ps.particle_size, ps.size_random = "OBJECT", 0.004, 0.7
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=1, location=(0, 0, -5))
    grain = bpy.context.object
    grain.data.materials.append(material("M_powder", (0.55, 0.30, 0.15), 1.0))
    ps.instance_object = grain
    emitter.show_instancer_for_render = False

    spin_deg = 0.0
    for frame in range(1, frames + 1):
        t = (frame - 1) / FPS
        depth_mm, torque, mode = drill_profile(t)
        approach = min(1.0, max(0.0, (t - 3.5) / 3.0))
        lift = 0.30 * (1 - (3 * approach ** 2 - 2 * approach ** 3))
        hammer = 0.004 * math.sin(t * 2 * math.pi * 12) if mode == "DARBELİ" else 0.0
        if t > 22.5:
            lift = 0.12 * min(1.0, (t - 22.5) / 1.5)
        rig.location.z = surface_z + lift - depth_mm / 1000.0 + hammer
        rig.keyframe_insert("location", index=2, frame=frame)
        rate = {"HAZIR": 0.0 if t < 5 else 8.0, "DÖNER": 24.0, "STALL": 2.0, "GERİ ÇEKİL": 6.0,
                "DARBELİ": 18.0, "TAMAM": 3.0}[mode]
        spin_deg += rate
        bit.rotation_euler[2] = math.radians(spin_deg)
        bit.keyframe_insert("rotation_euler", index=2, frame=frame)
        cutter.location.z = surface_z + 0.1 - min(depth_mm, 50.0) / 1000.0 if t < 21 else \
            surface_z + 0.1 - 0.050
        cutter.keyframe_insert("location", index=2, frame=frame)

    # camera: establishing orbit, then low close-up during the stall and percussive drilling
    cam, aim = camera((1.9, -1.8, surface_z + 0.9), (0, 0, surface_z + 0.25), lens=38)
    shots = [(1, (2.2, -2.0, surface_z + 1.0), (0, 0, surface_z + 0.3)),
             (int(7 * FPS), (1.3, -1.2, surface_z + 0.55), (0, 0, surface_z + 0.25)),
             (int(12.5 * FPS), (0.75, -0.65, surface_z + 0.22), (0, 0, surface_z + 0.10)),
             (int(20 * FPS), (0.8, 0.65, surface_z + 0.30), (0, 0, surface_z + 0.12)),
             (frames, (1.8, 1.3, surface_z + 0.8), (0, 0, surface_z + 0.25))]
    for frame, loc, target in shots:
        cam.location = loc
        cam.keyframe_insert("location", frame=frame)
        aim.location = target
        aim.keyframe_insert("location", frame=frame)

    # overlay: caption, gauge numbers, honesty tag
    caption = hud_text(cam, "caption", "", (-0.92, -0.78), 0.05, bold=True)
    gauge = hud_text(cam, "gauge", "", (0.42, 0.86), 0.04, color=(1.0, 0.85, 0.55))
    hud_text(cam, "tag", "SİMÜLASYON · sertlik ve tork SCENARIO · proje.md §9.2 B5", (-0.92, -0.92), 0.028,
             color=(0.85, 0.85, 0.85))

    def update(scene_, *_):
        t = (scene_.frame_current - 1) / FPS
        caption.data.body = next((tr for s, e, tr, _ in DRILL_BEATS if s <= t < e), DRILL_BEATS[-1][2])
        depth_mm, torque, mode = drill_profile(t)
        alarm = mode == "STALL"
        gauge.data.body = f"DERİNLİK {depth_mm:5.1f} mm\nTORK     {torque:4.1f} N·m{'  ⚠' if alarm else ''}\nMOD      {mode}"
        gauge.active_material.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = \
            (1.0, 0.15, 0.1, 1) if alarm else (1.0, 0.85, 0.55, 1)

    bpy.app.handlers.frame_change_pre.append(update)
    return DRILL_BEATS


# ------------------------------------------------------------------------------------------- APXS
APXS_BEATS = [
    (0.0, 3.0, "B1 · APXS ile temas bilimi", "B1 · Contact science with the APXS"),
    (3.0, 7.0, "Ölçüm kafası kayaya yaklaşır.", "The sensor head comes down to the rock."),
    (7.0, 11.0, "Küryum-244 kaynakları kayayı alfa parçacığı ve X ışınıyla uyarır.",
     "Curium-244 sources excite the rock with alpha particles and X-rays."),
    (11.0, 15.0, "Atomlar kendine özgü X ışınıyla cevap verir; dedektör bunları sayar.",
     "Each element answers with its own X-rays; the detector counts them."),
    (15.0, 19.0, "Temas iyileşince hata çubukları küçülür.", "Better contact shrinks the error bars."),
    (19.0, 24.0, "Gerçek APXS arşivi: 1 saat saymak hatayı yalnız ~%16 azaltır; iyi temas daha çok kazandırır.",
     "Real APXS archive: counting for an hour cuts the error by only ~16%; good contact gains more."),
]
APXS_OXIDES = (("SiO2", 46.0), ("FeO", 18.0), ("Al2O3", 12.0), ("CaO", 6.0), ("MgO", 5.0))  # BXW_RIDGE_A, SCENARIO


def apxs_state(t: float) -> tuple[float, float]:
    """(standoff cm, integration s) of the explainer story at time t."""
    if t < 7.0:
        return 6.0 - 4.0 * min(1.0, max(0.0, (t - 3.0) / 4.0)), 0.0
    if t < 15.0:
        return 2.0, 600.0 * min(1.0, (t - 7.0) / 4.0) if t < 11.0 else 600.0
    if t < 19.0:
        return 2.0 - 1.8 * min(1.0, (t - 15.0) / 2.0), 600.0
    return 0.2, 600.0 + 3000.0 * min(1.0, (t - 19.0) / 3.0)


def build_apxs(scene, preview: bool):
    model = json.loads((ROOT / "data/derived/instruments/apxs_precision_v1.json").read_text(encoding="utf-8"))

    def sigma(oxide, value, seconds, standoff):
        o = model["oxides"][oxide]
        return o["sigma_ref_wt"] * math.exp(o["exp_t"] * math.log(seconds / model["t_ref_s"])
                                            + o["exp_v"] * math.log(value / o["v_ref_wt"])
                                            + o["per_cm_standoff"] * max(standoff, 0.0))

    ground()
    sun(angle_deg=32.0, azimuth_deg=-60.0)
    rock = append_lod0("rock_09")[0]
    rock.scale = (2.4, 2.4, 2.0)
    matte(rock)
    bpy.context.view_layer.update()
    hit, where, *_ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((0, 0, 5)), Vector((0, 0, -1)))
    surface_z = where.z if hit else 0.25
    head = append_lod0("tool_apxs")
    rig = bpy.data.objects.new("apxs_rig", None)
    scene.collection.objects.link(rig)
    turn = bpy.data.objects.new("apxs_turn", None)  # +X sensor face -> -Z, face on the rig origin
    scene.collection.objects.link(turn)
    turn.parent = rig
    turn.rotation_euler = (0.0, math.pi / 2, 0.0)
    for obj in head:
        obj.parent = turn
        obj.location = (obj.location.x - 0.09, obj.location.y, obj.location.z - 0.052)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.2, location=(0, 0, 0.78))
    arm = bpy.context.object
    arm.data.materials.append(material("M_arm", (0.75, 0.75, 0.78), 0.35, metallic=1.0))
    arm.parent = rig

    def emitter(name, z, normal_speed, color, start, end, count):
        bpy.ops.mesh.primitive_circle_add(radius=0.03, fill_type="NGON", location=(0, 0, z))
        e = bpy.context.object
        e.name = name
        ps = e.modifiers.new(name, "PARTICLE_SYSTEM").particle_system.settings
        ps.count, ps.frame_start, ps.frame_end, ps.lifetime = count, int(start * FPS), int(end * FPS), 12
        ps.normal_factor, ps.factor_random, ps.effector_weights.gravity = normal_speed, 0.08, 0.0
        ps.render_type, ps.particle_size, ps.size_random = "OBJECT", 0.0035, 0.5
        bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=1, location=(0, 0, -5))
        spark = bpy.context.object
        spark.data.materials.append(material(f"M_{name}", color, emission=color, strength=4.0))
        ps.instance_object = spark
        e.show_instancer_for_render = False
        return e

    excite = emitter("excite", surface_z + 0.02, 0.0, (0.55, 0.75, 1.0), 7.0, 19.5, 700)
    excite.rotation_euler[0] = math.pi  # emit downward into the rock
    excite.modifiers["excite"].particle_system.settings.normal_factor = 0.25
    answers = [emitter(f"answer_{i}", surface_z + 0.001, 0.22, c, 11.0, 23.5, 380)
               for i, c in enumerate(((1.0, 0.85, 0.2), (1.0, 0.3, 0.15), (0.3, 1.0, 0.45)))]
    for i, e in enumerate(answers):
        e.location.x += (i - 1) * 0.012

    for frame in range(1, scene.frame_end + 1):
        t = (frame - 1) / FPS
        standoff_cm, _ = apxs_state(t)
        approach = min(1.0, t / 3.0)
        rig.location.z = surface_z + standoff_cm / 100.0 + 0.6 * (1 - approach) ** 2
        rig.keyframe_insert("location", index=2, frame=frame)

    cam, aim = camera((1.2, -1.1, surface_z + 0.6), (0, 0, surface_z + 0.05), lens=42)
    shots = [(1, (1.5, -1.3, surface_z + 0.8), (0, 0, surface_z + 0.25)),
             (int(6 * FPS), (0.65, -0.55, surface_z + 0.18), (0, 0, surface_z + 0.04)),
             (int(14 * FPS), (0.45, -0.38, surface_z + 0.08), (0, 0, surface_z + 0.02)),
             (scene.frame_end, (0.9, 0.7, surface_z + 0.35), (0, 0, surface_z + 0.05))]
    for frame, loc, target in shots:
        cam.location = loc
        cam.keyframe_insert("location", frame=frame)
        aim.location = target
        aim.keyframe_insert("location", frame=frame)

    caption = hud_text(cam, "caption", "", (-0.92, -0.78), 0.05, bold=True)
    table = hud_text(cam, "table", "", (0.38, 0.88), 0.036, color=(0.75, 0.95, 1.0))
    hud_text(cam, "tag", "Hata: MSL APXS arşivi (Berger vd. 2020) · bileşim SCENARIO · proje.md §9.2 B1", (-0.92, -0.92),
             0.028, color=(0.85, 0.85, 0.85))

    def update(scene_, *_):
        t = (scene_.frame_current - 1) / FPS
        caption.data.body = next((tr for s, e, tr, _ in APXS_BEATS if s <= t < e), APXS_BEATS[-1][2])
        standoff_cm, seconds = apxs_state(t)
        lines = [f"BOŞLUK   {standoff_cm:4.1f} cm", f"SAYIM    {seconds / 60:4.0f} dk"]
        if seconds >= 540.0:
            for oxide, value in APXS_OXIDES:
                lines.append(f"{oxide:<6} {value:5.1f} ± {sigma(oxide, value, seconds, standoff_cm):4.2f}")
        table.data.body = "\n".join(lines)

    bpy.app.handlers.frame_change_pre.append(update)
    return APXS_BEATS


# ------------------------------------------------------------------------------------------- LIBS
LIBS_BEATS = [
    (0.0, 3.0, "B2 · Uzaktan LIBS ve otonom hedef seçimi", "B2 · Remote LIBS with autonomous targeting"),
    (3.0, 8.0, "Rover çevredeki kayaları tarar; boyut ve parlaklığa göre aday seçer (AEGIS benzeri).",
     "The rover scans the rocks around it and picks candidates by size and brightness (AEGIS-like)."),
    (8.0, 10.0, "Hedef seçildi.", "Target chosen."),
    (10.0, 17.0, "Lazer kayadan mikroskobik bir noktayı buharlaştırır; plazma ışık saçar. 5 noktalık tarama.",
     "The laser vaporises a microscopic spot of rock; the plasma glows. A 5-point raster."),
    (17.0, 21.0, "Teleskop bu ışığı toplar; spektrumdaki çizgiler elementleri söyler.",
     "A telescope collects that light; the lines in the spectrum name the elements."),
    (21.0, 24.0, "İlk atışlar yüzeydeki tozu temizler. (Simülasyon)", "The first shots clear the surface dust. (Simulation)"),
]
# Emission lines: NIST atomic spectra database values, rounded (air wavelengths).
LIBS_LINES = (("Mg II", 279.6), ("Si I", 288.2), ("Ca II", 393.4), ("Al I", 396.2), ("Fe I", 404.6),
              ("Na I", 589.0), ("H I", 656.3))


def build_libs(scene, preview: bool):
    ground()
    sun(angle_deg=24.0, azimuth_deg=-30.0)
    rocks = []
    for package, xy, scale in (("namaqualand_boulder_04", (4.6, 0.3), 0.9), ("rock_07", (3.7, -1.9), 1.6),
                               ("moon_rock_03", (5.5, 2.4), 1.3)):
        parts = append_lod0(package)
        if not parts:
            continue
        rock = parts[0]
        rock.location = (xy[0], xy[1], 0.0)
        rock.scale = (scale, scale, scale)
        matte(rock)
        rocks.append(rock)
    bpy.context.view_layer.update()
    target = rocks[0]  # the bright boulder: what an AEGIS-like brightness rule would pick
    tz = max((target.matrix_world @ Vector(c)).z for c in target.bound_box) * 0.55
    toward = (Vector((target.location.x, target.location.y, tz)) - Vector((0, 0, 2.05))).normalized()
    hit, where, *_ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), Vector((0, 0, 2.05)), toward)
    aim_point = where if hit else Vector((target.location.x - 0.3, target.location.y, tz))
    # mast with the LIBS head
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=2.0, location=(0, 0, 1.0))
    mast = bpy.context.object
    mast.data.materials.append(material("M_mast", (0.8, 0.8, 0.82), 0.3, metallic=1.0))
    pan = bpy.data.objects.new("libs_pan", None)
    scene.collection.objects.link(pan)
    pan.location = (0, 0, 2.05)
    for obj in append_lod0("tool_libs"):
        obj.parent = pan
        obj.location = (obj.location.x, obj.location.y, obj.location.z - 0.05)
    # candidate rings (AEGIS-like picks) on the ground
    rings = []
    for rock in rocks:
        corners = [rock.matrix_world @ Vector(c) for c in rock.bound_box]
        footprint = max(max(abs(c.x - rock.location.x), abs(c.y - rock.location.y)) for c in corners)
        bpy.ops.mesh.primitive_torus_add(major_radius=footprint * 1.25, minor_radius=0.01,
                                         location=(rock.location.x, rock.location.y, 0.03))
        ring = bpy.context.object
        ring.data.materials.append(material(f"M_ring_{rock.name}", (0.04, 0.03, 0.02), emission=(1.0, 0.8, 0.2), strength=0.0))
        rings.append(ring)
    # beam and spark
    origin = Vector((0, 0, 2.05))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=1.0)
    beam = bpy.context.object
    beam_mat = material("M_beam", (1.0, 0.3, 0.8), emission=(1.0, 0.3, 0.8), strength=0.0)
    beam.data.materials.append(beam_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02)
    spark = bpy.context.object
    spark_mat = material("M_spark", (0.8, 0.9, 1.0), emission=(0.8, 0.9, 1.0), strength=0.0)
    spark.data.materials.append(spark_mat)

    def point(i):  # 5-point vertical raster on the target face, 2 cm apart
        return aim_point + Vector((0, 0, (i - 2) * 0.02))

    frames = scene.frame_end
    for frame in range(1, frames + 1):
        t = (frame - 1) / FPS
        # pan: sweep across the candidates, then lock on the target
        if t < 8.0:
            yaw = math.radians(-35 + 70 * (0.5 - 0.5 * math.cos(math.pi * t / 4.0)))
        else:
            d = aim_point - origin
            yaw = math.atan2(d.y, d.x)
        pan.rotation_euler[2] = yaw
        pan.keyframe_insert("rotation_euler", index=2, frame=frame)
        for k, ring in enumerate(rings):
            bsdf = ring.data.materials[0].node_tree.nodes["Principled BSDF"]
            lit = (3.0 < t < 8.0 and t > 3.0 + k * 1.2) or (t >= 8.0 and k == 0)
            color = (0.2, 0.9, 1.0, 1) if (t >= 8.0 and k == 0) else (1.0, 0.8, 0.2, 1)
            bsdf.inputs["Emission Strength"].default_value = 3.0 if lit else 0.0
            bsdf.inputs["Emission Color"].default_value = color
            bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)
            bsdf.inputs["Emission Color"].keyframe_insert("default_value", frame=frame)
        firing = 10.0 <= t < 17.0
        shot = int((t - 10.0) * 3) if firing else 0  # 3 pulses per second
        on = firing and ((t - 10.0) * 3) % 1.0 < 0.25
        p = point(min(4, shot // 4)) if firing else aim_point
        mid, length = (origin + p) / 2, (p - origin).length
        beam.location = mid
        beam.rotation_euler = (p - origin).to_track_quat("Z", "Y").to_euler()
        beam.scale = (1.0 if on else 0.0, 1.0 if on else 0.0, length)  # only while a pulse fires
        spark.location = p
        spark.scale = (1.6 if on else 0.0,) * 3
        for obj in (beam, spark):
            obj.keyframe_insert("location", frame=frame)
            obj.keyframe_insert("rotation_euler", frame=frame)
            obj.keyframe_insert("scale", frame=frame)
        for mat, strength in ((beam_mat, 6.0 if on else 0.0), (spark_mat, 25.0 if on else 0.0)):
            node = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            node.default_value = strength
            node.keyframe_insert("default_value", frame=frame)

    cam, aim = camera((-2.2, -3.4, 2.4), (2.5, 0.0, 0.6), lens=32)
    a = aim_point
    shots = [(1, (-2.2, -3.4, 2.4), (2.5, 0.0, 0.8)), (int(8 * FPS), (-1.0, -2.2, 2.2), (a.x - 0.5, a.y, a.z)),
             (int(11 * FPS), (a.x - 1.3, a.y - 1.2, a.z + 0.25), (a.x, a.y, a.z)),
             (int(17 * FPS), (a.x - 1.0, a.y - 0.8, a.z + 0.1), (a.x, a.y, a.z)),
             (frames, (1.0, -3.0, 2.2), (a.x - 1.0, a.y, a.z + 0.3))]
    for frame, loc, tgt in shots:
        cam.location = loc
        cam.keyframe_insert("location", frame=frame)
        aim.location = tgt
        aim.keyframe_insert("location", frame=frame)

    caption = hud_text(cam, "caption", "", (-0.92, -0.78), 0.05, bold=True)
    spectrum = hud_text(cam, "spectrum", "", (0.40, 0.88), 0.036, color=(0.85, 0.75, 1.0))
    hud_text(cam, "tag", "SİMÜLASYON · ChemCam RDR yok · kızılötesi lazer görünmez, burada çizildi · menzil ≤ 7 m [?] · "
             "proje.md §9.2 B2", (-0.92, -0.92), 0.026, color=(0.85, 0.85, 0.85))

    def update(scene_, *_):
        t = (scene_.frame_current - 1) / FPS
        caption.data.body = next((tr for s, e, tr, _ in LIBS_BEATS if s <= t < e), LIBS_BEATS[-1][2])
        shown = 0 if t < 12.0 else min(len(LIBS_LINES), int((t - 12.0) * 1.2) + 1)
        lines = ["SPEKTRUM ÇİZGİLERİ"] + [f"{name:<6} {nm:6.1f} nm" for name, nm in LIBS_LINES[:shown]] if shown else []
        spectrum.data.body = "\n".join(lines)

    bpy.app.handlers.frame_change_pre.append(update)
    return LIBS_BEATS


# ----------------------------------------------------------------------------------------- output
ASSETS_USED = {"drill": ["assets/incoming/tool_drill", "assets/incoming/rock_07"],
               "apxs": ["assets/incoming/tool_apxs", "assets/incoming/rock_09", "data/derived/instruments/apxs_precision_v1.json"],
               "libs": ["assets/incoming/tool_libs", "assets/incoming/rock_07", "assets/incoming/moon_rock_03",
                        "assets/incoming/namaqualand_boulder_04", "NIST atomic spectra line wavelengths"]}


def srt(beats, lang: int) -> str:
    def ts(s):
        return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(round(s % 1 * 1000)):03d}"
    return "".join(f"{i}\n{ts(b[0])} --> {ts(b[1])}\n{b[lang]}\n\n" for i, b in enumerate(beats, 1))


def render(task: str, beats, scene, preview: bool, still_s: float | None = None):
    out = ROOT / "assets" / "explainers" / task
    out.mkdir(parents=True, exist_ok=True)
    scene.frame_set(int((still_s if still_s is not None else 9.5) * FPS))
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out / ("still.png" if still_s is not None else "poster.png"))
    bpy.ops.render.render(write_still=True)
    if still_s is not None:
        print("WROTE", scene.render.filepath)
        return
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    name = f"{task}_preview.mp4" if preview else f"{task}.mp4"
    scene.render.filepath = str(out / name)
    bpy.ops.render.render(animation=True)
    (out / "captions_tr.srt").write_text(srt(beats, 2), encoding="utf-8")
    (out / "captions_en.srt").write_text(srt(beats, 3), encoding="utf-8")
    (out / "explainer.json").write_text(json.dumps({
        "task": task, "status": "SCENARIO presentation", "video": name, "poster": "poster.png",
        "fps": FPS, "frames": scene.frame_end, "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "captions": {"tr": "captions_tr.srt", "en": "captions_en.srt"},
        "beats": [{"start_s": b[0], "end_s": b[1], "tr": b[2], "en": b[3]} for b in beats],
        "assets": ASSETS_USED.get(task, []),
        "note": "Shows how the instrument works; numbers are the SCENARIO model's story, not a measurement."},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("WROTE", out / name)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    task = argv[0] if argv else "drill"
    preview = "--preview" in argv
    builders = {"drill": (build_drill, 25.0), "apxs": (build_apxs, 24.0), "libs": (build_libs, 24.0)}
    build, seconds = builders[task]
    scene = reset_scene(int(seconds * FPS), preview)
    beats = build(scene, preview)
    still = float(argv[argv.index("--still") + 1]) if "--still" in argv else None
    render(task, beats, scene, preview, still)


main()
