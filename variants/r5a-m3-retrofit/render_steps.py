"""Render the checked V5 M3 assembly and selected installation details."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def matches(name, patterns):
    return any(name.startswith(p[:-1]) if p.endswith("*") else name == p for p in patterns)


def render(filename, view, patterns=("*",), offsets=(), accent=()):
    points = []
    for name, obj in objects.items():
        show = matches(name, patterns)
        obj.hide_render = not show
        if not show:
            continue
        offset = next((v for keys, v in offsets if matches(name, keys)), (0, 0, 0))
        obj.location = base[name] + Vector(offset) * 0.001
        obj.color = GOLD if matches(name, accent) else colors[name]
    bpy.context.view_layer.update()
    for obj in objects.values():
        if not obj.hide_render:
            points.extend(obj.matrix_world @ Vector(v) for v in obj.bound_box)
    normal = Vector(view).normalized()
    cam.rotation_euler = (-normal).to_track_quat("-Z", "Y").to_euler()
    rot = cam.rotation_euler.to_matrix()
    projected = [rot.transposed() @ p for p in points]
    low = Vector(tuple(min(p[i] for p in projected) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in projected) for i in range(3)))
    cam.location = rot @ ((low + high) / 2) + normal
    cam.data.ortho_scale = 1.12 * max(high.x - low.x, (high.y - low.y) * 1.35)
    scene.render.filepath = str(output / filename)
    bpy.ops.render.render(write_still=True)


argv = sys.argv[sys.argv.index("--") + 1:]
assembly, output = map(Path, argv)
output.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1350
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.display.shading.color_type = "OBJECT"
scene.display.shading.light = "STUDIO"
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.background_type = "WORLD"
scene.world.color = (0.13, 0.16, 0.21)
scene.view_settings.view_transform = "Standard"

TEAL, GRAY, BLUE, GOLD, STEEL = (
    (0.10, 0.68, 0.68, 1), (0.62, 0.66, 0.72, 1),
    (0.20, 0.38, 0.77, 1), (0.94, 0.61, 0.16, 1), (0.23, 0.27, 0.32, 1),
)
reused = {"P01", "P20", "P35_L", "P35_R"}
objects, colors = {}, {}
for item in json.loads((assembly / "scene.json").read_text()):
    name = item["name"]
    bpy.ops.wm.stl_import(filepath=str(assembly / item["file"]), global_scale=0.001)
    obj = bpy.context.object
    obj.name = name
    objects[name] = obj
    if name.startswith(("MG90S", "SG90")) and not name.endswith(("_clip", "_screw", "_nut")):
        color = BLUE
    elif name in reused:
        color = GRAY
    elif name.startswith("OEM_horn") or name.endswith(("_clip", "_plate")):
        color = GOLD
    elif name.startswith("P") or name.endswith(("/top", "/back", "_shim", "_spacer")):
        color = TEAL
    else:
        color = STEEL
    colors[name] = color
base = {name: obj.location.copy() for name, obj in objects.items()}
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.clip_start = 0.001
scene.camera = cam

render("01-complete.png", (0.7, -1, 0.38))
render("02-neck.png", (0.8, 1, 0.5), ("P01", "P03", "P20", "neck_*"),
       ((("P01", "neck_*"), (0, 0, -27)),))
render("03-servo-mounts.png", (-0.62, 1, 0.48),
       ("P41", "P44", "P45", "MG90S*", "SG90*"))
render("04-eye-shaft.png", (0.43, 1, 0.2),
       ("P34_L", "P37_L", "P34_L_clamp*", "P37_L_clamp*", "STEEL_yaw_shaft_L", "yaw_L_axial_shim"),
       ((("P34_L", "P34_L_clamp*"), (0, 0, 11)), (("P37_L", "P37_L_clamp*"), (0, 0, -8))),
       ("yaw_L_axial_shim",))
render("05-lids-and-stops.png", (0.46, -1, 0.26),
       ("P36", "P39_L", "P40_R", "P45", "hinge_*", "P49_L", "P49_R", "lid_L_screw", "lid_R_screw"))
render("06-pitch-horn.png", (0.9, -0.5, 0.32),
       ("MG90S_CH2_pitch", "OEM_horn_CH2", "pitch/*", "P46"),
       ((("pitch/top", "pitch/pivot_*", "P46"), (8, 0, 0)),
        (("OEM_horn_CH2",), (4, 0, 0))), ("OEM_horn_CH2",))
render("07-jaw.png", (-0.88, 0.67, 0.44),
       ("P33", "P43", "P44", "jaw_*", "MG90S_CH1_jaw*", "OEM_horn_CH1_double"))
render("08-mechanism-rear.png", (0.24, 1, 0.36),
       ("P34_*", "P36", "P37_*", "P38_*", "P39_L", "P40_R", "P41", "P45", "P46", "P49_*",
        "MG90S_CH0_yaw*", "MG90S_CH2_pitch*", "SG90*", "yaw/*", "pitch/*", "lid_L/*", "lid_R/*"))
