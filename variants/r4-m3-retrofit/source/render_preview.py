import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.14,.17,.22,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
objects=[];mats={}
for i in json.loads((ROOT/'source/assembly_scene.json').read_text()):
    bpy.ops.wm.stl_import(filepath=str(ROOT/i['file']),global_scale=.001)
    o=bpy.context.object;o.name=i['name'];o['pid']=i['pid'];objects.append(o)
    key=tuple(i['color'])
    if key not in mats:
        m=bpy.data.materials.new(str(key));m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*key,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.55;mats[key]=m
    o.data.materials.append(mats[key])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(ROOT/'preview/Mimic_M3_assembly.glb'),export_format='GLB',use_selection=True)
def look(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.35,-.65,.29));cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.29;cam.data.clip_start=.001;look(cam,(0,0,.045))
for loc,power,size in [((.3,-.4,.6),6,.4),((-.4,-.2,.3),4,.3),((.1,.4,.6),7,.4)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;look(o,(0,0,.08))
scene.render.filepath=str(ROOT/'preview/01_complete.png');bpy.ops.render.render(write_still=True)
for o in objects:
    if o['pid'] in ['P12','P13']:o.hide_render=True
cam.location=(.31,.60,.35);look(cam,(0,-.005,.06));scene.render.filepath=str(ROOT/'preview/02_mechanism_rear.png');bpy.ops.render.render(write_still=True)
