"""Render assembly diagrams from the retrofit's existing CAD meshes.

Run with Blender in background mode, passing the retrofit directory after --.
Colors and exploded offsets are for illustration. This script creates no print geometry.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUTPUT = ROOT / "preview" / "assembly"
OUTPUT.mkdir(parents=True, exist_ok=True)

TEAL = (0.08, 0.64, 0.66, 1)
GRAY = (0.51, 0.56, 0.63, 1)
GOLD = (0.95, 0.62, 0.16, 1)
BLUE = (0.16, 0.36, 0.83, 1)
GREEN = (0.33, 0.72, 0.32, 1)
STEEL = (0.23, 0.26, 0.34, 1)


def matches(name, selectors):
    return any(name.startswith(s[:-1]) if s.endswith("*") else name == s for s in selectors)


def add_mesh(file, name):
    bpy.ops.wm.stl_import(filepath=str(ROOT / file), global_scale=0.001)
    obj = bpy.context.object
    obj.name = name
    return obj


def draw(filename, camera_direction, groups, offsets=()):
    visible = []
    for name, obj in objects.items():
        color = next((color for color, names in groups if matches(name, names)), None)
        obj.hide_render = color is None
        if color is None:
            continue
        obj.color = color
        offset = next((offset for names, offset in offsets if matches(name, names)), (0, 0, 0))
        obj.location = home[name] + Vector(offset) * 0.001
        visible.append(obj)

    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(corner) for obj in visible for corner in obj.bound_box]
    direction = Vector(camera_direction).normalized()
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    rotation = camera.rotation_euler.to_matrix()
    view = [rotation.transposed() @ point for point in points]
    low = Vector(tuple(min(v[i] for v in view) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in view) for i in range(3)))
    camera.location = rotation @ ((low + high) / 2) + direction
    camera.data.ortho_scale = max(high.x - low.x, (high.y - low.y) * 1.35) * 1.12
    scene.render.filepath = str(OUTPUT / filename)
    bpy.ops.render.render(write_still=True)


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1080
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.background_type = "WORLD"
scene.world.color = (0.12, 0.15, 0.20)
scene.view_settings.view_transform = "Standard"

objects = {}
for entry in json.loads((ROOT / "source/assembly_scene.json").read_text()):
    objects[entry["name"]] = add_mesh(entry["file"], entry["name"])

for index, path in enumerate(sorted((ROOT / "FIT_TEST_FIRST").glob("*.stl"))):
    name = path.name.split("_")[0]
    objects[name] = add_mesh(path.relative_to(ROOT), name)
    objects[name].location.x += index * 0.034

home = {name: obj.location.copy() for name, obj in objects.items()}
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.clip_start = 0.001
scene.camera = camera

draw("00-fit-coupons.png", (0.03, -0.65, 1), [
    (TEAL, ("T01",)), (BLUE, ("T02",)), (GRAY, ("T03",)), (GOLD, ("T04",)),
])
draw("01-neck.png", (1, 0.66, 0.6), [
    (GRAY, ("P01",)), (TEAL, ("P03",)), (GOLD, ("neck_nut*",)), (STEEL, ("neck_bolt*", "neck_head*")),
], [
    (("P01", "neck_head*", "neck_bolt*"), (0, 0, -28)),
    (("neck_nut*",), (0, 9, 0)),
])
draw("02-servo-mounts.png", (-1, 0.8, 0.42), [
    (GRAY, ("P04",)), (BLUE, ("servo_eye", "servo_jaw")), (TEAL, ("A01_eye*",)),
    (GOLD, ("A03_jaw*",)), (STEEL, ("eye_mount*", "jaw_mount*")),
], [
    (("A01_eye*", "eye_mount_head*", "eye_mount_screw*"), (0, 0, 10)),
    (("A03_jaw*", "jaw_mount_head*", "jaw_mount_screw*"), (-12, 0, 0)),
])
draw("03-eye-pivots.png", (0.52, 1, 0.22), [
    (TEAL, ("P05_L",)), (BLUE, ("P10_L*",)), (GOLD, ("eye_nut_L*",)),
    (STEEL, ("eye_pin_L*", "eye_pin_head_L*")),
], [
    (("eye_pin_L115", "eye_pin_head_L140", "eye_nut_L130.2", "eye_nut_L132.6", "P10_L134"), (0, 0, 14)),
    (("eye_pin_L85", "eye_pin_head_L82", "eye_nut_L90", "eye_nut_L92.4", "P10_L90"), (0, 0, -14)),
])
draw("04-eye-horn.png", (0.9, -1, 0.8), [
    (BLUE, ("servo_eye",)), (GREEN, ("OEM_eye_horn",)), (TEAL, ("P07",)),
    (GOLD, ("A02_eye",)), (STEEL, ("horn_eye*",)),
], [
    (("P07", "horn_eye_nut*"), (0, 0, 19)),
    (("OEM_eye_horn",), (0, 0, 12)),
    (("A02_eye", "horn_eye_head*", "horn_eye_screw*"), (0, 0, 5)),
])
draw("05-eye-link.png", (0.24, 1, 0.78), [
    (GRAY, ("P05_L", "P05_R", "P07")), (TEAL, ("P06",)), (BLUE, ("P11_*",)),
    (GOLD, ("link_nut*",)), (STEEL, ("link_pin*", "link_head*")),
], [
    (("P06", "link_nut*"), (0, 0, 8)),
    (("P11_*",), (0, 0, 4)),
])
draw("06-jaw.png", (-0.91, 0.54, 0.7), [
    (TEAL, ("P08",)), (GRAY, ("P18", "P19")), (BLUE, ("servo_jaw", "P09")),
    (GREEN, ("OEM_jaw_horn",)), (GOLD, ("A02_jaw", "jaw_pivot_nut*")),
    (STEEL, ("horn_jaw*", "jaw_pivot_head", "jaw_pivot_screw")),
], [
    (("P08", "horn_jaw*"), (-24, 0, 0)),
    (("OEM_jaw_horn",), (-15, 0, 0)),
    (("A02_jaw",), (-8, 0, 0)),
    (("jaw_pivot_head", "jaw_pivot_screw", "P09"), (13, 0, 0)),
])
draw("06a-jaw-horn.png", (-0.5, 1, 0.65), [
    (TEAL, ("P08",)), (BLUE, ("servo_jaw",)), (GREEN, ("OEM_jaw_horn",)),
    (GOLD, ("A02_jaw",)), (STEEL, ("horn_jaw*",)),
], [
    (("P08", "horn_jaw_head*", "horn_jaw_screw*"), (-34, 0, 0)),
    (("OEM_jaw_horn",), (-19, 0, 0)),
    (("A02_jaw", "horn_jaw_nut*"), (-9, 0, 0)),
])
draw("07-outer-panels.png", (0.88, -1, 0.48), [
    (TEAL, ("P04", "P05_*", "P08")), (BLUE, ("P12",)), (GOLD, ("P13",)),
    (GRAY, ("P18", "P19", "P01", "P03")),
], [
    (("P12",), (0, -30, 0)),
    (("P13",), (0, 29, 0)),
])
