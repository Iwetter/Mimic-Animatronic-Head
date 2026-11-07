from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'PRINT_PLATES_3MF';OUT.mkdir(exist_ok=True)
rows={r['id']:r for r in json.loads((ROOT/'checks/mesh_validation.json').read_text())}
groups=[('00_FIT_TEST_FIRST',['T01','T02','T03','T04']),('01_NECK',['P03']),('02_FRAME',['P04']),('03_EYES',['P05','P10']),('04_EYE_LINK',['P06','P07','P11']),('05_LEFT_JAW',['P08']),('06_CLAMPS',['A01','A02','A03'])]
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',NS)
def e(parent,name,attrib={}):return ET.SubElement(parent,'{'+NS+'}'+name,attrib)
records=[]
for name,ids in groups:
    root=ET.Element('{'+NS+'}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    e(root,'metadata',{'name':'Title'}).text=name+' - Mimic M3 PROTOTYPE'
    res=e(root,'resources');build=e(root,'build');x=y=8.;rh=0.;obj=1;placed=[]
    for pid in ids:
        r=rows[pid];m=trimesh.load_mesh(ROOT/r['stl']);sx,sy,sz=m.extents
        o=e(res,'object',{'id':str(obj),'type':'model','name':pid+' '+r['name']});mesh=e(o,'mesh');vs=e(mesh,'vertices');ts=e(mesh,'triangles')
        for v in m.vertices:e(vs,'vertex',dict(zip(['x','y','z'],[f'{a:.6f}' for a in v])))
        for t in m.faces:e(ts,'triangle',dict(zip(['v1','v2','v3'],map(str,t))))
        for copy in range(r['quantity']):
            if x+sx>212:x=8.;y+=rh+8;rh=0.
            assert y+sy<=212,(name,pid,'bed overflow')
            e(build,'item',{'objectid':str(obj),'transform':f'1 0 0 0 1 0 0 0 1 {x:.6f} {y:.6f} 0'})
            placed.append(dict(part=pid,x=x,y=y,width=float(sx),depth=float(sy)));x+=sx+8;rh=max(rh,sy)
        obj+=1
    path=OUT/(name+'.3mf')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
    with zipfile.ZipFile(path) as z:ET.fromstring(z.read('3D/3dmodel.model'));assert z.testzip() is None
    records.append(dict(plate=name,pieces=placed))
(ROOT/'checks/plate_validation.json').write_text(json.dumps(records,indent=2))
print('Seven geometry-only plates built; all copies fit within 220 mm bed.')
