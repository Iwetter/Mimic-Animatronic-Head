"""M3-only mechanical retrofit, actual millimetres. Prototype: physical fit required."""
from pathlib import Path
import cadquery as cq
import trimesh
import math, json, csv

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reference_R4' if (ROOT/'reference_R4').exists() else ROOT.parent/'Mimic_Head_R4'
for d in ['STL_REPRINT','STEP','checks','preview','FIT_TEST_FIRST']:
    (ROOT/d).mkdir(parents=True,exist_ok=True)
def box(a,b,c,p): return cq.Workplane('XY').box(a,b,c).val().translate(p)
def cyl(r,h,p,axis=(0,0,1)): return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*axis))
def join(a,*bs):
    for b in bs:a=a.fuse(b)
    return a.clean()
def cut(a,*bs):
    for b in bs:a=a.cut(b)
    return a.clean()
def hx(af,h,p):
    return cq.Workplane('XY').polygon(6,af/math.cos(math.pi/6)).extrude(h).val().rotate((0,0,0),(0,1,0),90).translate(p)
def load(pid):return cq.importers.importStep(str(next((BASE/'STEP/parts').glob(pid+'_*.step')))).val()
parts={}; report=[]
def save(pid,name,s,qty=1,rot=None,fit=False):
    assert s.isValid(),pid+' invalid'
    assert len(s.Solids())==1,(pid,'disconnected',len(s.Solids()))
    dest=ROOT/('FIT_TEST_FIRST' if fit else 'STL_REPRINT')
    cq.exporters.export(s,str(ROOT/'STEP'/f'{pid}_{name}.step'))
    t=s if rot is None else s.rotate((0,0,0),rot[0],rot[1])
    b=t.BoundingBox();t=t.translate((-b.xmin,-b.ymin,-b.zmin))
    path=dest/f'{pid}_{name}_PRINT_{qty}.stl'
    cq.exporters.export(t,str(path),tolerance=.04,angularTolerance=.08)
    m=trimesh.load_mesh(path);m.merge_vertices(digits_vertex=4)
    m.update_faces(m.nondegenerate_faces(height=1e-7));m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
    assert m.is_watertight and m.is_winding_consistent,(pid,'mesh')
    assert len(m.split())==1,(pid,'mesh shells')
    assert max(m.extents[:2])<220,(pid,'bed')
    m.export(path)
    row=dict(id=pid,name=name,quantity=qty,stl=path.relative_to(ROOT).as_posix(),size_mm=m.extents.tolist(),valid_solid=True,watertight=True,volume_mm3=s.Volume())
    report.append(row);parts[pid]=s
    print(pid,name,flush=True)

# Keep P01. Replace two full-width bolts with four side bolts into P03 nuts.
neck=load('P03')
for z in [-38,-48]:
    for x in [-12.2,9.0]:
        neck=cut(neck,hx(5.8,3.2,(x,21,z)),box(3.2,10,6.8,(x+1.6,26,z)))
save('P03','short_bolt_neck',neck,rot=((1,0,0),180))

# M3 clamping bridges straddle OEM servo tabs; no servo-tab drilling.
frame=load('P04')
for y in [-36,-7]:
    for x in [-10,10]:
        frame=join(frame,cyl(4,5.5,(x,y,85)))
        frame=cut(frame,cyl(1.7,12,(x,y,82)))
for y in [4,33]:
    frame=join(frame,box(6,7,36,(-63.75,y,56.25)))
    frame=cut(frame,box(8,8,36,(-70.75,y,56.25)))
    for z in [42.25,70.25]:
        frame=join(frame,cyl(4,6,(-66.75,y,z),(1,0,0)))
        frame=cut(frame,cyl(1.7,16,(-74,y,z),(1,0,0)))
        frame=cut(frame,hx(5.9,5,(-60.75,y,z)))
frame=cut(frame,cyl(17,3,(-70.25,12.5,56.25),(1,0,0)))
# Preserve the existing front-face bore through the widened jaw-mount webs.
frame=cut(frame,cyl(1.7,110,(-63.75,-45,72.5),(0,1,0)))
frame=cut(frame,box(45,24,13.2,(-55,18.5,56.25)))
save('P04','M3_clamp_frame',frame,rot=((1,0,0),90))
bridge=box(28,7,2.5,(0,0,1.25))
for x in [-10,10]:bridge=cut(bridge,cyl(1.7,5,(x,0,-1)))
for y in [-3.2,3.2]:bridge=cut(bridge,box(13.2,1.2,5,(0,y,1.25)))
save('A01','eye_servo_tab_bridge',bridge,qty=2)
jbridge=box(36,7,2.5,(0,0,1.25))
for x in [-14,14]:jbridge=cut(jbridge,cyl(1.7,5,(x,0,-1)))
for y in [-3.2,3.2]:jbridge=cut(jbridge,box(13.2,1.2,5,(0,y,1.25)))
save('A03','jaw_servo_tab_bridge',jbridge,qty=2)

# Eye pins: opposing M3x25 bolts fixed to shelves with two jam nuts each.
# Existing through-bore guides the pins. End recesses and rear openings expose
# the jam nuts for assembly and keep all rotating plastic clear of the nuts.
eye=load('P05')
for z in [90.5,127.0]:
    eye=cut(eye,cyl(4.5,7.5,(0,-27.5,z)),box(9,25,7.5,(0,-15,z+3.75)))
eye=cut(eye,cyl(1.7,9,(0,-6.25,98)))
save('P05','short_pin_eye',eye,qty=2,rot=((1,0,0),-90))
thrust=cut(cyl(6,1,(0,0,0)),cyl(4.5,3,(0,0,-1)))
save('P10','eye_thrust_ring',thrust,qty=4)
tie=load('P06')
for x in [-33.75,0,33.75]:tie=cut(tie,cyl(1.7,8,(x,-6.25,104)))
save('P06','M3_eye_link',tie)
washer=cut(cyl(3.3,1.25,(0,0,0)),cyl(1.7,4,(0,0,-1)))
save('P11','M3_link_washer',washer,qty=3)

# Sandwich original straight horns. M3 screws run BESIDE the horn, never through
# its small holes. Nominal 22 mm length, <=6 mm width, 2 mm thickness.
# A shallow locating channel captures the horn edges; verify fit on the coupon.
horn=load('P07')
horn=join(horn,box(24,28,2.5,(0,-27.5,103.75)))
horn=cut(horn,cyl(4.75,7,(0,-27.5,100)),cyl(1.7,7,(0,-6.25,101)))
for y in [-37.5,-17.5]:horn=cut(horn,cyl(1.7,7,(0,y,100)))
# Locating cheeks project 0.6 mm below the mating plane, not into the boss.
for y in [-31.6,-23.4]:
    for x in [-8,8]:horn=join(horn,box(6,2,0.6,(x,y,102.2)))
save('P07','eye_horn_sandwich',horn,rot=((1,0,0),180))
plate=join(cyl(10,2.25,(0,0,0)),cyl(3.8,2.25,(0,-10,0)),cyl(3.8,2.25,(0,10,0)))
plate=cut(plate,cyl(5.5,5,(0,0,-1)))
for y in [-10,10]:plate=cut(plate,cyl(1.7,5,(0,y,-1)))
save('A02','horn_clamp_plate',plate,qty=2)

jaw=load('P08')
# Horn runs along Y; clamp bolts straddle it along Z.
for z in [46.25,66.25]:jaw=cut(jaw,cyl(1.7,9,(-85,12.5,z),(1,0,0)))
for z in [52.15,60.35]:
    for y in [4.5,20.5]:jaw=join(jaw,box(.6,6,2,(-78.45,y,z)))
save('P08','jaw_horn_sandwich',jaw,rot=((0,1,0),-90))

# First-print coupon includes exact horn clamping faces and bolt spacing.
coupon=cut(box(24,28,2.5,(0,0,1.25)),cyl(4.75,5,(0,0,-1)))
for y in [-10,10]:coupon=cut(coupon,cyl(1.7,5,(0,y,-1)))
for y in [-4.1,4.1]:
    for x in [-8,8]:coupon=join(coupon,box(6,2,.6,(x,y,-.3)))
save('T01','horn_fit_upper',coupon,fit=True,rot=((1,0,0),180))
save('T02','horn_fit_lower',plate,fit=True)
# Separate native-size servo-tab trial, cheap enough to test actual clone first.
tab=box(28,7,5.5,(0,0,2.75))
for x in [-10,10]:tab=cut(tab,cyl(1.7,8,(x,0,-1)))
save('T03','servo_tab_fit_base',tab,fit=True)
save('T04','servo_tab_fit_bridge',bridge,fit=True)

(ROOT/'checks/mesh_validation.json').write_text(json.dumps(report,indent=2))
with (ROOT/'REPRINT_LIST.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Part','Name','Copies','File'])
    for r in report:w.writerow([r['id'],r['name'],r['quantity'],r['stl']])
print('Finished geometry export',flush=True)
