"""Export reviewed STEP parts with recorded print orientations and verify meshes."""
from pathlib import Path
import sys,json,hashlib
import cadquery as cq
import trimesh,numpy as np
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'bom/parts.json').read_text());out=[]
selected=set(sys.argv[2:]);previous={}
if selected:
    previous={p['id']:p for p in json.loads((ROOT/'validation/mesh_report.json').read_text())['parts']}
(ROOT/'stl_backup').mkdir(exist_ok=True)
for p in d['parts']:
    if selected and p['id'] not in selected:
        row=previous[p['id']]
        row['step_sha256']=hashlib.sha256((ROOT/p['step']).read_bytes()).hexdigest()
        row['unchanged_geometry_basis']='validation/final_clearance_amendment.json'
        out.append(row);continue
    source=ROOT/p['step'];s=cq.importers.importStep(str(source)).val();vol=s.Volume()
    for axis,angle in zip([(1,0,0),(0,1,0),(0,0,1)],p['print_rotation_xyz_deg']):
        if angle:s=s.rotate((0,0,0),axis,angle)
    b=s.BoundingBox();s=s.translate((-(b.xmin+b.xmax)/2,-(b.ymin+b.ymax)/2,-b.zmin))
    target=ROOT/p['stl'];cq.exporters.export(s,str(target),tolerance=.05,angularTolerance=.1)
    m=trimesh.load_mesh(target);m.merge_vertices();m.remove_unreferenced_vertices()
    # OCC can emit zero-area triangles whose vertices collapse to the same
    # float32 point in STL (observed twice per eyelid). Removing only EXACTLY
    # zero-area triangles changes no surface, volume, or vertex coordinates.
    # No hole filling, movement, smoothing, or general mesh repair is allowed.
    zero=m.area_faces==0;removed=int(zero.sum());original_volume=float(m.volume)
    if removed:
        old_vertices=m.vertices.copy();m.update_faces(~zero);m.remove_unreferenced_vertices()
        original_points={tuple(v) for v in old_vertices}
        assert all(tuple(v) in original_points for v in m.vertices)
        assert abs(float(m.volume)-original_volume)<1e-8
        m.export(target)
    good=bool(m.is_watertight and m.is_winding_consistent and m.volume>0 and len(m.split())==1 and abs(m.volume-vol)/vol<.005)
    r=dict(id=p['id'],passed=good,watertight=bool(m.is_watertight),consistent_winding=bool(m.is_winding_consistent),
       connected_components=len(m.split()),step_volume_mm3=vol,mesh_volume_mm3=float(m.volume),relative_volume_error=abs(float(m.volume)-vol)/vol,
       rotation_xyz_deg=p['print_rotation_xyz_deg'],oriented_bounds_mm=m.bounds.tolist(),triangles=len(m.faces),
       zero_area_degenerate_triangles_removed=removed,vertex_coordinate_shift_mm=0,added_triangles=0,
       step_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),stl_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    out.append(r);print(p['id'],good,len(m.faces),r['relative_volume_error'],flush=True)
report=dict(revision=d['revision'],physical_tested=False,tessellation_tolerance_mm=.05,angular_tolerance_radians=.1,all_passed=all(x['passed'] for x in out),parts=out)
(ROOT/'validation/mesh_report.json').write_text(json.dumps(report,indent=2))
sys.exit(0 if report['all_passed'] else 1)
