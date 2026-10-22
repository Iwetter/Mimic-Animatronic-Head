"""3MF and extrusion-preview helpers. All lengths are millimetres."""
from __future__ import annotations
import collections, hashlib, io, json, pathlib, re, zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import lib3mf
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw, ImageFont

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
def tag(n): return '{'+CORE+'}'+n
ET.register_namespace('',CORE)

def sha256(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def write_3mf(path, meshes, items, title):
    """Core-spec 3MF with independent named model resources and build instances."""
    root=ET.Element(tag('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    ET.SubElement(root,tag('metadata'),{'name':'Title'}).text=title
    ET.SubElement(root,tag('metadata'),{'name':'Application'}).text='Mimic R5a deterministic print packager'
    ET.SubElement(root,tag('metadata'),{'name':'Description'}).text='Geometry only; printer settings are present only in Orca-saved sliced projects.'
    resources=ET.SubElement(root,tag('resources'));ids={}
    for i,(name,mesh) in enumerate(meshes.items(),1):
        ids[name]=str(i);obj=ET.SubElement(resources,tag('object'),{'id':str(i),'type':'model','name':name})
        me=ET.SubElement(obj,tag('mesh'));ve=ET.SubElement(me,tag('vertices'));fa=ET.SubElement(me,tag('triangles'))
        for v in mesh.vertices:
            ET.SubElement(ve,tag('vertex'),{k:format(float(x),'.10g') for k,x in zip('xyz',v)})
        for f in mesh.faces:
            ET.SubElement(fa,tag('triangle'),{f'v{k+1}':str(int(x)) for k,x in enumerate(f)})
    build=ET.SubElement(root,tag('build'))
    for name,matrix in items:
        # 3MF uses a row-vector 4x3 transform; our matrices use column vectors.
        values=matrix[:3,:].T.reshape(-1)
        ET.SubElement(build,tag('item'),{'objectid':ids[name],'transform':' '.join(format(float(x),'.10g') for x in values)})
    entries={'3D/3dmodel.model':ET.tostring(root,encoding='utf-8',xml_declaration=True),
      '[Content_Types].xml':b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
      '_rels/.rels':b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'}
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in entries.items():
            info=zipfile.ZipInfo(name,(2026,10,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)

def transform(text):
    mat=np.eye(4)
    if text:mat[:3,:]=np.array([float(x) for x in text.split()]).reshape(4,3).T
    return mat

def read_3mf_meshes(path):
    """Read core and production component hierarchies, preserving build instances."""
    result=[]
    with zipfile.ZipFile(path) as z:
        roots={}
        def getroot(name):
            name=name.lstrip('/')
            if name not in roots:roots[name]=ET.fromstring(z.read(name))
            return roots[name]
        def walk(file,oid,parent):
            root=getroot(file)
            obj=next(x for x in root.find(tag('resources')) if x.get('id')==oid)
            mesh=obj.find(tag('mesh'))
            if mesh is not None:
                verts=np.array([[float(v.get(k)) for k in 'xyz'] for v in mesh.find(tag('vertices'))])
                faces=np.array([[int(t.get(k)) for k in ['v1','v2','v3']] for t in mesh.find(tag('triangles'))])
                m=trimesh.Trimesh(verts,faces,process=False);m.apply_transform(parent)
                return [m]
            out=[]
            for c in obj.find(tag('components')):
                p=c.get('{'+PROD+'}path',file).lstrip('/')
                out+=walk(p,c.get('objectid'),parent@transform(c.get('transform')))
            return out
        root=getroot('3D/3dmodel.model')
        assert root.get('unit','millimeter')=='millimeter'
        for item in root.find(tag('build')):
            subs=walk('3D/3dmodel.model',item.get('objectid'),transform(item.get('transform')))
            result.append(trimesh.util.concatenate(subs))
    return result

def validate_3mf(path, expected=None, tolerance=.002):
    wrapper=lib3mf.Wrapper();model=wrapper.CreateModel();reader=model.QueryReader('3mf');reader.ReadFromFile(str(path))
    warnings=[str(reader.GetWarning(i)) for i in range(reader.GetWarningCount())]
    meshes=read_3mf_meshes(path)
    rows=[]
    for m in meshes:
        # STL and 3MF may use repeated vertices at seams. Welding does not repair geometry.
        m.merge_vertices()
        rows.append({'watertight':bool(m.is_watertight),'positive_volume':bool(m.volume>0),
                     'volume_mm3':float(m.volume),'bounds_mm':m.bounds.tolist(),'faces':len(m.faces)})
    assert all(r['watertight'] and r['positive_volume'] for r in rows),str(path)
    distances=[]
    if expected is not None:
        assert len(expected)==len(meshes),(str(path),len(expected),len(meshes))
        unused=list(range(len(meshes)))
        for e in expected:
            # Each packaged object corresponds to exactly one source instance.
            i=min(unused,key=lambda i:np.linalg.norm(meshes[i].bounds-e.bounds))
            unused.remove(i);m=meshes[i]
            d=max(float(cKDTree(m.vertices).query(e.vertices)[0].max()),float(cKDTree(e.vertices).query(m.vertices)[0].max()))
            assert d<=tolerance,(str(path),'geometry drift',d)
            assert len(m.faces)==len(e.faces),(str(path),'face count changed')
            assert abs(m.volume-e.volume)<=max(.01,abs(e.volume)*1e-5)
            # Check triangle connectivity independently of vertex order/welding.
            nearest=cKDTree(e.vertices).query(m.vertices)[1]
            actual=np.sort(nearest[m.faces],axis=1);wanted=np.sort(e.faces,axis=1)
            actual=actual[np.lexsort(actual.T[::-1])];wanted=wanted[np.lexsort(wanted.T[::-1])]
            assert np.array_equal(actual,wanted),(str(path),'triangle connectivity changed')
            distances.append(d)
    return {'file':str(path),'sha256':sha256(path),'lib3mf_read_ok':True,'lib3mf_warnings':warnings,
            'instances':len(meshes),'meshes':rows,'max_vertex_deviation_mm':max(distances,default=0)}

def complete_orca_thumbnail_parts(source,target,preview):
    """Orca CLI omits thumbnails that its OPC relationships reference.

    Supply those images without touching geometry, printer settings or G-code.
    Returns the inserted ZIP part names and proves all original parts unchanged.
    """
    added=[]
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        names=set(src.namelist())
        for n in src.namelist():dst.writestr(n,src.read(n))
        rels=ET.fromstring(src.read('_rels/.rels'))
        for rel in rels:
            name=rel.get('Target','').lstrip('/')
            if name.endswith('.png') and name not in names:
                im=Image.open(preview).convert('RGB');im.thumbnail((512,512) if 'small' not in name else (128,128))
                b=io.BytesIO();im.save(b,format='PNG');dst.writestr(name,b.getvalue());added.append(name);names.add(name)
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target) as dst:
        assert all(src.read(n)==dst.read(n) for n in src.namelist()),'Slicer content changed'
    return added

def font(size):
    for p in ['C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if pathlib.Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

COLORS=['#22577a','#38a3a5','#d68128','#ab447d','#658635','#765ca8','#ce6349']
def plate_image(path,plate,mesh_by_id):
    im=Image.new('RGB',(1300,1160),'white');d=ImageDraw.Draw(im);s=3.65;ox=70;oy=1040
    def xy(p):return (ox+(p[0]+110)*s,oy-(p[1]+110)*s)
    d.text((65,25),plate['id']+' — '+plate['group'],font=font(34),fill='#18324a')
    d.text((65,75),'AD5M 220 × 220 mm | PLA | 0.4 mm nozzle | models ≥10 mm from edge',font=font(20),fill='#46586b')
    d.rectangle([xy((-110,110)),xy((110,-110))],outline='#18324a',width=3)
    d.rectangle([xy((-100,100)),xy((100,-100))],outline='#c0c9d0',width=2)
    for t in range(-100,101,20):
        d.line([xy((t,-110)),xy((t,110))],fill='#edf0f2');d.line([xy((-110,t)),xy((110,t))],fill='#edf0f2')
    for idx,item in enumerate(plate['items']):
        m=mesh_by_id[item['id']].copy();m.apply_translation(item['translation_mm']);color=COLORS[idx%len(COLORS)]
        # Top-down triangle projection displays actual part outline, not only its box.
        for tri in m.triangles:
            d.polygon([xy(v) for v in tri],fill=color)
        bb=m.bounds;ctr=bb.mean(axis=0);p=xy(ctr)
        label=item['id']+'-'+str(item['copy']);bbox=d.textbbox((0,0),label,font=font(18));w=bbox[2];h=24
        d.rectangle((p[0]-w/2-4,p[1]-h/2,p[0]+w/2+4,p[1]+h/2),fill='white')
        d.text((p[0]-w/2,p[1]-h/2),label,font=font(18),fill='#182a3a')
    y=145
    counts=collections.Counter(i['id'] for i in plate['items'])
    for pid,n in counts.items():
        d.text((930,y),f'{pid} × {n}',font=font(23),fill='#18324a');y+=34
    d.text((65,1080),'View: above build plate. Outer margin is reserved for adhesion/support clearance.',font=font(18),fill='#46586b')
    d.text((65,1110),'Print fit coupon first; inspect actual sliced support and brim before printing.',font=font(18),fill='#46586b')
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True);im.save(path)

def parse_gcode(path):
    layers=[];layer=None;state={'X':0.,'Y':0.,'Z':0.,'E':0.};relative_e=True;typ='Custom';z=0.;est={};max_width=.5
    for raw in pathlib.Path(path).read_text(encoding='utf-8',errors='replace').splitlines():
        if raw.startswith(';LAYER_CHANGE'):
            layer={'z':None,'segments':[],'types':collections.Counter()};layers.append(layer)
        if raw.startswith(';Z:') and layer is not None:layer['z']=float(raw[3:])
        if raw.startswith(';TYPE:'):typ=raw[6:]
        if raw.startswith(';WIDTH:'):max_width=max(max_width,float(raw[7:]))
        if raw.startswith('; estimated printing time') or raw.startswith('; total estimated time') or raw.startswith('; filament used'):
            k,_,v=raw[2:].partition('=');est[k.strip()]=v.strip()
        line=raw.split(';')[0].strip();tok=line.split()
        if not tok:continue
        if tok[0]=='M83':relative_e=True
        if tok[0]=='M82':relative_e=False
        args={m.group(1):float(m.group(2)) for m in re.finditer(r'([XYZE])\s*([-+]?(?:\d*\.\d+|\d+))',line)}
        if tok[0]=='G92':state.update(args);continue
        if tok[0] not in ('G0','G1'):continue
        old=state.copy();state.update({k:v for k,v in args.items() if k!='E'})
        ext=args.get('E',0.) if relative_e else args.get('E',old['E'])-old['E']
        if 'E' in args:state['E']=state['E']+args['E'] if relative_e else args['E']
        if ext>0 and layer is not None and typ!='Custom' and (state['X']!=old['X'] or state['Y']!=old['Y']):
            seg=(old['X'],old['Y'],state['X'],state['Y'],typ)
            layer['segments'].append(seg);layer['types'][typ]+=1
    points=np.array([[s[0],s[1]] for l in layers for s in l['segments']]+[[s[2],s[3]] for l in layers for s in l['segments']])
    support=[(i,sum(v for k,v in l['types'].items() if 'Support' in k)) for i,l in enumerate(layers)]
    minextr=points.min(axis=0)-max_width/2;maxextr=points.max(axis=0)+max_width/2
    summary={'layers':len(layers),'path_center_bounds_xy_mm':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
             'extrusion_bounds_xy_mm':[minextr.tolist(),maxextr.tolist()],'conservative_max_extrusion_width_mm':max_width,
             'max_z_mm':max(l['z'] or 0 for l in layers),'feature_segments':dict(sum((l['types'] for l in layers),collections.Counter())),
             'estimates':est,'first_layer_extrusion_segments':len(layers[0]['segments'])}
    summary['within_bed']=bool((minextr.min()>=-110) and (maxextr.max()<=110) and summary['max_z_mm']<=220)
    # Support planes may interleave between model layers. Select a middle
    # MODEL layer by Z, and a separate support-interface-sensitive layer.
    model_indices=[i for i,l in enumerate(layers) if any(k not in ('Brim','Custom') and 'Support' not in k for k in l['types'])]
    mid=min(model_indices,key=lambda i:abs((layers[i]['z'] or 0)-summary['max_z_mm']/2))
    interfaces=[(i,sum(v for k,v in l['types'].items() if 'Support interface' in k)) for i,l in enumerate(layers)]
    sensitive=max(interfaces,key=lambda t:t[1])
    if sensitive[1]==0:sensitive=max(support,key=lambda t:t[1])
    picks=sorted(set([0,mid,model_indices[-1],sensitive[0]]))
    return layers,summary,picks

def layer_image(path,plate_id,layers,picks):
    colors={'Outer wall':'#15456b','Inner wall':'#3c8eb9','Sparse infill':'#8abbc4','Internal solid infill':'#749fa7',
            'Bottom surface':'#427a98','Top surface':'#427a98','Brim':'#c08a32','Support':'#bc587d','Support interface':'#7d327f','Bridge':'#d46632'}
    im=Image.new('RGB',(1660,1300),'white');d=ImageDraw.Draw(im)
    d.text((35,20),plate_id+' — actual OrcaSlicer extrusion paths',font=font(29),fill='#18324a')
    d.text((35,62),'Blue: model | ochre: brim | pink/purple: supports | orange: bridge. Travel moves omitted.',font=font(20),fill='#46586b')
    for index,li in enumerate(picks):
        col=index%2;row=index//2;ox=40+col*820;oy=115+row*575;s=2.25
        def xy(x,y):return (ox+60+(x+110)*s,oy+525-(y+110)*s)
        layer=layers[li]
        d.text((ox,oy),f'Layer {li+1}/{len(layers)} — Z={layer["z"]:.2f} mm',font=font(23),fill='#18324a')
        d.rectangle([xy(-110,110),xy(110,-110)],outline='#879ba8',width=2)
        for x0,y0,x1,y1,typ in layer['segments']:
            color=colors.get(typ,'#6f8d92');d.line([xy(x0,y0),xy(x1,y1)],fill=color,width=1)
    d.text((35,1265),'Software toolpath review only. Adhesion, fit, surface quality and support removal require physical checks.',font=font(19),fill='#46586b')
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True);im.save(path)
