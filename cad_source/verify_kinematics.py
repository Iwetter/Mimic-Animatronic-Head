"""Analytic closure/branch/transmission sweep, including design overtravel.
This validates the nominal planar constraints, not friction, backlash or strength.
"""
from pathlib import Path
import sys,json,csv,math,hashlib
from motion import solve
R=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
reports={}
for dof,lo,hi,soft in [('pitch',-17,17,(-12,12)),('lid',-5,55,(0,50))]:
    rows=[]
    def angle(a):
        s=solve(a,0) if dof=='pitch' else solve(0,a)
        return s[dof+'_horn_deg']
    for k in range(int((hi-lo)*2)+1):
        a=lo+k*.5;s=solve(a,0) if dof=='pitch' else solve(0,a)
        derivative=(angle(a+.001)-angle(a-.001))/.002
        mu=s[dof+'_transmission_deg']
        rows.append(dict(output_deg=a,horn_deg=s[dof+'_horn_deg'],closure_mm=float(s[dof+'_closure_error_mm']),
          transmission_deg=mu,acute_transmission_deg=min(mu,180-mu),horn_deg_per_output_deg=derivative,
          output_deg_per_horn_deg=1/derivative,within_soft_limits=soft[0]<=a<=soft[1]))
    with (R/f'bom/{dof}_horn_lookup.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    ratios=[abs(x['output_deg_per_horn_deg']) for x in rows]
    active=[x for x in rows if x['within_soft_limits']]
    reports[dof]=dict(sample_step_deg=.5,sampled_output_deg=[lo,hi],soft_limits_deg=soft,
       maximum_closure_mm=max(x['closure_mm'] for x in rows),minimum_acute_transmission_deg=min(x['acute_transmission_deg'] for x in rows),
       velocity_ratio_variation=max(ratios)/min(ratios),horn_range_soft_deg=[min(x['horn_deg'] for x in active),max(x['horn_deg'] for x in active)],rows=rows)
out=dict(revision='R5a-E1',physical_tested=False,status='PASS_ANALYTIC_NOMINAL_LINKAGES',
 source_sha256=hashlib.sha256((R/'cad_source/motion.py').read_bytes()).hexdigest(),
 yaw=dict(crank_radius_mm=12,tie_half_length_mm=33.75,output_equals_local_horn_deg=True,
    planar_links_including_ground=6,revolute_joints=7,mobility=1,
    rationale='3 ground-pivoted cranks plus2 separate pin-connected links: M=3(6-1)-2*7=1. Common pitch carrier adds one controlled DOF; no free translated-bar assumption.'),
 pitch_and_lid=reports,gaze_convention='Positive mechanical yaw looks+X; positive mechanical pitch looks down(-Z). Gaze=[sin(yaw),-cos(yaw)cos(pitch),-cos(yaw)sin(pitch)]. Servo pulse signs calibrated separately.',
 limitations=['Nominal rigid planar model; hole-axis alignment and measured horn radius required.','Does not validate printed pin clearance, fastener/tool access, friction, backlash, load, collisions or hardware fit.','A separate full geometry sweep is required.'])
if any(v['maximum_closure_mm']>.01 or v['minimum_acute_transmission_deg']<40 or v['velocity_ratio_variation']>3 for v in reports.values()):out['status']='FAIL_ANALYTIC_ACCEPTANCE'
(R/'validation/kinematic_report.json').write_text(json.dumps(out,indent=2))
print(out['status'],{k:{f:v[f] for f in('maximum_closure_mm','minimum_acute_transmission_deg','velocity_ratio_variation','horn_range_soft_deg')} for k,v in reports.items()})
