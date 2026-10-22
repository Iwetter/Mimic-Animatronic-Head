"""Actual R5a-E1 constrained mechanism transforms and planar closure solver.

Axes use world XYZ. Common carrier pitch is Rx about (0,-36.25,112.5),
eye local yaw Rz occurs first. All yaw cranks are R12 and tie spans33.75.
Rod endpoints rotate about X, so planar YZ circle intersection is exact.
"""
import json,math
from pathlib import Path
import cadquery as cq
import numpy as np

EX,EY,EZ=33.75,-36.25,112.5
def rx(p,deg,c=(0,EY,EZ)):
    p=np.array(p,float);c=np.array(c,float);a=math.radians(deg);d=p-c
    return c+np.array([d[0],d[1]*math.cos(a)-d[2]*math.sin(a),d[1]*math.sin(a)+d[2]*math.cos(a)])
def circle_solve(S,B,r,L,P0):
    """Return horn pin closest to known neutral branch, exact two-circle closure."""
    S=np.array(S,float);B=np.array(B,float);P0=np.array(P0,float)
    d=B-S;D=float(np.linalg.norm(d));a=(r*r-L*L+D*D)/(2*D);h2=r*r-a*a
    if h2 < -1e-8:raise ValueError({'unreachable':True,'S':S.tolist(),'B':B.tolist(),'r':r,'L':L,'h2':h2})
    u=d/D;v=np.array([-u[1],u[0]]);mid=S+a*u;h=math.sqrt(max(0,h2))
    candidates=[mid+h*v,mid-h*v];P=min(candidates,key=lambda p:np.linalg.norm(p-P0))
    a0=math.atan2(P0[1]-S[1],P0[0]-S[0]);angle=math.atan2(P[1]-S[1],P[0]-S[0])-a0
    angle=(angle+math.pi)%(2*math.pi)-math.pi
    u=(B-P)/L;v=(P-S)/r;mu=math.degrees(math.acos(float(np.clip(np.dot(u,v),-1,1))))
    return P,math.degrees(angle),abs(np.linalg.norm(P-B)-L),mu
def solve(pitch=0,lid=0):
    B=rx((6,-12.25,112.5),pitch)[1:]
    PP,pa,pe,pm=circle_solve((1.75,176.5),B,14,64,(-12.25,176.5))
    LS=(-26.45+10*math.cos(math.radians(35)),186+10*math.sin(math.radians(35)))
    LB=rx((0,-26.45,108.4),lid)[1:]
    LP,la,le,lm=circle_solve(LS,LB,10,77.6,(-26.45,186))
    return dict(pitch_pin_yz=PP.tolist(),pitch_lower_yz=B.tolist(),pitch_horn_deg=pa,pitch_closure_error_mm=pe,pitch_transmission_deg=pm,
        lid_pin_yz=LP.tolist(),lid_lower_yz=LB.tolist(),lid_horn_deg=la,lid_closure_error_mm=le,lid_transmission_deg=lm)
def angle_from_vertical(v):return math.degrees(math.atan2(-v[0],v[1]))
class Scene:
    def __init__(self,release):
        self.root=Path(release);self.contract=json.loads((self.root/'cad_source/scene_contract.json').read_text())
        groups={x['name']:x['group'] for x in self.contract['scene']}
        self.items=[]
        for s,n,l,c in cq.Assembly.load(str(self.root/'step/assembly/Mimic_R5a_E1_complete.step')):
            if s is not None:self.items.append(dict(name=n.split('/')[-1],shape=s.moved(l),group=groups[n.split('/')[-1]]))
    def pose(self,yaw=0,pitch=0,jaw=0,lid_L=0,lid_R=0):
        sol=solve(pitch,0);ls={tag:solve(0,lid_L if tag=='L' else lid_R) for tag in('L','R')}
        ans=[]
        for item in self.items:
            n,g,s=item['name'],item['group'],item['shape']
            if g=='jaw':s=s.rotate((0,12.5,56.25),(1,12.5,56.25),jaw)
            elif g in('eye_L','eye_R','crank_L','crank_R'):
                x=-EX if g.endswith('L') else EX
                s=s.rotate((x,EY,EZ),(x,EY,EZ+1),yaw).rotate((0,EY,EZ),(1,EY,EZ),pitch)
            elif g=='pitch':s=s.rotate((0,EY,EZ),(1,EY,EZ),pitch)
            elif g.startswith('yawlink'):
                a=math.radians(yaw);s=s.translate((-12*math.sin(a),12*(math.cos(a)-1),0)).rotate((0,EY,EZ),(1,EY,EZ),pitch)
            elif g=='yawhorn':s=s.rotate((0,EY,90.5),(0,EY,91.5),yaw).rotate((0,EY,EZ),(1,EY,EZ),pitch)
            elif g=='pitchhorn':s=s.rotate((0,1.75,176.5),(1,1.75,176.5),sol['pitch_horn_deg'])
            elif g=='pitchrod':
                low=np.array(sol['pitch_lower_yz']);hi=np.array(sol['pitch_pin_yz']);ang=angle_from_vertical(hi-low)
                s=s.rotate((6,-12.25,112.5),(7,-12.25,112.5),ang).translate((0,low[0]+12.25,low[1]-112.5))
            elif g.startswith('lid_'):
                x=-EX if g.endswith('L') else EX;l=lid_L if g.endswith('L') else lid_R
                s=s.rotate((x,EY,EZ),(x+1,EY,EZ),l)
            elif g.startswith('lidrod_'):
                tag=g[-1];x=-58.5 if tag=='L' else 58.5;lo=np.array(ls[tag]['lid_lower_yz']);hi=np.array(ls[tag]['lid_pin_yz']);ang=angle_from_vertical(hi-lo)
                s=s.rotate((x,-26.45,108.4),(x+1,-26.45,108.4),ang).translate((0,lo[0]+26.45,lo[1]-108.4))
            elif g.startswith('lidhorn_'):
                tag=g[-1];x=-55.5 if tag=='L' else 55.5;S=(-26.45+10*math.cos(math.radians(35)),186+10*math.sin(math.radians(35)))
                s=s.rotate((x,S[0],S[1]),(x+1,S[0],S[1]),ls[tag]['lid_horn_deg'])
            ans.append(dict(name=n,shape=s,group=g))
        return ans,dict(pitch=sol,lids=ls)
