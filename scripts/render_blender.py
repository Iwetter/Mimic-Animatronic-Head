"""Blender background renderer. Input geometry is tessellated directly from named STEP."""
import bpy,json,pathlib,sys,math
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];scene_file,out=map(pathlib.Path,args)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1600;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world.color=(.22,.22,.22)
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-1.5
def mat(name,color,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=.38
    return m
steel=mat('Grey PLA mechanism',(.30,.37,.42),.35)
dark=mat('Dark PLA structure',(.065,.09,.105),.15)
white=mat('Eye white',(.85,.83,.76));iris=mat('Iris',(.32,.20,.065));teeth=mat('Teeth',(.75,.71,.59))
hardware=mat('Metal hardware',(.53,.58,.62),.8);servo=mat('Nominal servo',(.04,.075,.12))
obj=[]
for item in json.loads(scene_file.read_text()):
    mesh=bpy.data.meshes.new(item['name']);mesh.from_pydata(item['v'],[],item['f']);mesh.update()
    o=bpy.data.objects.new(item['name'],mesh);scene.collection.objects.link(o)
    name=item['name'];pid=name[:3]
    material=white if pid=='P34' else iris if pid=='P35' else teeth if pid in ('P42','P43') else servo if 'servo' in name.lower() or 'MG90' in name or 'SG90' in name else hardware if not name.startswith('P') else dark if pid in ('P20','P21','P22','P25','P26','P27','P30','P31','P36','P41','P44') else steel
    o.data.materials.append(material);obj.append(o)
def area(name,loc,power,size,target=(0,0,.1)):
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.name=name
    light.data.energy=power;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(Vector(target)-light.location).to_track_quat('-Z','Y').to_euler()
area('Key',(.5,-.6,.65),110,.5);area('Fill',(-.45,-.2,.3),70,.4);area('Rim',(.2,.45,.55),120,.4)
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.clip_end=100
def render(name,eye,target,scale,hide=()):
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    for o in obj:o.hide_render=any(o.name.startswith(h) for h in hide)
    scene.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)
render('assembly_three_quarter.png',(.42,-.65,.31),(0,0,.09),.36)
render('assembly_front.png',(0,-.65,.09),(0,0,.09),.34)
render('assembly_side.png',(.65,0,.09),(0,0,.09),.34)
shell=('P23','P24','P25','P26','P27','P28','P29','P30','P31')
render('mechanism_view.png',(.36,-.6,.3),(0,0,.11),.31,shell)
# Explode named subassemblies in fixed, documented directions; no part geometry edits.
offsets={}
for o in obj:
    pid=o.name[:3];v=Vector((0,0,0))
    if pid in ('P23','P24'):v.x=-.10 if pid=='P23' else .10
    elif pid in ('P21','P22'):v.x=-.065 if pid=='P21' else .065
    elif pid in ('P25','P26','P27','P28'):v.z=.10
    elif pid in ('P29','P30','P31','P32','P42'):v.y=-.09
    elif pid in ('P33','P43'):v.y=-.055;v.z=-.05
    elif pid in ('P01','P03'):v.z=-.065
    o.location+=v;offsets[o.name]=list(v)
render('assembly_exploded.png',(.7,-1,.55),(0,-.02,.09),.58)
(out/'exploded_offsets.json').write_text(json.dumps({'units':'metres','description':'Presentation offsets only; see assembly STEP for true coordinates','offsets':offsets},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'assembly_presentation.blend'))
