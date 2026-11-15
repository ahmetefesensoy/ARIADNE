"""Procedural REDLINE props (original geometry, SCENARIO dimensions, no generative AI).

Usage: blender --background --factory-startup --python procedural_assets.py -- [ids]
Writes incoming/<id>/source.glb and generator.json. Every model is authored with its
front toward -Y because build_package.py rotates non-tool assets +90° about Z, which
puts the front on +X (master convention). Moving parts are separate objects; a part's
custom property `suggested_source_pivot` (source coordinates) marks its rotation centre.
Engineering-prop fidelity: simple bevel-free primitives, flat PBR colours.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
TEXTURES = json.loads((ROOT / "production/procedural_textures.json").read_text(encoding="utf-8"))

PALETTE = {  # name: (base colour linear RGB, roughness, metallic, alpha)
    "white": ((0.80, 0.80, 0.78), 0.45, 0.0, 1.0),
    "graphite": ((0.045, 0.047, 0.05), 0.55, 0.0, 1.0),
    "alu": ((0.62, 0.63, 0.65), 0.32, 1.0, 1.0),
    "red": ((0.50, 0.035, 0.03), 0.42, 0.0, 1.0),
    "rubber": ((0.025, 0.025, 0.025), 0.88, 0.0, 1.0),
    "fabric": ((0.78, 0.76, 0.70), 0.92, 0.0, 1.0),
    "solar": ((0.02, 0.04, 0.10), 0.22, 0.3, 1.0),
    "screen": ((0.012, 0.014, 0.016), 0.12, 0.0, 1.0),
    "glass": ((0.55, 0.62, 0.66), 0.05, 0.0, 0.25),
    "brass": ((0.55, 0.38, 0.12), 0.35, 1.0, 1.0),
}
_materials: dict[str, bpy.types.Material] = {}


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    _materials.clear()


def material(name: str, image: Path | None = None) -> bpy.types.Material:
    key = name + (str(image) if image else "")
    if key in _materials:
        return _materials[key]
    color, rough, metal, alpha = PALETTE.get(name, PALETTE["white"])
    mat = bpy.data.materials.new("MAT_RL_" + (image.stem if image else name))
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
    if image:
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(image))
        node.interpolation = "Closest" if "aruco" in image.stem else "Linear"
        mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    _materials[key] = mat
    return mat


def _finish(obj, mat_name: str | None, image: Path | None = None):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if mat_name:
        obj.data.materials.clear()
        obj.data.materials.append(material(mat_name, image))
    return obj


def cube(size, loc, mat="white", rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.scale = size
    return _finish(obj, mat)


def cyl(radius, depth, loc, mat="alu", rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    return _finish(bpy.context.object, mat)


def tube(p0, p1, radius, mat="alu", verts=12):
    a, b = Vector(p0), Vector(p1)
    direction = b - a
    rot = direction.to_track_quat("Z", "Y").to_euler()
    return cyl(radius, direction.length, (a + b) / 2, mat, rot, verts)


def torus(major, minor, loc, mat="red", rot=(0, 0, 0), segments=32):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=segments,
                                     minor_segments=10, location=loc, rotation=rot)
    return _finish(bpy.context.object, mat)


def sphere(radius, loc, mat="red"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=loc)
    return _finish(bpy.context.object, mat)


def textured_plane(width, height, loc, image: Path, rot=(math.pi / 2, 0, 0)):
    """Plane with full 0..1 UVs; default rotation makes it face -Y, +u to the right."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.scale = (width, height, 1)
    return _finish(obj, "white", image)


def screen_plane(width, height, loc, rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.scale = (width, height, 1)
    return _finish(obj, "screen")


def disc_planar_uv(radius, z, mat_name, image: Path | None = None, segments=96):
    """Flat disc facing +Z with top-down planar UVs (u = +x, v = +y)."""
    mesh = bpy.data.meshes.new("disc")
    bm = bmesh.new()
    centre = bm.verts.new((0, 0, z))
    ring = [bm.verts.new((radius * math.cos(2 * math.pi * i / segments),
                          radius * math.sin(2 * math.pi * i / segments), z)) for i in range(segments)]
    for i in range(segments):
        bm.faces.new((centre, ring[i], ring[(i + 1) % segments]))
    uv = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            loop[uv].uv = (co.x / (2 * radius) + 0.5, co.y / (2 * radius) + 0.5)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("disc", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return _finish(obj, mat_name, image)


def half_shape(obj, keep_above_z=0.0):
    """Cut a mesh at z and keep the upper half (UVs are preserved by bisect)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                           plane_co=(0, 0, keep_above_z), plane_no=(0, 0, 1), clear_inner=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def part(name, objects, pivot=None):
    """Join objects into one named part; optional rotation centre in source coordinates."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    if pivot is not None:
        obj["suggested_source_pivot"] = [float(v) for v in pivot]
    return obj


# --- assets -----------------------------------------------------------------------

def station_marker():
    legs = []
    for i, angle in enumerate((90, 210, 330), start=1):
        a = math.radians(angle)
        foot = (0.45 * math.cos(a), 0.45 * math.sin(a), 0.0)
        legs.append(part(f"leg_{i}", [tube((0, 0, 0.36), foot, 0.012), cyl(0.03, 0.01, foot, "rubber")]))
    pole = part("body_pole", [cyl(0.02, 1.70, (0, 0, 0.85))])
    flag = part("flag", [tube((0, 0, 1.63), (0.49, 0, 1.63), 0.008),
                         cube((0.45, 0.004, 0.30), (0.26, 0, 1.47), "red")])
    plate = part("id_plate", [cube((0.26, 0.006, 0.13), (0, -0.026, 1.12), "white"),
                              cube((0.28, 0.004, 0.15), (0, -0.022, 1.12), "graphite")])
    beacon = part("beacon", [sphere(0.035, (0, 0, 1.74), "red")])
    return [*legs, pole, flag, plate, beacon], {
        "purpose": "Station flag / survey marker (proje kılavuzu M10 'istasyon bayrağı')",
        "notes": "Blank ID plate: station number is shown with an Unreal decal or text render.",
    }


def relay_mast():
    legs = []
    for i, angle in enumerate((90, 210, 330), start=1):
        a = math.radians(angle)
        foot = (0.9 * math.cos(a), 0.9 * math.sin(a), 0.0)
        legs.append(part(f"leg_{i}", [tube((0, 0, 0.9), foot, 0.02), cyl(0.05, 0.015, foot, "rubber")]))
    mast = part("body_mast", [cyl(0.035, 2.6, (0, 0, 1.3))])
    box = part("body_box", [cube((0.32, 0.22, 0.28), (0, -0.15, 0.69), "white"),
                            cube((0.33, 0.012, 0.06), (0, -0.265, 0.79), "red")])
    tilt = math.radians(-35)  # face the sky and the front
    solar = part("solar_panel", [cube((0.62, 0.025, 0.42), (0, -0.2, 1.55), "solar", rot=(tilt, 0, 0)),
                                 tube((0, -0.035, 1.55), (0, -0.19, 1.55), 0.015)])
    head = part("antenna_head", [cyl(0.06, 0.08, (0, 0, 2.64), "graphite"),
                                 cube((0.40, 0.03, 0.40), (0, -0.09, 2.88), "white", rot=(math.radians(-10), 0, 0)),
                                 tube((0, 0, 2.68), (0, -0.07, 2.80), 0.02),
                                 tube((0.0, 0, 2.66), (0.12, 0, 2.66), 0.01, "graphite"),
                                 tube((0.12, 0, 2.66), (0.12, 0, 3.5), 0.006, "graphite")])
    return [*legs, mast, box, solar, head], {
        "purpose": "Radio relay point (kılavuz M10 'röle direği', S05 röle noktası)",
        "notes": "Flat-panel antenna with pan head (antenna_head, pivot at its base) and a whip.",
    }


def equipment_cart():
    radius, y_axle = 0.25, 0.10
    wheels = []
    for side, x in (("L", 0.43), ("R", -0.43)):
        wheels.append(part(f"wheel_{side}", [cyl(radius, 0.09, (x, y_axle, radius), "rubber", rot=(0, math.pi / 2, 0)),
                                             cyl(0.07, 0.11, (x, y_axle, radius), "alu", rot=(0, math.pi / 2, 0))],
                           pivot=(x, y_axle, radius)))
    z = 0.47
    frame = part("body_frame", [tube((-0.33, -0.75, z), (-0.33, 0.45, z), 0.016), tube((0.33, -0.75, z), (0.33, 0.45, z), 0.016),
                                tube((-0.33, -0.75, z), (0.33, -0.75, z), 0.016), tube((-0.33, 0.45, z), (0.33, 0.45, z), 0.016),
                                tube((-0.39, y_axle, radius), (0.39, y_axle, radius), 0.018),
                                tube((-0.33, y_axle, z), (-0.33, y_axle, radius), 0.016),
                                tube((0.33, y_axle, z), (0.33, y_axle, radius), 0.016)])
    tray = part("body_tray", [cube((0.62, 0.95, 0.22), (0, -0.15, z + 0.12), "white"),
                              cube((0.63, 0.96, 0.02), (0, -0.15, z + 0.235), "graphite")])
    handle = part("handle", [tube((-0.30, -0.75, z), (0, -1.25, 0.95), 0.014), tube((0.30, -0.75, z), (0, -1.25, 0.95), 0.014),
                             tube((-0.18, -1.27, 0.96), (0.18, -1.27, 0.96), 0.02, "graphite")])
    rack = part("tool_rack", [tube((-0.28, 0.43, z), (-0.28, 0.43, 1.05), 0.012), tube((0.28, 0.43, z), (0.28, 0.43, 1.05), 0.012),
                              tube((-0.28, 0.43, 1.0), (0.28, 0.43, 1.0), 0.012),
                              *[cyl(0.022, 0.08, (x, 0.43, 0.92), "red") for x in (-0.16, 0.0, 0.16)]])
    stand = part("leg_stand", [tube((0, -0.72, z), (0, -0.80, 0.0), 0.014), cyl(0.04, 0.012, (0, -0.80, 0.006), "rubber")])
    return [*wheels, frame, tray, handle, rack, stand], {
        "purpose": "Hand-pulled equipment cart (kılavuz M10 'alet arabası'); Apollo MET-like layout, SCENARIO design",
        "notes": "Two wheels roll about master +Y; the astronaut pulls the handle at the front (+X).",
    }


def valve_panel():
    aruco = TEXTURES["aruco"]
    plate = aruco["plate_size_m"]
    panel = part("body_panel", [cube((1.0, 0.05, 0.8), (0, 0.025, 0.4), "graphite"),
                                cube((0.92, 0.01, 0.72), (0, -0.005, 0.4), "white")])
    pipes = [tube((-0.46, -0.08, 0.22), (0.46, -0.08, 0.22), 0.025)]
    for x in (-0.46, 0.46):
        pipes.append(tube((x, -0.08, 0.22), (x, 0.0, 0.22), 0.025))
    valves = []
    for i, x in enumerate((-0.3, 0.0, 0.3), start=1):
        pipes += [tube((x, -0.08, 0.22), (x, -0.08, 0.47), 0.02), cyl(0.04, 0.09, (x, -0.08, 0.5), "brass")]
        centre = (x, -0.16, 0.5)
        spokes = [tube((x - 0.06, -0.16, 0.5), (x + 0.06, -0.16, 0.5), 0.006, "red"),
                  tube((x, -0.16, 0.44), (x, -0.16, 0.56), 0.006, "red")]
        valves.append(part(f"valve_{i}", [torus(0.065, 0.009, centre, "red", rot=(math.pi / 2, 0, 0)),
                                           *spokes, tube((x, -0.125, 0.5), (x, -0.17, 0.5), 0.01, "alu")], pivot=centre))
    pipes_part = part("pipes", pipes)
    gauge_centre = (0.0, -0.05, 0.70)
    gauge = part("gauge", [cyl(0.075, 0.03, (0, -0.035, 0.70), "graphite", rot=(math.pi / 2, 0, 0)),
                           cyl(0.065, 0.004, (0, -0.052, 0.70), "white", rot=(math.pi / 2, 0, 0))])
    needle = part("gauge_needle", [cube((0.006, 0.003, 0.055), (0.0, -0.056, 0.725), "red")], pivot=gauge_centre)
    markers = []
    for marker, x in zip(aruco["markers"], (-0.36, 0.36)):
        image = ROOT / marker["png"]
        # Backing spans y -0.015..-0.010 (on the white plate); the marker face sits 0.5 mm in front.
        markers.append(part(f"aruco_{marker['id']}", [textured_plane(plate, plate, (x, -0.0155, 0.62), image),
                                                      cube((plate + 0.01, 0.005, plate + 0.01), (x, -0.0125, 0.62), "graphite")]))
    return [panel, pipes_part, *valves, gauge, needle, *markers], {
        "purpose": "Habitat service-line valve panel (kılavuz H06, optional Evre 5 sub-task: ArUco ID + arm action)",
        "notes": "Handwheels and gauge needle rotate about the panel normal (master +X). ArUco plates carry the exact "
                 "OpenCV pattern; keep the texture unfiltered/uncompressed so the bit cells stay sharp.",
        "aruco": aruco,
    }


def drone_pad():
    texture = TEXTURES["drone_pad"]
    pad = part("body_pad", [cyl(1.5, 0.05, (0, 0, 0.025), "graphite", verts=64),
                            disc_planar_uv(1.48, 0.0506, "white", ROOT / texture["png"])])
    lights = [cube((0.09, 0.05, 0.03), (1.47 * math.cos(a), 1.47 * math.sin(a), 0.065), "red", rot=(0, 0, a))
              for a in (2 * math.pi * k / 8 for k in range(8))]
    return [pad, part("edge_lights", lights)], {
        "purpose": "Drone landing pad (kılavuz H04)",
        "notes": "Texture heading mark points to source +Y (master -X after the +90° build rotation); "
                 "edge lights are plain geometry, emission is set in the engine.",
        "texture": texture,
    }


def rover_garage():
    radius, length = 2.6, 7.0
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=length, end_fill_type="NOTHING",
                                        location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    shell = _finish(bpy.context.object, "fabric")
    half_shape(shell)
    solid = shell.modifiers.new("shell", "SOLIDIFY")
    solid.thickness = 0.06
    bpy.ops.object.modifier_apply(modifier=solid.name)
    ribs = []
    for y in (-3.4, -2.04, -0.68, 0.68, 2.04, 3.4):
        rib = torus(radius + 0.04, 0.06, (0, y, 0), "graphite", rot=(math.pi / 2, 0, 0), segments=48)
        ribs.append(half_shape(rib))
    back = cyl(radius, 0.06, (0, length / 2 - 0.03, 0), "fabric", rot=(math.pi / 2, 0, 0), verts=48)
    half_shape(back)
    floor = cube((2 * radius + 0.1, length, 0.05), (0, 0, 0.025), "graphite")
    return [part("body_shell", [shell]), part("ribs", ribs), part("back_wall", [back]), part("floor_pad", [floor])], {
        "purpose": "Inflatable rover garage (kılavuz H03); open front toward master +X",
        "notes": "Clear width 5.2 m, ridge 2.66 m: fits the 3.94 x 2.78 x 2.21 m rover_1 package with margin. "
                 "Shell is visual; ingress collision must be checked in the engine.",
    }


def map_table():
    frame = part("body_frame", [cube((1.6, 1.0, 0.06), (0, 0, 0.87), "white"),
                                cube((1.62, 1.02, 0.012), (0, 0, 0.836), "red")])
    pedestal = part("body_pedestal", [cube((0.5, 0.3, 0.84), (0, 0, 0.42), "graphite"),
                                      cube((0.9, 0.6, 0.04), (0, 0, 0.02), "graphite")])
    screen = part("screen_top", [screen_plane(1.5, 0.9, (0, 0, 0.901), rot=(0, 0, 0))])
    return [frame, pedestal, screen], {
        "purpose": "Habitat map table (kılavuz H01 'harita masası')",
        "notes": "screen_top has full 0..1 UVs for the live map render target.",
    }


def console_desk():
    desk = part("body_desk", [cube((1.8, 0.8, 0.05), (0, 0, 0.745), "white"),
                              cube((0.05, 0.7, 0.72), (-0.86, 0.02, 0.36), "graphite"),
                              cube((0.05, 0.7, 0.72), (0.86, 0.02, 0.36), "graphite")])
    monitors, screens = [], []
    # Side monitors turn toward the operator (positive yaw on the left, x < 0) and come forward.
    for i, (x, yaw) in enumerate(((-0.62, 0.35), (0.0, 0.0), (0.62, -0.35)), start=1):
        y = 0.22 - 0.08 * abs(yaw) / 0.35
        rot = (math.pi / 2 - math.radians(10), 0, yaw)
        monitors += [cube((0.62, 0.04, 0.38), (x, y + 0.025, 1.12), "graphite", rot=(-math.radians(10), 0, yaw)),
                     tube((x, y + 0.06, 0.77), (x, y + 0.06, 0.95), 0.02, "alu")]
        offset = Vector((0, -0.021, 0)) @ Matrix.Rotation(-yaw, 3, "Z")
        screens.append(part(f"screen_{i}", [screen_plane(0.58, 0.34, (x + offset.x, y + offset.y, 1.12), rot=rot)]))
    controls = part("controls", [cube((0.5, 0.18, 0.025), (0, -0.2, 0.783), "graphite"),
                                 cyl(0.02, 0.12, (0.45, -0.2, 0.83), "graphite"), sphere(0.025, (0.45, -0.2, 0.9), "red")])
    return [desk, part("monitors", monitors), *screens, controls], {
        "purpose": "Robot console desk (kılavuz H01 'robot konsolu')",
        "notes": "Three screen_N planes with full UVs face the operator side (master +X after the build rotation).",
    }


def lab_bench():
    bench = part("body_bench", [cube((2.0, 0.75, 0.05), (0, 0, 0.905), "white"),
                                cube((1.9, 0.65, 0.84), (0, 0.02, 0.44), "graphite")])
    glovebox = [cube((0.92, 0.62, 0.04), (-0.35, 0.02, 0.95), "graphite"),
                cube((0.92, 0.62, 0.04), (-0.35, 0.02, 1.57), "graphite"),
                cube((0.9, 0.6, 0.6), (-0.35, 0.02, 1.26), "glass")]
    for x in (-0.55, -0.15):
        glovebox.append(torus(0.075, 0.012, (x, -0.29, 1.2), "graphite", rot=(math.pi / 2, 0, 0)))
    rack = [cube((0.4, 0.15, 0.06), (0.55, 0.15, 0.96), "white")]
    rack += [cyl(0.012, 0.13, (0.40 + 0.06 * k, 0.15, 1.02), "alu") for k in range(6)]
    instrument = part("instrument", [cube((0.35, 0.3, 0.28), (0.55, -0.12, 1.07), "white"),
                                     screen_plane(0.2, 0.12, (0.55, -0.271, 1.1))])
    return [bench, part("glovebox", glovebox), part("rack", rack), instrument], {
        "purpose": "Sample laboratory bench with glovebox (kılavuz H05, optional)",
        "notes": "Glass uses alpha 0.25 in Blender; the engine material decides translucency. Results stay model-labelled.",
    }


def mission_wall():
    frame = part("body_frame", [cube((3.2, 0.08, 1.8), (0, 0.04, 0.9), "graphite"),
                                cube((3.22, 0.09, 0.03), (0, 0.04, 0.015), "red")])
    screen = part("screen_wall", [screen_plane(3.1, 1.7, (0, -0.001, 0.9))])
    return [frame, screen], {
        "purpose": "Mission wall display (kılavuz H01 'görev duvarı')",
        "notes": "Wall-mounted; screen_wall has full UVs for the timeline/plan render target.",
    }


def storage_rack():
    posts = [cyl(0.02, 1.8, (x, y, 0.9), "alu", verts=8) for x in (-0.58, 0.58) for y in (-0.23, 0.23)]
    shelves = [cube((1.2, 0.5, 0.03), (0, 0, z), "white") for z in (0.1, 0.65, 1.2, 1.75)]
    bins = [cube((0.36, 0.4, 0.22), (x, 0, z + 0.125), "graphite") for x in (-0.38, 0.0, 0.38) for z in (0.1, 0.65)]
    return [part("body_rack", posts + shelves), part("bins", bins)], {
        "purpose": "Container/tool rack (kılavuz H03 'kap rafı')",
        "notes": "Bins are generic boxes; sample_case can be placed on the shelves instead.",
    }


BUILDERS = {f.__name__: f for f in (station_marker, relay_mast, equipment_cart, valve_panel, drone_pad,
                                    rover_garage, map_table, console_desk, lab_bench, mission_wall, storage_rack)}


def export(aid: str) -> dict:
    reset()
    objects, info = BUILDERS[aid]()
    for o in objects:
        if not o.data.uv_layers:
            raise ValueError(f"{aid}/{o.name} has no UV map")
    lo = Vector((min(v[i] for o in objects for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
    hi = Vector((max(v[i] for o in objects for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
    folder = ROOT / "incoming" / aid
    folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(folder / "source.glb"), export_format="GLB", use_selection=True,
                              export_extras=True, export_yup=True)
    record = {
        "asset_id": aid,
        "kind": "REDLINE procedural original geometry",
        "provenance": {"status": "SCENARIO", "note": "Original procedural prop; dimensions are design choices, not "
                                                      "measured hardware. No generative AI and no third-party mesh."},
        "generator": {"script": "production/procedural_assets.py", "sha256": SCRIPT_SHA, "blender": bpy.app.version_string},
        "source_frame": "metres, +Z up, front toward -Y (build_package rotates +90° Z -> front +X)",
        "source_dimensions_m": [hi[i] - lo[i] for i in range(3)],
        "parts": [{"name": o.name, "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
                   "suggested_source_pivot": list(o["suggested_source_pivot"]) if "suggested_source_pivot" in o else None}
                  for o in objects],
        **info,
    }
    (folder / "generator.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("GENERATED", aid, [round(v, 3) for v in record["source_dimensions_m"]], len(objects), "parts", flush=True)
    return record


if __name__ == "__main__":
    ids = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for aid in ids or list(BUILDERS):
        export(aid)
