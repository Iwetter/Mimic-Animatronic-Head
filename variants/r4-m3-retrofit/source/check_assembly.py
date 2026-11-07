from pathlib import Path
import cadquery as cq
import math,json,trimesh
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/'reference_R4' if (ROOT/'reference_R4').exists() else ROOT.parent/'Mimic_Head_R4'
(ROOT/'assembly_meshes').mkdir(exist_ok=True)
def part(pid):
    folder=ROOT/'STEP' if list((ROOT/'STEP').glob(pid+'_*.step')) else BASE/'STEP/parts'
    return cq.importers.importStep(str(next(folder.glob(pid+'_*.step')))).val()
def box(a,b,c,p):return cq.Workplane('XY').box(a,b,c).val().translate(p)
def cyl(r,h,p,axis=(0,0,1)):return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))
def nut(p,axis=(0,0,1)):
    n=cq.Workplane('XY').polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val().cut(cyl(1.5,3,(0,0,-.1)))
    if axis==(1,0,0):n=n.rotate((0,0,0),(0,1,0),90)
    return n.translate(p)
items=[]
def add(name,s,group='fixed',pid=None,reference=False):items.append(dict(name=name,shape=s,group=group,pid=pid or name.split('_')[0],reference=reference))
for pid in ['P01','P03','P04','P06','P07','P08','P09','P12','P13','P18','P19']:
    add(pid,part(pid),{'P06':'link','P07':'eye_horn','P08':'jaw','P09':'fixed','P18':'jaw','P19':'jaw'}.get(pid,'fixed'))
for label,x in [('L',-33.75),('R',33.75)]:
    add('P05_'+label,part('P05').translate((x,0,0)),'eye_'+label)
    add('P15_'+label,part('P15').translate((x,0,0)),'eye_'+label)
    for z in [90,134]:add('P10_'+label+str(z),part('P10').translate((x,-27.5,z)))
    for z in [90,92.4,130.2,132.6]:add('eye_nut_'+label+str(z),nut((x,-27.5,z)),reference=True)
    for z in [85,115]:add('eye_pin_'+label+str(z),cyl(1.5,25,(x,-27.5,z)),reference=True)
    for z in [82,140]:add('eye_pin_head_'+label+str(z),cyl(2.75,3,(x,-27.5,z)),reference=True)
for x in [-33.75,0,33.75]:
    add('P11_'+str(x),part('P11').translate((x,-6.25,105)),'link')
    z=102.5 if x==0 else 100
    add('link_pin_'+str(x),cyl(1.5,20,(x,-6.25,z)),'link',reference=True)
    add('link_head_'+str(x),cyl(2.75,3,(x,-6.25,z-3)),'link',reference=True)
    for nz in [110.3,112.7]:add('link_nut_'+str(x)+str(nz),nut((x,-6.25,nz)),'link',reference=True)
for y in [-36,-7]:
    add('A01_eye_'+str(y),part('A01').translate((0,y,92.5)))
    for x in [-10,10]:
        add('eye_mount_screw_'+str((x,y)),cyl(1.5,16,(x,y,79)),reference=True)
        add('eye_mount_head_'+str((x,y)),cyl(2.75,3,(x,y,95)),reference=True)
        add('eye_mount_nut_'+str((x,y)),nut((x,y,82.6)),reference=True)
for y in [4,33]:
    add('A03_jaw_'+str(y),part('A03').rotate((0,0,0),(0,1,0),90).translate((-71.25,y,56.25)))
    for z in [42.25,70.25]:
        add('jaw_mount_screw_'+str((y,z)),cyl(1.5,16,(-71.25,y,z),(1,0,0)),reference=True)
        add('jaw_mount_head_'+str((y,z)),cyl(2.75,3,(-74.25,y,z),(1,0,0)),reference=True)
        add('jaw_mount_nut_'+str((y,z)),nut((-60.75,y,z),(1,0,0)),reference=True)
add('A02_eye',part('A02').translate((0,-27.5,98.25)),'eye_horn')
add('A02_jaw',part('A02').rotate((0,0,0),(1,1,1),120).translate((-76.75,12.5,56.25)),'jaw')
for y in [-37.5,-17.5]:
    add('horn_eye_screw'+str(y),cyl(1.5,10,(0,y,98.25)),'eye_horn',reference=True)
    add('horn_eye_head'+str(y),cyl(2.75,3,(0,y,95.25)),'eye_horn',reference=True)
    add('horn_eye_nut'+str(y),nut((0,y,105)),'eye_horn',reference=True)
for z in [46.25,66.25]:
    add('horn_jaw_screw'+str(z),cyl(1.5,16,(-83.75,12.5,z),(1,0,0)),'jaw',reference=True)
    add('horn_jaw_head'+str(z),cyl(2.75,3,(-86.75,12.5,z),(1,0,0)),'jaw',reference=True)
    add('horn_jaw_nut'+str(z),nut((-74.5,12.5,z),(1,0,0)),'jaw',reference=True)
for z in [-38,-48]:
    for x in [-12.2,9]:add('neck_nut'+str((x,z)),nut((x,21,z),(1,0,0)),reference=True)
    for x in [-19,7]:add('neck_bolt'+str((x,z)),cyl(1.5,12,(x,21,z),(1,0,0)),reference=True)
    for x in [-22,19]:add('neck_head'+str((x,z)),cyl(2.75,3,(x,21,z),(1,0,0)),reference=True)
for x in [62.7,65.1]:add('jaw_pivot_nut'+str(x),nut((x,12.5,56.25),(1,0,0)),reference=True)
add('jaw_pivot_screw',cyl(1.5,25,(58.75,12.5,56.25),(1,0,0)),reference=True)
add('jaw_pivot_head',cyl(2.75,3,(83.75,12.5,56.25),(1,0,0)),reference=True)
def servo():return box(12.2,22.8,22.3,(0,6,-17.35)).fuse(box(12.2,32.5,2,(0,6,-9))).fuse(cyl(5,6.2,(0,0,-6.2))).clean()
add('servo_eye',servo().translate((0,-27.5,100.5)),reference=True)
add('servo_jaw',servo().rotate((0,0,0),(0,1,0),-90).translate((-76.75,12.5,56.25)),reference=True)
hn=box(22,6,2,(0,0,1)).fuse(cyl(4.5,2,(0,0,0))).clean()
add('OEM_eye_horn',hn.translate((0,-27.5,100.5)),'eye_horn',reference=True)
add('OEM_jaw_horn',hn.rotate((0,0,0),(1,1,1),120).translate((-78.75,12.5,56.25)),'jaw',reference=True)

def bbox_overlap(a,b):
    a=a.BoundingBox();b=b.BoundingBox()
    return all(min(getattr(a,k+'max'),getattr(b,k+'max'))-max(getattr(a,k+'min'),getattr(b,k+'min'))>1e-5 for k in 'xyz')
def pose(i,eye_deg,jaw_deg):
    s=i['shape'];g=i['group']
    if g=='jaw':return s.rotate((0,12.5,56.25),(1,12.5,56.25),jaw_deg)
    if g in ['eye_L','eye_R','eye_horn']:
        x={'eye_L':-33.75,'eye_R':33.75,'eye_horn':0}[g]
        return s.rotate((x,-27.5,0),(x,-27.5,1),eye_deg)
    if g=='link':
        r=math.radians(eye_deg);return s.translate((-21.25*math.sin(r),21.25*(math.cos(r)-1),0))
    return s
findings=[]
for ed,jd in [(0,0)]+[(e,j) for j in [0,20] for e in [-18,-12,-6,0,6,12,18] if (e,j)!=(0,0)]+[(0,j) for j in [5,10,15]]:
    shapes=[pose(i,ed,jd) for i in items]
    for j,a in enumerate(items):
        for k in range(j):
            b=items[k]
            if a['reference'] and b['reference'] and not any(q['name'].startswith(('servo_','OEM_')) for q in [a,b]):continue
            if (ed or jd) and a['group']==b['group']:continue
            if not bbox_overlap(shapes[j],shapes[k]):continue
            vol=shapes[j].intersect(shapes[k]).Volume()
            if vol>.05:findings.append(dict(eye_deg=ed,jaw_deg=jd,a=a['name'],b=b['name'],overlap_mm3=round(vol,4)))
    print('pose',ed,jd,'findings',len(findings),flush=True)
(ROOT/'checks/assembly_clearance.json').write_text(json.dumps(dict(prototype=True,threshold_mm3=.05,findings=findings,limitations=['Nominal servo and straight horn envelope; actual clones not measured','Discrete poses, not continuous sweep','Cosmetic fixed fastening hardware omitted; original R4 geometry retained','No physical strength or friction tests']),indent=2))
scene=[]
for i in items:
    file='assembly_meshes/'+i['name']+'.stl'
    cq.exporters.export(i['shape'],str(ROOT/file),tolerance=.07,angularTolerance=.12)
    scene.append(dict(name=i['name'],pid='REFERENCE' if i['reference'] else i['pid'],group=i['group'],file=file,color=[.18,.20,.23] if i['reference'] else ([.2,.65,.75] if list((ROOT/'STEP').glob(i['pid']+'_*.step')) else [.55,.57,.60])))
(ROOT/'source/assembly_scene.json').write_text(json.dumps(scene,indent=2))
print('Finished; findings:',len(findings),flush=True)
