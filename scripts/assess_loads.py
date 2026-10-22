"""Conditional first-order gravity, inertia and linkage screening from final STEP.
No measured servo capacity or printed-material strength is implied.
Run after the mechanical contract is frozen: python scripts/assess_loads.py RELEASE
"""
from pathlib import Path
import sys,json,math
import numpy as np
import cadquery as cq

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'bom/parts.json').read_text())
rho=1.25e-6 # chosen solid PLA analysis density, kg/mm3, not measured
g=9.80665; alpha=math.radians(180); parts={r['id']:r for r in data['parts']}
shapes={k:cq.importers.importStep(str(ROOT/v['step'])).val() for k,v in parts.items()}
massrows=[]
for pid,s in shapes.items():
    c=s.Center();b=s.BoundingBox()
    massrows.append(dict(id=pid,qty=parts[pid]['qty'],solid_mass_g=s.Volume()*rho*1000,
        centre_mm=[c.x,c.y,c.z],size_mm=[b.xlen,b.ylen,b.zlen]))

def rx(v,q):
    x,y,z=v;return np.array([x,y*math.cos(q)-z*math.sin(q),y*math.sin(q)+z*math.cos(q)])
def rz(v,q):
    x,y,z=v;return np.array([x*math.cos(q)-y*math.sin(q),x*math.sin(q)+y*math.cos(q),z])
def circles(A,S,r,L,ref):
    A=np.asarray(A,float);S=np.asarray(S,float);v=A-S;d=np.linalg.norm(v)
    if d>r+L or d<abs(r-L):raise ValueError('Unreachable rod pose')
    ex=v/d;a=(r*r-L*L+d*d)/(2*d);h=math.sqrt(max(0,r*r-a*a));perp=np.array([-ex[1],ex[0]])
    pts=[S+a*ex+h*perp,S+a*ex-h*perp]
    return min(pts,key=lambda q:np.linalg.norm(q-np.asarray(ref)))
def motor_angles(kind,qs):
    if kind in ('jaw','yaw'):return np.asarray(qs)
    m=data['motion'];out=[]
    if kind=='pitch':
        d=m['pitch_linkage'];C=np.array(d['pivot_yz']);P=np.array(d['output_pin_neutral_yz']);S=np.array(d['servo_axis_yz']);R=d['horn_radius_mm'];L=d['rod_length_mm'];ref=P+[0,L]
    else:
        d=m['lid_linkage'];C=np.array([data['interfaces']['eye_centres'][0][1],data['interfaces']['eye_centres'][0][2]]);P=C+np.array(d['lever_yz']);S=np.array(d['servo_yz']);R=d['horn_radius_mm'];L=d['rod_length_mm'];ref=np.array([P[0],P[1]+L])
    for q in qs:
        c,s=math.cos(q),math.sin(q);A=C+np.array([[c,-s],[s,c]])@(P-C)
        Q=circles(A,S,R,L,ref);out.append(math.atan2(Q[1]-S[1],Q[0]-S[0]));ref=Q
    return np.unwrap(out)

def body(pid,qty=1):
    s=shapes[pid];c=s.Center();b=s.BoundingBox()
    return dict(m=s.Volume()*rho*qty,c=np.array([c.x,c.y,c.z]),halfdiag=.5*math.sqrt(b.xlen**2+b.ylen**2+b.zlen**2),source=pid)
EY,EZ=data['interfaces']['eye_centres'][0][1:];JY,JZ=data['interfaces']['jaw_axis_yz']
pitch=[]
for pid in ('P34','P35','P37','P38','P45'):
    if pid in shapes:pitch.append(body(pid,parts[pid]['qty']))
# Purchased bodies, shafts, collars and fasteners are represented by explicit
# added point masses/radii. They are conservative chosen budgets, not weighing.
pitch += [dict(m=.025,c=np.array([0,EY,112.5]),halfdiag=25,source='25 g yaw servo/horn/cable budget'),dict(m=.030,c=np.array([0,EY,106]),halfdiag=45,source='30 g shafts/collars/fasteners budget')]
groups={'jaw':([body('P33'),body('P43'),dict(m=.010,c=np.array([0,JY-20,JZ-5]),halfdiag=30,source='10 g moving hardware budget')],np.array([0,JY,JZ]),'x',.010),
 'pitch':(pitch,np.array([0,EY,EZ]),'x',.010),
 'lid_L':([body('P39'),dict(m=.005,c=np.array([-33.75,EY+8,EZ]),halfdiag=20,source='5 g linkage/hardware budget')],np.array([-33.75,EY,EZ]),'x',.005),
 'lid_R':([body('P40'),dict(m=.005,c=np.array([33.75,EY+8,EZ]),halfdiag=20,source='5 g linkage/hardware budget')],np.array([33.75,EY,EZ]),'x',.005)}
results=[]
for axis,(bodies,C,rotation,friction) in groups.items():
    kind='lid' if axis.startswith('lid') else axis
    lo,hi=data['motion']['soft_limits_deg'][axis];qs=np.linspace(math.radians(lo),math.radians(hi),301)
    betas=motor_angles(kind,qs);ratio=np.gradient(betas,qs);minratio=float(np.min(np.abs(ratio)))
    grav=[]
    for q in qs:
        grav.append(abs(sum(b['m']*g*rx(b['c']-C,q)[1]/1000 for b in bodies)))
    Ibound=sum(b['m']*((np.linalg.norm((b['c']-C)[1:])+b['halfdiag'])/1000)**2 for b in bodies)
    # Virtual work: motor torque = output torque / |d beta / d q|.
    demand=float(np.max((np.array(grav)+Ibound*alpha)/np.abs(ratio)))+friction
    results.append(dict(axis=axis,moving_solid_and_allowance_mass_g=1000*sum(b['m'] for b in bodies),
        max_gravity_output_Nm=max(grav),inertia_upper_bound_kgm2=Ibound,
        min_abs_motor_output_angle_ratio=minratio,motor_sweep_deg=math.degrees(float(np.ptp(betas))),
        motor_speed_for_output_60_deg_s=float(np.max(np.abs(ratio))*60),
        design_demand_Nm=demand,conditional_minimum_rated_stall_Nm=4*demand,
        conditional_minimum_rated_stall_kgcm=4*demand/.0980665,
        assumptions=[b['source'] for b in bodies]))
# Shared yaw: both globes count. Pitch tilts yaw axes; worst gravity is bounded
# by full 12 degree tilt and the two globe/iris centre offsets plus hardware.
yawmass=sum(body(pid,parts[pid]['qty'])['m'] for pid in ('P34','P35','P37','P38'))+.020
Iyaw=yawmass*.035**2;Tyaw=yawmass*g*.025*math.sin(math.radians(12))+Iyaw*alpha+.005
results.append(dict(axis='yaw',moving_solid_and_allowance_mass_g=yawmass*1000,design_demand_Nm=Tyaw,
    conditional_minimum_rated_stall_Nm=4*Tyaw,conditional_minimum_rated_stall_kgcm=4*Tyaw/.0980665,
    motor_sweep_deg=40,assumptions=['Both eyes, cranks and links; 20 g additional hardware allowance','35 mm inertia radius bound; 25 mm gravity offset at 12 degree pitch','1:1 equal-radius planar parallelograms']))
rods=[]
for name,L,t,w in [('P46 pitch pushrod',data['motion']['pitch_linkage']['rod_length_mm'],2.5,6),('P49 eyelid pushrod',data['motion']['lid_linkage']['rod_length_mm'],2,6)]:
    E=500;I=w*t**3/12;load=math.pi**2*E*I/L**2
    rods.append(dict(part=name,pinned_length_mm=L,weak_axis_I_mm4=I,assumed_effective_modulus_MPa=E,ideal_euler_load_N=load,
        interpretation='Screening only: holes, layer adhesion, creep, impact and crookedness omitted. Proof test under measured rod load required.'))
report=dict(revision=data['revision'],physical_tested=False,status='CONDITIONAL ANALYTICAL SCREEN; servo capacity and printed strength unverified',
 assumptions=dict(solid_PLA_density_g_cm3=1.25,output_angular_acceleration_deg_s2=180,
    sizing_heuristic='Rated stall at least 4x screened demand; heuristic for design comparison, not continuous-duty guarantee',
    friction_reserve_Nm='0.010 jaw/pitch; 0.005 lid/yaw; chosen allowance, not measured'),
 mass=massrows,axes=results,rod_buckling=rods,
 limitations=['No measured servo model, torque-speed curve, supply drop, current or thermal data.',
 'CAD solid-density mass overestimates infill but may miss cables/fasteners; weigh final assemblies.',
 'First-order inertia bound omits exact coupled linkage dynamics and compliance.',
 'No FEA, fatigue, screw pullout, spline or clamp strength qualification.',
 'Pulse-per-degree mapping is unknown; firmware speed in us/s must be calibrated against actual angles.',
 'Neck load rating and future torso/arm/hand loads are not established.'])
(ROOT/'validation/load_speed_assessment.json').write_text(json.dumps(report,indent=2))
lines=['# Conditional load and speed assessment', '',f"Revision {data['revision']}. Analytical calculation only; no physical test.",'',
 '| Axis | Moving mass incl. allowance (g) | Screened demand (N m) | Conditional rated stall target (kg cm) | Motor sweep (deg) |',
 '|---|---:|---:|---:|---:|']
for r in results:lines.append(f"| {r['axis']} | {r['moving_solid_and_allowance_mass_g']:.1f} | {r['design_demand_Nm']:.4f} | {r['conditional_minimum_rated_stall_kgcm']:.2f} | {r['motor_sweep_deg']:.1f} |")
lines += ['', 'Mass uses a chosen 1.25 g/cm3 solid PLA density and explicit purchased-hardware allowances. Gravity follows CAD centers of mass. The output acceleration is assumed 180 deg/s2; inertia uses an enclosing-radius bound. Virtual work converts output load to motor load using the solved linkage derivative. A chosen friction reserve is included. The 4x stall target is a sizing heuristic; it does not establish continuous-duty capability.', '',
 'The actual servo markings remain uncertain (reported SG950/MG950). Do not substitute a named microservo specification for measured identification. Compare these targets to the real manufacturer curve at the measured rail voltage, then measure current, temperature, lost motion and margin in the assembled mechanism.', '',
 'A rapid blink requires both closing and reopening strokes. Minimum time is bounded by actual motor sweep divided by measured loaded speed, with extra acceleration time. The firmware is deliberately calibrated in pulse units; no angular speed claim follows until pulse-to-angle measurements are entered.', '',
 '## Printed linkage strength screening','',
 '| Rod | Ideal pinned Euler load with assumed effective E=500 MPa (N) |','|---|---:|']
for r in rods:lines.append(f"| {r['part']} | {r['ideal_euler_load_N']:.2f} |")
lines += ['', 'These ideal values omit end holes, print anisotropy, creep and imperfect straightness. Inspect rods and perform a measured compression/tension proof test with at least the chosen design load margin. No printed-part load rating is released from this calculation.', '', '## Outstanding limits', '']+['- '+x for x in report['limitations']]
(ROOT/'docs/load_speed_assessment.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(results,indent=2))
