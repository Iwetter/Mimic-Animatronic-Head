#!/usr/bin/env python3
"""Mimic R5a E1: STEP-first engineering build. Units mm; no mesh export here.

Run: python cad_source/build_release.py [output-release-directory]
Reference neck/socket are exact shapes recovered from the supplied named assembly,
not reconstructed claims about an unavailable R4 release. All servo/horn dimensions
are nominal fit assumptions. See parameters.json and parts.json physical gates.
"""
from pathlib import Path
import sys,json,math,csv
import cadquery as cq
import base_geometry as b
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
for d in ('step/parts','step/assembly','bom','validation'): (ROOT/d).mkdir(parents=True,exist_ok=True)
V=cq.Vector; box,cyl,U,D=b.box,b.cyl,b.U,b.D
EX,EY,EZ=33.75,-36.25,112.5
JY,JZ=12.5,56.25
REV='R5a-E1'
parts={k:dict(v) for k,v in b.parts.items()}
hardware=[]; joints=[]; instances=[]
def put(pid,name,s,qty=1,mat='frame_dark',note='',rot=None):
    s=s.clean()
    if not s.isValid() or len(s.Solids())!=1: raise ValueError((pid,s.isValid(),len(s.Solids())))
    parts[pid]=dict(id=pid,name=name,shape=s.Solids()[0],qty=qty,mat=mat,installation=note,rotation=rot)
    return s.Solids()[0]
def sh(pid): return parts[pid]['shape']
def edit(pid,s,note):
    p=parts[pid];return put(pid,p['name'],s,p['qty'],p['mat'],note,p.get('rotation'))
def hole(s,p,direction,length=200,diam=3.4):
    a=V(*p);v=V(*direction).normalized()*length/2
    return D(s,cyl(diam/2,tuple(a-v),tuple(a+v)))
def bolt(jid,description,qty,location,axis,size,grip,note):
    hardware.append(dict(id=jid,description=description,qty=qty,location_mm=location,axis=axis,size=size,
        nominal_grip_mm=grip,installation=note,physical_fit='UNVERIFIED'))
def joint(jid,pids,axis,centers,fastener,notes):
    joints.append(dict(id=jid,parts=pids,axis=axis,centers_mm=centers,fastener=fastener,notes=notes))
def arc_sector(x0,t,cy,cz,r,a0,a1):
    pts=[(cy,cz)]+[(cy+r*math.cos(math.radians(a)),cz+r*math.sin(math.radians(a))) for a in [a0+(a1-a0)*i/60 for i in range(61)]]
    return b.prism_yz(pts,x0,t)
def arc_slot(s,x0,x1,cy,cz,r,a0,a1,rad):
    # Polygonal annular slot at <=0.5 degree with round end caps; max radial
    # chord deviation below0.0002mm at these radii.
    n=math.ceil((a1-a0)/.5); aa=[math.radians(a0+(a1-a0)*i/n) for i in range(n+1)]
    pts=[(cy+(r+rad)*math.cos(a),cz+(r+rad)*math.sin(a)) for a in aa]+[(cy+(r-rad)*math.cos(a),cz+(r-rad)*math.sin(a)) for a in reversed(aa)]
    cutter=b.prism_yz(pts,x0,x1-x0)
    for a in (aa[0],aa[-1]):cutter=U(cutter,cyl(rad,(x0,cy+r*math.cos(a),cz+r*math.sin(a)),(x1,cy+r*math.cos(a),cz+r*math.sin(a))))
    return D(s,cutter)
def capsule(p0,p1,r,t,axis):
    a,c=V(*p0),V(*p1);z=V(*axis);u=(c-a).normalized();w=z.cross(u);mid=(a+c)*.5
    web=box((0,0,0),((c-a).Length,2*r,t)).moved(cq.Location(cq.Plane(mid,u,z)))
    return U(web,cyl(r,tuple(a-z*t/2),tuple(a+z*t/2)),cyl(r,tuple(c-z*t/2),tuple(c+z*t/2)))

# Structural fastening. Exterior surfaces retained except necessary fastener bores.
base=sh('P20')
for sx,pid in ((-1,'P21'),(1,'P22')):
    wall=sh(pid)
    foot=box((sx*63,37,8),(10,16,4))
    wall=U(wall,foot,box((sx*67,35,14),(2,10,12)))
    for y in (33,41):
        p=(sx*63,y,8);wall=hole(wall,p,(0,0,1),20);base=hole(base,p,(0,0,1),20)
    edit(pid,wall,'Two inward feet bolt to P20 with M3x16, washers and accessible nuts below; assemble before neck.')
    bolt('H_BASE_'+pid,'M3x16 socket screw + 2 flat washers + M3 hex nut',2,[[sx*63,y,0] for y in (33,41)],[0,0,1],'M3x16',10,'Screw from above; hold nut below base before P03 installation.')
edit('P20',base,'Mount frame feet and P44 first, then neck flange with four M3x20 through bolts.')
for sx,lo,up in ((-1,'P21','P23'),(1,'P22','P24')):
    for y,z in ((5,122),(68,124)):
        edit(lo,hole(sh(lo),(sx*72,y,z),(1,0,0),30),'Upper/lower plate joint: two M3x18 through bolts each side.')
        edit(up,hole(sh(up),(sx*75,y,z),(1,0,0),30),'Two M3x18 join lower wall; three M3x20 secure cranial arches; face anchor pad at front.')
    bolt('H_PLATE_'+up,'M3x18 socket screw + 2 washers + M3 hex nut',2,[[sx*79,y,z] for y,z in ((5,122),(68,124))],[sx,0,0],'M3x18',11,'Heads outside, nuts accessible inside before installing mechanism deck.')

# Cranial arches gain hidden fastening end tabs. Crest bolts vertically through half laps.
for pid,y in (('P25',-45),('P26',2),('P27',52)):
    a=sh(pid)
    for sx,up in ((-1,'P23'),(1,'P24')):
        a=U(a,box((sx*69.5,y,150.8),(9,8,7)))
        a=hole(a,(sx*70,y,151.5),(1,0,0),30)
        plate=U(sh(up),cyl(5,(sx*74,y,151.5),(sx*79,y,151.5)))
        edit(up,hole(plate,(sx*75,y,151.5),(1,0,0),30),'Arch screw bosses and front face anchor; preserve frame silhouette.')
    a=hole(a,(0,y,210),(0,0,1),100,2.2)
    edit(pid,a,'Two M3x20 at end tabs; one M2x16 through crest lap, washer and plain nut.')
    edit('P28',hole(sh('P28'),(0,y,210),(0,0,1),100,2.2),'Three M2x16 vertical through bolts retain the existing half-lap crest joints.')
    bolt('H_ARCH_'+pid,'M3x20 socket screw + 2 washers + M3 nut',2,[[-79,y,151.5],[79,y,151.5]],[1,0,0],'M3x20',14,'Outside heads, inward nuts; fit arch before crest.')
bolt('H_CREST','M2x16 socket screw + 2 washers + M2 nut',3,[[0,y,210] for y in (-45,2,52)],[0,0,1],'M2x16',10,'Trim screw only if measured joint differs; confirm at least 1.5 threads beyond nut.')

# Face mask anchors and zygoma/maxilla mounting feet; all open to tool access.
for sx,up,zyg,wall in ((-1,'P23','P30','P21'),(1,'P24','P31','P22')):
    pad=box((sx*74.5,-53.5,125.5),(8,8,8))
    edit(up,hole(U(sh(up),pad),(sx*74.5,-55,125.5),(0,1,0),20),'Face pad accepts M3x16 through bolt with nut accessible behind.')
    bolt('H_FACE_'+up,'M3x16 socket screw + 2 washers + M3 nut',1,[[sx*74.5,-62,125.5]],[0,1,0],'M3x16',12.5,'Nut at rear of pad; mount mask after eye cassette.')
    # A raised shoe beneath the zygoma root attaches across its original butt joint.
    zfoot=box((sx*65,-15,82.5),(6,10,7))
    edgetab=box((sx*66,-15,80),(4,10,4))
    edit(zyg,hole(U(sh(zyg),zfoot),(sx*65,-15,87),(0,0,1),24),'One M3x18 vertical root bolt to eye deck; front mask M2x10 retained screw.')
    # Forward face junction uses a Y screw through the existing overlapping edge.
    edit(zyg,hole(sh(zyg),(sx*59,-57,90),(0,1,0),20,2.2),'M3 root bolt and M2 face bolt. No adhesive structural joint.')
    edit('P29',hole(sh('P29'),(sx*59,-59,90),(0,1,0),20,2.2),'Two M3 top anchors, two M2 zygoma anchors; two M2 maxilla anchors below nasal window.')
    bolt('H_ZYG_'+zyg,'M2x10 screw + washers + M2 nut',1,[[sx*59,-62,90]],[0,1,0],'M2x10',6.5,'Front screw, nut behind zygoma root; inspect actual mating overlap before tightening.')

# Maxilla: side attachment pads and holes through lower walls, plus face nasal bolts.
for sx,wall in ((-1,'P21'),(1,'P22')):
    for pid in ('P32',wall): edit(pid,hole(sh(pid),(sx*68,-16,60),(1,0,0),28,2.2),'M2x16 side bolts retain maxilla struts; nut accessible toward centre.')
    bolt('H_MAX_'+wall,'M2x16 screw + 2 washers + M2 nut',1,[[sx*74,-16,60]],[sx,0,0],'M2x16',12,'Fit before jaw; align and clamp side strut to lower wall.')
edit('P32',U(sh('P32'),box((0,-55.5,65),(28,4,10))),'Hidden nasal-floor back pad supports two transverse M2 fasteners.')
for x in (-8,8):
    for pid in ('P29','P32'): edit(pid,hole(sh(pid),(x,-59,67),(0,1,0),20,2.2),'Two M2x16 front-to-rear nasal-floor bolts with rear nuts; dry fit before teeth.')
bolt('H_MAX_FACE','M2x16 screw + washers + M2 nut',2,[[-8,-62,67],[8,-62,67]],[0,1,0],'M2x16',8.5,'Straight front access; nuts behind new maxilla pad atY-53.5.')

# Teeth are removable via two M1.6 screws through rear carrier ends, no glue requirement.
for teeth,carrier,z,xs,yy in [('P42','P32',56.6,(-33,33),-40.5),('P43','P33',35.5,(-32,32),-41)]:
    for x in xs:
        for pid in (teeth,carrier): edit(pid,hole(sh(pid),(x,yy,z),(0,0,1),18,1.8),'Rear carrier M1.6 through bolts; install after free-motion testing.')
    bolt('H_TEETH_'+teeth,'M1.6x16 screw + 2 washers + M1.6 nut',2,[[x,yy,z] for x in xs],[0,0,1],'M1.6x16',10,'Rear carrier only; upper grip8mm, lower10mm. Trim excess only after confirming nut engagement and travel.')

# Eye deck: remove old unsupported posts, retain fixed lid supports and broad plate.
ed=box((0,-29,72),(136,46,4))
ed=D(ed,box((0,-30,72),(14,30,8)))
for sx in (-1,1):
    for side in (-1,1):
        x0=sx*EX+(19.8 if side>0 else -22.8)
        pr=box((x0+1.5,EY,95.25),(3,8,43.5))
        pr=hole(pr,(x0+1.5,EY,EZ),(1,0,0),6,2.2)
        ed=U(ed,pr)
for sx in (-1,1):
    # Pitch supports outside both lid assemblies. M3 axes at eye centres.
    ed=U(ed,box((sx*66,EY,93.5),(4,10,39)),cyl(5,(sx*64,EY,EZ),(sx*68,EY,EZ)))
    ed=hole(ed,(sx*66,EY,EZ),(1,0,0),12,3.2)
    # Side screw pads to fixed walls at rear deck edge.
    ed=U(ed,box((sx*65,-12,75),(6,10,8)))
    for pid in ('P21' if sx<0 else 'P22',): edit(pid,hole(sh(pid),(sx*69,-12,76),(1,0,0),22),'Eye cassette support M3x18 cross screw at Y-12 Z76.')
    ed=hole(ed,(sx*65,-12,76),(1,0,0),22)
    ed=hole(ed,(sx*65,-15,82),(0,0,1),24)
    # Outer prong has a positive pin-and-slot eyelid stop.
    x0=sx*EX+(19.8 if sx>0 else -22.8)
    ed=U(ed,arc_sector(x0,3,EY,EZ,12,-30,80))
    ed=arc_slot(ed,x0-1,x0+4,EY,EZ,8,-1.2,51.2,1.25)
    ed=hole(ed,(x0+1.5,EY,EZ),(1,0,0),6,2.2)
    lp='P39' if sx<0 else 'P40'
    edit(lp,hole(sh(lp),(sx*(EX+18.55),EY+8,EZ),(1,0,0),8,2.2),'Original visible lid shell, retained M2 pivots, M2 stop pin at R8, flat pushrod at outer lever.')
    bolt('H_EYE_DECK_'+str(sx),'M3x18 screw + 2 washers + M3 nut',1,[[sx*74,-12,76]],[sx,0,0],'M3x18',12,'Bolt wall to fixed eye deck; inside nut accessible before globes.')
    bolt('H_ZYG_ROOT_'+str(sx),'M3x25 screw + 2 washers + M3 nut',1,[[sx*65,-15,90]],[0,0,1],'M3x25',15,'One root bolt joins P30/P31 to eye deck shoe. Nested shoe is relieved from fixed support; verify nut engagement at underside.')
    bolt('H_PITCH_PIVOT_'+str(sx),'M3x16 screw + 3 washers + M3 nyloc nut',1,[[sx*68,EY,EZ]],[sx,0,0],'M3x16',8,'Stationary screw, moving carrier running bore. Set nyloc for 0.2–0.4 axial play, not clamped.')
    bolt('H_LID_STOP_'+str(sx),'M2x8 screw + 2 washers + M2 nyloc nut',1,[[sx*(EX+18.55),EY+8,EZ]],[sx,0,0],'M2x8',5,'Pin traverses fixed curved slot. Nut outside; retain loose enough to slide.')
# Common-pitch stop is on the left support at R14, separated from eyelid R8 pin.
ed=U(ed,arc_sector(-68,4,EY,EZ,18,-27,27))
ed=arc_slot(ed,-69,-63,EY,EZ,14,-12.98,12.98,1.25)
for x in(-EX+21.3,EX-21.3):
    ed=D(ed,box((x,-30.875,89),(5,9.25,18)))
for zyg in ('P30','P31'):
    edit(zyg,D(sh(zyg),ed),'Hidden root relieved around fixed eye-deck pitch supports; root shoe retained by M3x25. Approved visible zygoma retained.')
edit('P36',ed,'Fixed eye/lid deck lowered internally10mm for yaw-link/nut travel; common-pitch outboard pivots, lid/pitch stop slots and sidewall bolts.')

# P45: common pitch carrier. Rotation axis is X through both eye centres.
pc=box((0,-10,95),(127,6,5))
for sx in (-1,1):
    xe=sx*EX
    pc=U(pc,box((xe,-23,95),(9,26,5)),cyl(5,(xe,EY,93),(xe,EY,105)))
    pc=hole(pc,(xe,EY,99),(0,0,1),20,3.2)
    arm=b.prism_yz([(-13,92.5),(-6,92.5),(-31,116.5),(-40,116.5),(-40,108.5)],sx*62-1.5,3)
    pc=U(pc,arm,box((sx*62,-10,95),(6,6,5)))
    pc=hole(pc,(sx*62,EY,EZ),(1,0,0),8,3.2)
    # Split clamp crack must not continue into bearing housing; bearings are drilled/reamed.
    bolt('H_YAW_SHAFT_'+str(sx),'Ground steel shaft Ø3 x 33 mm; collars separately H_YAW_COLLARS',1,[[xe,EY,84]],[0,0,1],'Ø3x33',0,'Deburr cut shaft84..117; 3.2 running bore in carrier, upper collar105.2..108.2; shaft clamped independently to globe and crank.')
pc=U(pc,box((0,-31,97),(21,42,4)))
pc=D(pc,box((0,-30.25,99),(13.2,24,12)))
for y in (EY-8,EY+20): pc=hole(pc,(0,y,98),(0,0,1),12,2.4)
pc=U(pc,box((0,-12.25,105),(8,6,20)))
pc=hole(pc,(0,-12.25,112.5),(1,0,0),12,2.2)
pc=D(pc,box((0,-14.75,100.5),(13,2.5,3)))
pc=U(pc,box((-62,-25,112.5),(3,14,7)))
pc=hole(pc,(-62,EY+14,EZ),(1,0,0),8,2.2)
# Left yaw crank pin is captured in a carrier-local XY sector. R12 crank,
# slot endpoints +/-21.8deg +1.194deg radial clearance => stops about +/-23deg.
aa=[math.radians(-35+i*70/80) for i in range(81)]
sector=b.prism_xy([(-EX,EY)]+[(-EX-16*math.sin(a),EY+16*math.cos(a)) for a in aa],93,4.5)
pc=U(pc,sector)
aa=[math.radians(-21.8+i*43.6/100) for i in range(101)]
poly=[(-EX-13.25*math.sin(a),EY+13.25*math.cos(a)) for a in aa]+[(-EX-10.75*math.sin(a),EY+10.75*math.cos(a)) for a in reversed(aa)]
slot=b.prism_xy(poly,92,7)
for a in (aa[0],aa[-1]):slot=U(slot,cyl(1.25,(-EX-12*math.sin(a),EY+12*math.cos(a),92),(-EX-12*math.sin(a),EY+12*math.cos(a),99)))
pc=D(pc,slot)
for sx in(-1,1):
    pc=hole(pc,(sx*EX,EY,99),(0,0,1),30,3.2)
    pc=D(pc,cyl(5.6,(sx*EX,EY,88),(sx*EX,EY,93.4)))
put('P45','common_pitch_carrier',pc,note='Rigid pitch carrier fixes both yaw-axis bearings. CH0 servo moves with carrier. Two outboard M3 pivots on X axis; two M2x10 servo-tab screws.',rot=[0,0,0])
bolt('H_PITCH_STOP','M2x12 screw + 2 washers + M2 nyloc nut',1,[[-62,EY+14,EZ]],[1,0,0],'M2x12',7.5,'Left carrier pin slides in R14 fixed slot. Set washer/nyloc gap; approximately±14deg physical stop.')
bolt('H_SERVO_YAW','M2x10 screw + washers + M2 nut',2,[[0,y,99] for y in (EY-8,EY+20)],[0,0,1],'M2x10',6,'Measure actual flange pitch before purchase/print; nominal 28mm. Bottom-access nuts.')

# P34 retains the sphere/iris silhouette; replaces toy ball and crossed pins with shaft clamp.
globe=sh('P34')
globe=D(globe,box((-EX,EY+24,EZ),(20,18,16)))
cone=cq.Solid.makeCone(0,25*math.tan(math.radians(49)),25,V(-EX,EY,EZ),V(0,0,-1))
globe=D(globe,cone)
globe=U(globe,box((-EX,EY,EZ),(29,6,5)),box((-EX,EY,EZ+1),(10,10,8)))
globe=hole(globe,(-EX,EY,EZ),(0,0,1),50,3.2)
# Captive M2 nut for radial grub screw; rear service window provides access.
globe=hole(globe,(-EX,EY+5,EZ),(0,1,0),16,1.8)
globe=D(globe,box((-EX,EY+3.5,EZ),(4.2,2.1,4.2)),box((-EX,EY+15,EZ+4),(12,10,19)))
edit('P34',globe,'Retained front sphere/iris; hidden rear access, 49-degree lower opening and internal shaft hub. M2x8 grub/setscrew in captive nut secures 3mm shaft; verify clamp strength physically.')
bolt('H_GLOBE_CLAMP','M2x8 set screw + M2 plain nut',2,[[-EX,EY+5,EZ],[EX,EY+5,EZ]],[0,1,0],'M2x8',5,'Trap nut in radial pocket before inserting axle; flats filed on steel shaft improve repeatable grip.')

# Equal R12 yaw cranks and two independent half-length tie links: planar 1 DOF.
crank=capsule((-EX,EY,90.5),(-EX,EY+12,90.5),3.5,3,(0,0,1))
crank=U(crank,cyl(5,(-EX,EY,89),(-EX,EY,92.8)))
crank=hole(crank,(-EX,EY,91),(0,0,1),10,3.2)
crank=hole(crank,(-EX,EY+12,90.5),(0,0,1),10,2.2)
crank=hole(crank,(-EX,EY+4,91.5),(0,1,0),12,1.8)
crank=D(crank,box((-EX,EY+3,91.5),(4.2,2.1,4.2)))
put('P37','yaw_crank',crank,2,'frame_dark','R12 crank clamped to 3mm shaft by M2x8 captive-nut set screw. Do not use printed spline.',rot=[0,0,0])
tie=capsule((-EX,EY+12,87),(0,EY+12,87),3,2,(0,0,1))
for x in (-EX,0):tie=hole(tie,(x,EY+12,87),(0,0,1),8,2.2)
put('P38','yaw_tie_half',tie,2,'frame_steel','Two independent links, 33.75mm centres; second link shifted +33.75mm X and -2.5mm Z. M2 bolts, washers, metal spacers; retain pivot freedom.',rot=[0,0,0])
bolt('H_YAW_CRANK_CLAMP','M2x8 set screw + M2 plain nut',2,[[-EX,EY+4,91.5],[EX,EY+4,91.5]],[0,1,0],'M2x8',5,'File local shaft flat and align both R12 crank holes rearward before tightening.')
bolt('H_YAW_LINK_LEFT','M2x20 screw + 2 washers + M2 nyloc nut + 1mm spacer',1,[[-EX,EY+12,90.5]],[0,0,1],'M2x20',12,'Left pin extends upward through carrier R12 curved stop slot. Head above carrier, nut below link; maintain sliding clearance.')
bolt('H_YAW_LINK_RIGHT','M2x16 screw + 2 washers + M2 nyloc nut + 3.5mm spacer',1,[[EX,EY+12,90.5]],[0,0,1],'M2x16',8,'Right link is lower in stack. SpacerØ2.2ID; leave free to rotate.')
bolt('H_YAW_LINK_CENTRE','M2x16 screw + 3 washers + M2 nyloc nut + 1mm spacer',1,[[0,EY+12,90.5]],[0,0,1],'M2x16',8,'Two links stacked on one retained OEM horn R12 pin. Validate horn has an R12 hole; adjust parameter consistently if measured otherwise.')

# Rebuild fixed mechanism deck: remove obsolete yaw stage and retain pitch/lid drives.
deck=box((0,-.5,156),(148,41,4))
deck=D(deck,box((0,-12.25,156),(20,16,10)))
pitchS=(0,1.75,176.5)
pbx=-12.5
pbr=box((pbx,7.75,172.25),(3,34,28.5))
pbr=D(pbr,box((pbx,7.75,176.5),(5,23.8,13.2)))
for y in (-6.25,21.75):pbr=hole(pbr,(pbx,y,176.5),(1,0,0),8,2.4)
deck=U(deck,pbr)
lidS=(55.5,b.P['lid_S'][1],b.P['lid_S'][2])
for sx in (-1,1):
    xb=sx*48; cy=lidS[1]+6;zt=lidS[2]+6.6
    br=box((xb,cy,(158+zt)/2),(3,33.2,zt-158))
    br=D(br,box((xb,cy,lidS[2]),(5,23.8,13.2)))
    for y in (lidS[1]-8,lidS[1]+20):br=hole(br,(xb,y,lidS[2]),(1,0,0),8,2.4)
    deck=U(deck,br)
    for y in (-15,15):
        deck=U(deck,box((sx*70,y,153),(8,8,6)))
        deck=hole(deck,(sx*71,y,153),(1,0,0),20)
        up='P23' if sx<0 else 'P24'
        plate=U(sh(up),cyl(5,(sx*74,y,153),(sx*79,y,153)),box((sx*76.5,y,163),(5,6,25)))
        edit(up,hole(plate,(sx*75,y,153),(1,0,0),20),'Mechanism deck side bolts; solid nut bosses added only at attachment interfaces.')
    bolt('H_DECK_'+str(sx),'M3x20 screw + 2 washers + M3 nut',2,[[sx*79,y,153] for y in (-15,15)],[sx,0,0],'M3x20',13,'Nuts inside, access before lid/pitch servo installation.')
    bolt('H_SERVO_LID_'+str(sx),'M2x10 screw + 2 washers + M2 nut',2,[[xb,y,lidS[2]] for y in (lidS[1]-8,lidS[1]+20)],[sx,0,0],'M2x10',5,'Two nominal28mm pitch flange screws; retain OEM horn and centre screw.')
deck=D(deck,sh('P26'))
# Cable-tie slots and a rearward power/voice harness path, away from eye links.
for x in (-28,28):
    for y in (9,15): deck=D(deck,box((x,y,156),(8,2.5,8)))
edit('P41',deck,'Fixed pitch/lid servo deck. Four M3 side bolts; M2 tab screws; paired cable-tie slots. Route cables rearward, service loop for moving yaw servo.')
bolt('H_SERVO_PITCH','M2x10 screw + 2 washers + M2 nut',2,[[pbx,y,176.5] for y in (-6.25,21.75)],[1,0,0],'M2x10',5,'Nominal pitch servo tabs. Inspect rear hole support on actual servo.')

# Rigid planar pitch pushrod: lower x=+6 gives side access to the carrier tab.
pr=capsule((6,-12.25,112.5),(6,-12.25,176.5),3,2.5,(1,0,0))
for z in (112.5,176.5):pr=hole(pr,(6,-12.25,z),(1,0,0),8,2.2)
put('P46','eye_pitch_pushrod',pr,note='64mm centre distance. Lower pivot M2 to common carrier tab; upper pivot M2 to OEM R14 pitch horn. Spacers align pin axes; no spherical rods.',rot=[0,90,0])
bolt('H_PITCH_ROD','M2x16 screw + 2 washers + M2 nyloc nut + metal spacer',2,[[6,-12.25,z] for z in (112.5,176.5)],[1,0,0],'M2x16',9,'Rod plane X6. Lower washer at carrier edgeX4; upper metal spacer from hornX0 to rodX4.75. Verify pin support and axial clearance.')

# Flat eyelid rods outside the original visible shell.
lrod=capsule((-58.5,-26.45,108.4),(-58.5,-26.45,186),3,2,(1,0,0))
for z in (108.4,186):lrod=hole(lrod,(-58.5,-26.45,z),(1,0,0),8,2.2)
put('P49','lid_pushrod',lrod,2,'frame_dark','77.6mm centres, M2 pinned at both ends. Outer rod plane X±58.5. Metal spacer aligns original lid lever to rod. No printed ball joints.',rot=[0,90,0])
bolt('H_LID_PIVOTS','M2x10 screw + 2 washers + M2 nyloc nut',4,[[sx*EX+side*20,EY,EZ] for sx in(-1,1) for side in(-1,1)],[1,0,0],'M2x10',5,'Four independent retained pivots. Washers in 0.5mm lid/prong gaps. Set axial play, no clamp on moving lid.')
bolt('H_LID_RODS','M2x14 screw + 2 washers + M2 nyloc nut + metal spacer',4,[[sx*58.5,-26.45,z] for sx in(-1,1) for z in(108.4,186)],[1,0,0],'M2x14',8,'Lower spacer4.45mm; upper spacer1mm nominal. Measure actual horns before selecting spacers.')

# Jaw: retained outboard support, corrected double arm horn interface and positive stops.
jaw=sh('P33');right=sh('P22')
lug=cyl(4,(59.5,JY+14,JZ),(64.5,JY+14,JZ))
jaw=U(jaw,lug,box((62,JY+10,JZ),(5,9,7)))
jaw=hole(jaw,(62,JY+14,JZ),(1,0,0),10,3.2)
right=U(right,arc_sector(65.2,8.8,JY,JZ,20,-20,35))
right=arc_slot(right,64.8,75,JY,JZ,14,.828,15.8,1.8)
edit('P22',right,'Right wall carries jaw stop sector; M3 stop pin follows slot. Mechanical stop approximately -0.4 to17 degrees, soft0..14. Closing stop precedes tooth/molar contact.')
# M3 threaded insert in driven left ramus; flush inner face avoids horn centre conflict.
jaw=D(jaw,cyl(2.3,(-63.5,JY,JZ),(-59.4,JY,JZ)))
edit('P33',jaw,'Driven-left ramus takes M3x4 heat-set insert and M3x18 outboard pivot screw. Right M3x25 retained pivot and M3x25 stop pin. OEM double-arm horn at +/-8mm, two M2 screws.')
for pid in ('P21','P22'):edit(pid,hole(sh(pid),(0,JY,JZ),(1,0,0),180,4.2),'Jaw pivot bearing Ø4.2 accepts smooth Ø4 metal sleeve; M3 screw never runs on FDM bearing.')
bolt('H_JAW_LEFT_PIVOT','M3x18 socket screw + one0.5mm washer + M3x4 heat-set insert',1,[[-77.9,JY,JZ]],[1,0,0],'M3x18',13.4,'Clamp on Ø4OD/Ø3.2ID sleeve12.9±0.05 long between jaw outer faceX-64.5 and washer inner faceX-77.4. Sleeve rotates inØ4.2 wall bore;0.4mm outside axial gap. InsertOD4.6x4 in pocketØ4.6x4.1; actual insert coupon required. Screw tipX-59.9 gives3.6mm engagement without horn intrusion.')
bolt('H_JAW_RIGHT_PIVOT','M3x25 socket screw + two0.5mm washers + M3 nyloc nut',1,[[77.9,JY,JZ]],[-1,0,0],'M3x25',18.4,'Same12.9mm sleeve between jaw outer faceX64.5 and washer inner faceX77.4. Nut/second washer at jaw inner faceX59.5; sleeve and screw rotate with jaw, not a loose pivot thread.')
bolt('H_JAW_SLEEVE','Brass/stainless tube Ø4OD/Ø3.2ID, cut12.9±0.05mm, square deburred ends',2,[[sx*70.95,JY,JZ] for sx in(-1,1)],[1,0,0],'Ø4/3.2x12.9',0,'Clamp with jaw pivot screws. Confirm12.5mm wall-to-ramus stack and0.4mm free play before fully tightening.')
bolt('H_JAW_STOP','M3x25 screw + 2 washers + M3 nyloc nut',1,[[62,JY+14,JZ]],[1,0,0],'M3x25',14.5,'Pin slides in curved wall slot; do not clamp moving ramus to wall.')
bolt('H_JAW_HORN','M2x10 screw + 2 washers + M2 nut',2,[[-60,JY+d,JZ] for d in (-8,8)],[1,0,0],'M2x10',7,'OEM double-arm horn requires holes at ±8mm and centre screw. Actual horn pattern must be measured; no printed spline.')
cr=sh('P44')
cr=U(cr,box((-47,34,8), (20,12,4)))
for x in (-55,-41):
    cr=hole(cr,(x,34,8),(0,0,1),14);edit('P20',hole(sh('P20'),(x,34,4),(0,0,1),14),'Jaw-cradle and frame-foot through holes; neck pattern preserved.')
for y in (4.5,32.5):cr=hole(cr,(-51.25,y,JZ),(1,0,0),8,2.4)
edit('P44',cr,'M3x16 base feet; M2x10 servo tabs at nominal28mm centres. Centre horn before attaching jaw.')
bolt('H_JAW_CRADLE_BASE','M3x16 screw + 2 washers + M3 nut',2,[[x,34,0] for x in (-55,-41)],[0,0,1],'M3x16',10,'Install before neck; nuts accessible from base underside.')
bolt('H_SERVO_JAW','M2x10 screw + 2 washers + M2 nut',2,[[-51.25,y,JZ] for y in (4.5,32.5)],[1,0,0],'M2x10',4.5,'Check servo dimensions and nominal28mm flange pitch.')

# Interface originals, unmodified. Include them in print quantity and full assembly.
for pid,name in (('P01','torso_spine_socket'),('P03','skeletal_neck_tenon')):
    put(pid,name,b.r4neck[pid],note='Exact named embedded R4 reference recovered from supplied complete R5a assembly; original standalone R4 absent. Do not scale.',rot=[0,0,0])
bolt('H_NECK_FLANGE','M3x20 screw + 2 washers + M3 nut',4,[[x,y,0] for x in (-40,40) for y in (-22.5,22.5)],[0,0,1],'M3x20',12,'P20/P03 80x45 pattern; cable opening16x18 atY8 preserved.')
bolt('H_NECK_LOCK','M3x45 screw + 2 washers + M3 nut',2,[[-19,21,z] for z in (-48,-38)],[1,0,0],'M3x45',38,'P01 socket side-lock bores; preserve torso interface. Stand has not been physically loaded.')

# Calibration coupon: through bores, nut pockets, shaft fit, nominal servo flange test.
coupon=box((0,0,3),(80,45,6))
for i,d in enumerate((2.0,2.2,2.4,3.0,3.2,3.4,4.4,4.6,4.8)):
    coupon=hole(coupon,(-32+i*8,-12,3),(0,0,1),10,d)
for y in(-14,14):coupon=hole(coupon,(0,y+6,3),(0,0,1),10,2.4)
coupon=D(coupon,box((0,6,3),(13.2,24,10)))
put('P90','hardware_fit_coupon',coupon,note='Bench coupon only, not installed. X-row bores from left:2.0,2.2,2.4,3.0,3.2,3.4,4.4,4.6,4.8mm. Servo aperture13.2x24; flange pitch28. Print and measure before all hardware-dependent parts.',rot=[0,0,0])
edit('P35',sh('P35'),'Nonstructural iris retained by two tiny removable neutral-cure RTV dots at rim. Cure off mechanism; do not contaminate pupil/LED aperture. Cut dots to replace iris.')
bolt('H_IRIS_RTV','Neutral-cure flexible RTV adhesive, two1mm dots per iris',1,[[sx*EX,EY-14,EZ] for sx in(-1,1)],[0,1,0],'consumable',0,'Only cosmetic insert; removable. No structural glue joints.')
bolt('H_OEM_HORNS','OEM horns plus manufacturer-specific spline centre screws',5,[[0,EY,91.5],[-57.5,JY,JZ],[-1,1.75,176.5],[-54.5,lidS[1],lidS[2]],[54.5,lidS[1],lidS[2]]],[0,0,0],'R12,R14,R10x2,double±8',0,'Use supplied OEM centre screw for actual servo. No universal replacement thread assumed. Never print spline.')
bolt('H_YAW_COLLARS','Split shaft collar Ø3ID/≤7OD/3mm long, screw retained',4,[[sx*EX,EY,z] for sx in(-1,1) for z in(85.5,106.7)],[0,0,1],'Ø3x≤7x3',0,'Two per33mm shaft. Upper collar105.2..108.2 lies between bearing and globe hub; lower collar84..87 lies below crank. Verify actual clamp-screw envelope and axial stack before purchase. Collars counted only here.')
for h in hardware:
    if h['id'].startswith('H_YAW_SHAFT'):h['description']='Ground steel shaft Ø3 x33mm; collars separately H_YAW_COLLARS'
    if h['id'].startswith('H_ZYG_ROOT'):h.update(size='M3x25',description='M3x25 screw + 2 washers + M3 nut',nominal_grip_mm=16)
    if h['id'].startswith('H_FACE_'):h.update(size='M3x20',description='M3x20 socket screw + 2 washers + M3 nut')
    if h['id'].startswith('H_LID_STOP_'):h.update(size='M2x12',description='M2x12 screw + 2 washers + M2 nyloc nut')
for h in hardware:
    # Each hardware row is a location-specific joint, with stated access path and
    # unverified real hardware fit. Positive print-space joints remain test gates.
    joints.append(dict(id=h['id'],axis=h['axis'],centres_mm=h['location_mm'],hardware_id=h['id'],quantity=h['qty'],nominal_grip_mm=h['nominal_grip_mm'],tool_access=h['installation'],status='nominal CAD design; physical fit not tested'))
for pid,rot in {'P03':[180,0,0],'P21':[0,-90,0],'P23':[0,-90,0],'P34':[-90,0,0],'P39':[0,-90,0],'P40':[0,90,0],'P36':[0,0,0],'P42':[180,0,0],'P45':[0,0,0]}.items():parts[pid]['rotation']=rot

# Assembly instances and transformation contract. Every printed unique part has a STEP.
def add(name,pid,s,group='fixed',mat=None):
    instances.append(dict(name=name,id=pid,shape=s,group=group,material=mat or parts[pid]['mat']))
special={'P34','P35','P37','P38','P39','P40','P45','P46','P49','P90'}
for pid,p in parts.items():
    if pid not in special:add(pid,pid,p['shape'],'jaw' if pid in ('P33','P43') else 'fixed')
for sx,tag in ((-1,'L'),(1,'R')):
    delta=(0 if sx<0 else 67.5,0,0)
    for pid in ('P34','P35','P37'):add(pid+'_'+tag,pid,sh(pid).translate(delta),'eye_'+tag if pid!='P37' else 'crank_'+tag)
    add('P49_'+tag,'P49',sh('P49') if sx<0 else sh('P49').mirror('YZ'),'lidrod_'+tag)
add('P38_L','P38',sh('P38'),'yawlink_L')
add('P38_R','P38',sh('P38').translate((33.75,0,-2.5)),'yawlink_R')
add('P39_L','P39',sh('P39'),'lid_L');add('P40_R','P40',sh('P40'),'lid_R')
add('P45','P45',sh('P45'),'pitch');add('P46','P46',sh('P46'),'pitchrod')

# Nominal purchased servo/OEM horn envelopes. Hardware modelling is distinct from fit proof.
servo_defs={
 'MG90S_CH0_yaw':dict(tip=[0,EY,91.5],z=[0,0,-1],y=[0,1,0],group='pitch'),
 'MG90S_CH1_jaw':dict(tip=[-57.5,JY,JZ],z=[-1,0,0],y=[0,1,0],group='fixed'),
 'MG90S_CH2_pitch':dict(tip=[-1,1.75,176.5],z=[1,0,0],y=[0,1,0],group='fixed')}
for sx,tag in ((-1,'L'),(1,'R')):servo_defs['SG90_CH'+('3' if sx<0 else'4')+'_lid_'+tag]=dict(tip=[sx*54.5,lidS[1],lidS[2]],z=[sx,0,0],y=[0,1,0],group='fixed')
purchased=[]
for n,v in servo_defs.items():purchased.append(dict(name=n,shape=b.servo_at(v['tip'],v['z'],v['y']),group=v['group'],material='servo'))
# Keep service clearance at the mid arch's hidden underside, away from its outer
# curve. This shallow relief follows the actual nominal servo body envelope.
for sx in(-1,1):
    # Covers the body and mounting-tab envelope, including 0.6 mm allowance.
    relief=box((sx*37.15,lidS[1]+6,lidS[2]),(23.5,34,14.4))
    edit('P26',D(sh('P26'),relief),'Mid arch underside relieved for lid servo body with0.6mm nominal envelope allowance; exterior upper curve retained.')
    for item in instances:
        if item['id']=='P26':item['shape']=sh('P26')
horns=[('OEM_horn_CH0',(0,EY,90.5),(0,EY+12,90.5),(0,0,1),'yawhorn'),
 ('OEM_horn_CH2',(0,1.75,176.5),(0,-12.25,176.5),(1,0,0),'pitchhorn')]
for sx,tag in ((-1,'L'),(1,'R')):horns.append(('OEM_horn_lid_'+tag,(sx*55.5,lidS[1],lidS[2]),(sx*55.5,-26.45,186),(sx,0,0),'lidhorn_'+tag))
for n,s,p,a,g in horns:
    h=b.horn_arm(s,p,a);h=hole(h,p,a,6,2.2);h=hole(h,s,a,6,2.2)
    purchased.append(dict(name=n,shape=h,group=g,material='horn'))
jh=U(b.horn_arm((-58.5,JY,JZ),(-58.5,JY+8,JZ),(1,0,0)),b.horn_arm((-58.5,JY,JZ),(-58.5,JY-8,JZ),(1,0,0)))
for dy in (-8,0,8):jh=hole(jh,(-58.5,JY+dy,JZ),(1,0,0),6,2.2)
purchased.append(dict(name='OEM_horn_CH1_double',shape=jh,group='jaw',material='horn'))
for sx,tag in ((-1,'L'),(1,'R')):
    purchased.append(dict(name='STEEL_yaw_shaft_'+tag,shape=cyl(1.5,(sx*EX,EY,84),(sx*EX,EY,117)),group='eye_'+tag,material='steel'))
    for zi,z in enumerate((85.5,106.7)):
        collar=D(cyl(3.5,(sx*EX,EY,z-1.5),(sx*EX,EY,z+1.5)),cyl(1.55,(sx*EX,EY,z-2),(sx*EX,EY,z+2)))
        purchased.append(dict(name='COLLAR_'+tag+'_'+str(zi),shape=collar,group='eye_'+tag,material='steel'))

# Build reports and exports; source-to-STEP volume agreement is a mandatory digital gate.
meta=[];roundtrip=[]
for pid,p in sorted(parts.items()):
    s=p['shape'];fn=f'{pid}_{p["name"]}.step';path=ROOT/'step/parts'/fn
    cq.exporters.export(s,str(path));read=cq.importers.importStep(str(path)).val()
    delta=abs(s.Volume()-read.Volume());bb=s.BoundingBox()
    good=read.isValid() and len(read.Solids())==1 and delta<=max(.5,s.Volume()*.001)
    roundtrip.append(dict(id=pid,valid=read.isValid(),solids=len(read.Solids()),source_mm3=s.Volume(),step_mm3=read.Volume(),difference_mm3=delta,passed=good))
    rot=p.get('rotation')
    if rot is None:
        axis=min(range(3),key=lambda i:[bb.xlen,bb.ylen,bb.zlen][i]);rot=[0,90,0] if axis==0 else [90,0,0] if axis==1 else [0,0,0]
    notes='PLA 0.4mm nozzle; 0.2mm layers, 4 perimeters; baseline5mm outer brim; automatic supports reviewed per print map. Fit unverified.'
    if pid in ('P34','P39','P40'):notes='Organic shell: baseline5mm outer brim and automatic supports; protect front/iris surface. Remove support inside before installing shaft. Review slicer layer preview.'
    orientation_notes={'P03':'Print flange down, tenon upward; preserve flange face and remove cable-channel support.',
      'P21':'Print outer boss side down; supports beneath wall are required and accessible.',
      'P23':'Print broad outer cranial face down for continuous first-layer adhesion.',
      'P42':'Print root carrier down and teeth upward; preserve tooth sockets and fastener bores.'}
    if pid in orientation_notes:notes+=' '+orientation_notes[pid]
    meta.append(dict(id=pid,name=p['name'],qty=p['qty'],revision=REV,step='step/parts/'+fn,stl='stl_backup/'+Path(fn).with_suffix('.stl').name,
      material='PLA',appearance_material=p['mat'],volume_mm3=s.Volume(),size_mm=[bb.xlen,bb.ylen,bb.zlen],print_rotation_xyz_deg=rot,
      print_group='coupon' if pid=='P90' else 'mechanism' if pid in special else 'structure',print_notes=notes,
      installation=p.get('installation','Retained original appearance; inspect assembly interfaces before fastening.'),
      assembly_instances=[x['name'] for x in instances if x['id']==pid]))
    print(pid,p['name'],round(s.Volume(),3),'roundtrip',round(delta,6),flush=True)

asm=cq.Assembly(name='MIMIC_R5A_E1_ENGINEERING')
for x in instances+purchased:asm.add(x['shape'],name=x['name'])
asm.export(str(ROOT/'step/assembly/Mimic_R5a_E1_complete.step'))
motion=dict(rotation_order='Yaw about each carrier-local Z axis, then common pitch about fixed X; gaze order Rx(pitch) Rz(yaw).',
 soft_limits_deg={'yaw':[-20,20],'pitch':[-12,12],'jaw':[0,14],'lid_L':[0,50],'lid_R':[0,50]},
 mechanical_stops_deg={'yaw':[-22.99,22.99],'pitch':[-14,14],'jaw':[-.4,17.03],'lid_L':[-2.99,52.99],'lid_R':[-2.99,52.99]},
 missing_stops=[],
 axes={'pitch':{'point':[0,EY,EZ],'direction':[1,0,0]},'yaw_L':{'point':[-EX,EY,EZ],'direction':[0,0,1]},'yaw_R':{'point':[EX,EY,EZ],'direction':[0,0,1]},'jaw':{'point':[0,JY,JZ],'direction':[1,0,0]}},
 yaw_linkage={'crank_radius_mm':12,'half_tie_mm':33.75,'constraint':'Two serial planar parallelograms; 1 yaw DOF; servo fixed on common pitch carrier'},
 pitch_linkage={'pivot_yz':[EY,EZ],'output_pin_neutral_yz':[-12.25,112.5],'servo_axis_yz':[1.75,176.5],'horn_radius_mm':14,'rod_length_mm':64,'rod_plane_x':6},
 lid_linkage={'lever_yz':[9.8,-4.1],'servo_yz':[lidS[1],lidS[2]],'horn_radius_mm':10,'rod_length_mm':77.6,'rod_plane_abs_x':58.5},
 nominal_servo_speed_limit_deg_s=120,physical_status='NOT BUILT, NOT CALIBRATED')
contract=dict(revision=REV,status='ENGINEERING BUILD — digital verification in progress; hardware-fit release gates remain',parts=meta,hardware=hardware,joints=joints,
 stl_orientation='bed-oriented: CAD XYZ rotations applied, centered XY, minimum Z at zero',
 interfaces=dict(coordinates='X right, Y rear, Z up; head underside Z0',eye_centres=[[-EX,EY,EZ],[EX,EY,EZ]],jaw_axis_yz=[JY,JZ],neck_pattern_xy=[80,45],torso_holes_xz=[46,24],
 recovered_R4='Exact named P01_R4/P03_R4 from original complete R5a STEP; no standalone R4 release supplied',servo_nominal='Body12.2x22.8x22.3; flange32.5mm; hole pitch28; verify actual SG950/MG950 marking and dimensions before servo-specific parts'),
 motion=motion,servos=servo_defs,
 physical_gates=['Identify and measure every servo; distinguish microservo from standard-size MG950/MG995-class before printing mounts.','Measure OEM horn radii and hole patterns (R12 yaw,R14 pitch,R10 lids,+/-8 jaw).',
 'Print P90; measure bores, inserts and running fits.','Hand-move assembled bare mechanism; record interference and actual stop angles.','Torque/load/current/temperature testing, fastener retention and cable bend life.'],
 scene=[{k:v for k,v in x.items() if k!='shape'} for x in instances+purchased])
(ROOT/'bom/parts.json').write_text(json.dumps(contract,indent=2))
(ROOT/'validation/mechanical_report.json').write_text(json.dumps(dict(revision=REV,physical_tested=False,source_step_roundtrip=roundtrip,all_roundtrip_pass=all(x['passed'] for x in roundtrip),motion=motion,status='ADDITIONAL COLLISION AND ASSEMBLY CHECKS REQUIRED'),indent=2))
(ROOT/'cad_source/parameters.json').write_text(json.dumps(dict(revision=REV,parameters=b.P,engineering_parameters=dict(yaw_radius_mm=12,pitch_arm_mm=24,pitch_rod_mm=64,lid_rod_mm=77.6,eye_bearing_bore_mm=3.2,servo_tab_pitch_mm=28),source='Original approved concept plus explicit engineering choices; no user-measured hardware dimensions supplied',tolerances='M3 clearance3.4, running shaft3.2, M2 clearance2.2, servo flange2.4; coupons required'),indent=2))
(ROOT/'cad_source/scene_contract.json').write_text(json.dumps({k:contract[k] for k in('revision','scene','motion','servos')},indent=2))
if not all(x['passed'] for x in roundtrip):raise SystemExit('STEP roundtrip gate failed')
print('STEP BUILD COMPLETE',len(parts),'unique parts',len(instances),'printed instances',flush=True)
