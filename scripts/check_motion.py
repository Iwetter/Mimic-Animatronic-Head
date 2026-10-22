"""Sampled revised assembly collision check. No continuous or physical claim."""
from pathlib import Path
import sys,json,itertools,hashlib,time,os
from concurrent.futures import ProcessPoolExecutor,as_completed
os.environ["OMP_NUM_THREADS"]="1"
os.environ["OPENBLAS_NUM_THREADS"]="1"
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad_source'))
from motion import Scene,solve

scene=None;pair_cache={}
def worker_init(root):
    global scene,pair_cache
    scene=Scene(root);pair_cache={}
cases=[dict(label='neutral')]
for key,values in [('yaw',range(-20,21,2)),('pitch',range(-12,13,2)),('jaw',range(0,15)),('lid_L',range(0,51,2)),('lid_R',range(0,51,2))]:
    cases += [dict(label=key+'_'+str(v),**{key:v}) for v in values if v]
for y,p,l,j in itertools.product((-20,20),(-12,12),(0,50),(0,14)):
    cases.append(dict(label=f'combined_{y}_{p}_{l}_{j}',yaw=y,pitch=p,jaw=j,lid_L=l,lid_R=l))
# Coupled eye sweep is required: single-axis sweeps do not bound rotated
# globes against stationary lid arms. Use2deg yaw/pitch grid at open lids.
for y,p in itertools.product(range(-20,21,2),range(-12,13,2)):
    if y and p:cases.append(dict(label=f'eye_grid_{y}_{p}',yaw=y,pitch=p))
# Independent eyelid asymmetry at combined extreme eyes, not only both lids equal.
for y,p,ll,rr in itertools.product((-20,20),(-12,12),(0,50),(0,50)):
    if ll!=rr:cases.append(dict(label=f'asymmetric_{y}_{p}_{ll}_{rr}',yaw=y,pitch=p,lid_L=ll,lid_R=rr,jaw=14))

def overlap(a,b):return all(getattr(a,k+'max')>getattr(b,k+'min')+.001 and getattr(b,k+'max')>getattr(a,k+'min')+.001 for k in 'xyz')
def deps(g):
    if g=='fixed':return()
    if g=='jaw':return('jaw',)
    if g.startswith(('eye_','crank_','yawlink')) or g=='yawhorn':return('yaw','pitch')
    if g in('pitch','pitchrod','pitchhorn'):return('pitch',)
    if g.startswith(('lid_','lidrod_','lidhorn_')):return('lid_'+g[-1],)
    raise ValueError(g)
def check_case(task):
    ci,case=task
    label=case['label'];pose={k:v for k,v in case.items() if k!='label'}
    items,sol=scene.pose(**pose);ns=[]
    for it in items:ns.append((it['name'],it['shape'],it['shape'].BoundingBox(),it['group']))
    ph=[]
    for i,(an,a,ab,ag) in enumerate(ns):
        for bn,b,bb,bg in ns[i+1:]:
            if ci and ag=='fixed' and bg=='fixed':continue
            if ci and ag==bg:continue # same rigid transform; neutral already checked
            if not overlap(ab,bb):continue
            dd=sorted(set(deps(ag)+deps(bg)));ck=(an,bn)+tuple((d,pose.get(d,0)) for d in dd)
            if ck in pair_cache:vol=pair_cache[ck]
            else:
                c=a.intersect(b);vol=sum(s.Volume() for s in c.Solids());pair_cache[ck]=vol
            if vol>.05:ph.append(dict(a=an,b=bn,volume_mm3=vol))
    errs=[sol['pitch']['pitch_closure_error_mm']]+[s['lid_closure_error_mm'] for s in sol['lids'].values()]
    mus=[sol['pitch']['pitch_transmission_deg']]+[s['lid_transmission_deg'] for s in sol['lids'].values()]
    clearances=[]
    if label=='neutral' or label.startswith(('combined_','asymmetric_')):
        dct={n:s for n,s,bb,g in ns}
        for an,bn in [('P34_L','P36'),('P34_R','P36'),('P34_L','P39_L'),('P34_R','P40_R'),('P34_L','P45'),('P38_L','P36'),('P38_R','P36'),('P46','P41'),('P33','P03'),('P33','P20')]:
            d=BRepExtrema_DistShapeShape(dct[an].wrapped,dct[bn].wrapped);d.Perform()
            clearances.append(dict(a=an,b=bn,distance_mm=d.Value() if d.IsDone() else None))
    return ci,dict(**case,closure_max_mm=float(max(errs)),min_transmission_angle_deg=min(min(m,180-m) for m in mus),overlaps=ph,selected_clearances_mm=clearances)

def main():
    input_hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'cad_source/build_release.py',ROOT/'cad_source/motion.py',ROOT/'step/assembly/Mimic_R5a_E1_complete.step']}
    rows=[];hits=[];start=time.time();workers=int(os.environ.get('MIMIC_SWEEP_WORKERS','8'))
    # Extreme combined poses first so failures are visible before the fine grid.
    ordered=[(i,c) for i,c in enumerate(cases) if i==0 or c['label'].startswith(('combined_','asymmetric_'))]+[(i,c) for i,c in enumerate(cases) if i!=0 and not c['label'].startswith(('combined_','asymmetric_'))]
    with ProcessPoolExecutor(max_workers=workers,initializer=worker_init,initargs=(str(ROOT),)) as pool:
        futures=[pool.submit(check_case,x) for x in ordered]
        for future in as_completed(futures):
            ci,row=future.result();rows.append((ci,row));ph=row['overlaps']
            if ph:hits.append(row)
            print(len(rows),'/',len(cases),row['label'],'hits',len(ph),json.dumps(ph) if ph else '',flush=True)
            (ROOT/'validation/motion_progress.json').write_text(json.dumps(dict(status='RUNNING',completed=len(rows),total=len(cases),collision_pose_count=len(hits),last_pose=row['label'],hits=hits),indent=2))
    rows=[x[1] for x in sorted(rows,key=lambda x:x[0])]
    report=dict(revision='R5a-E1',physical_tested=False,sampled_only=True,
     status='PASS_SAMPLED_NOMINAL_GEOMETRY' if not hits else 'FAIL_UNINTENDED_SOLID_INTERSECTIONS',
     source_sha256=input_hashes,
     threshold_mm3=.05,excluded_pairs=[],poses=rows,pose_count=len(rows),collision_pose_count=len(hits),
     max_closure_mm=max(x['closure_max_mm'] for x in rows),elapsed_s=time.time()-start,
     limitations=['Discrete samples only; no continuous swept-volume proof.','Nominal purchased servo/horn envelopes, not actual hardware.','Fastener heads/nuts, collars and cables are not fully solid-modeled; measured fit/access and physical sweep required.','Zero intersection does not establish tolerance margin or print/assembly success.'])
    (ROOT/'validation/motion_report.json').write_text(json.dumps(report,indent=2))
    print(report['status'],len(hits),'collision poses',flush=True)
    sys.exit(1 if hits or report['max_closure_mm']>.01 else 0)

if __name__=="__main__":main()
