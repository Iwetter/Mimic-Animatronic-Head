"""Independent release audit. No CAD, firmware, or printer is modified.

Run after CAD/print/manual generation, before writing SHA256SUMS.txt:
  python scripts/verify_release.py --release .
Re-check a completed hash manifest without changing audit output:
  python scripts/verify_release.py --release . --check-manifest --report PATH_OUTSIDE_RELEASE
Checks are digital evidence only. A failed/missing check never becomes a physical pass.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, pathlib, re, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CORE = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PROD = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'

def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def local(root, name):
    path=(root/name).resolve()
    if not path.is_relative_to(root): raise ValueError('Path escapes release: '+str(name))
    return path

def matrix(text):
    a=np.eye(4)
    if text: a[:3,:]=np.asarray([float(v) for v in text.split()]).reshape(4,3).T
    return a

def meshes_3mf(path):
    """Independent OPC/core/production reader, not the print packager's reader."""
    with zipfile.ZipFile(path) as archive:
        roots={}
        def root(name):
            name=name.lstrip('/')
            if name not in roots: roots[name]=ET.fromstring(archive.read(name))
            return roots[name]
        def walk(filename, identity, tr, active):
            key=(filename,identity)
            if key in active: raise ValueError('Cyclic component hierarchy')
            model=root(filename)
            if model.get('unit','millimeter')!='millimeter': raise ValueError('Non-mm 3MF')
            obj=next(x for x in model.find(CORE+'resources') if x.get('id')==identity)
            mesh=obj.find(CORE+'mesh')
            if mesh is not None:
                v=np.array([[float(n.get(k)) for k in ('x','y','z')] for n in mesh.find(CORE+'vertices')])
                f=np.array([[int(n.get(k)) for k in ('v1','v2','v3')] for n in mesh.find(CORE+'triangles')])
                m=trimesh.Trimesh(vertices=v,faces=f,process=False);m.apply_transform(tr);return [m]
            result=[]
            for component in obj.find(CORE+'components'):
                target=component.get(PROD+'path',filename).lstrip('/')
                result.extend(walk(target,component.get('objectid'),tr@matrix(component.get('transform')),active|{key}))
            return result
        main=root('3D/3dmodel.model');result=[]
        for item in main.find(CORE+'build'):
            result.append(trimesh.util.concatenate(walk('3D/3dmodel.model',item.get('objectid'),matrix(item.get('transform')),set())))
        return result

def mesh_match(actual, expected, tolerance=0.002):
    if len(actual)!=len(expected): raise ValueError(f'Instance count {len(actual)} != {len(expected)}')
    unused=list(actual);deviations=[]
    for source in expected:
        idx=min(range(len(unused)),key=lambda i:np.linalg.norm(unused[i].bounds-source.bounds))
        m=unused.pop(idx);m.merge_vertices()
        if not m.is_watertight or not m.is_winding_consistent or m.volume<=0: raise ValueError('Invalid packaged mesh')
        if len(m.faces)!=len(source.faces): raise ValueError('Changed face count')
        d=max(cKDTree(m.vertices).query(source.vertices)[0].max(),cKDTree(source.vertices).query(m.vertices)[0].max())
        if d>tolerance: raise ValueError(f'Vertex deviation {d} > {tolerance} mm')
        nearest=cKDTree(source.vertices).query(m.vertices)[1]
        af=np.sort(nearest[m.faces],axis=1);ef=np.sort(source.faces,axis=1)
        af=af[np.lexsort(af.T[::-1])];ef=ef[np.lexsort(ef.T[::-1])]
        if not np.array_equal(af,ef): raise ValueError('Changed triangle connectivity')
        if abs(m.volume-source.volume)>max(0.01,abs(source.volume)*1e-5):raise ValueError('Changed mesh volume')
        deviations.append(float(d))
    return {'instances':len(expected),'max_vertex_deviation_mm':max(deviations,default=0)}

def gcode_bounds(data):
    state=dict(X=0.,Y=0.,Z=0.,E=0.);relative_e=False;relative_xyz=False
    layer=False;feature='Custom';points=[];width=0.5;max_z=0.;layer_count=0
    for raw in data.decode('utf-8',errors='replace').splitlines():
        if raw.startswith(';LAYER_CHANGE'):layer=True;layer_count+=1
        if raw.startswith(';TYPE:'):feature=raw[6:]
        if raw.startswith(';WIDTH:'):width=max(width,float(raw[7:]))
        code=raw.split(';')[0].strip().split()
        if not code:continue
        op=code[0];args={m.group(1):float(m.group(2)) for m in re.finditer(r'([XYZE])\s*([-+]?(?:\d*\.\d+|\d+))',' '.join(code[1:]))}
        if op=='M83':relative_e=True
        if op=='M82':relative_e=False
        if op=='G90':relative_xyz=False
        if op=='G91':relative_xyz=True
        if op=='G92':state.update(args);continue
        if op in ('G2','G3') and layer:raise ValueError('Arc extrusion needs explicit arc-bounds audit')
        if op not in ('G0','G1'):continue
        before=state.copy()
        for k in ('X','Y','Z'):
            if k in args:state[k]=state[k]+args[k] if relative_xyz else args[k]
        extrusion=args.get('E',0) if relative_e else args.get('E',state['E'])-state['E']
        if 'E' in args:state['E']=state['E']+args['E'] if relative_e else args['E']
        if layer and feature!='Custom' and extrusion>0 and any(state[k]!=before[k] for k in ('X','Y')):
            points.extend([(before['X'],before['Y']),(state['X'],state['Y'])]);max_z=max(max_z,state['Z'])
    if not points:raise ValueError('No model/support/brim extrusion')
    p=np.asarray(points);lower=p.min(axis=0)-width/2;upper=p.max(axis=0)+width/2
    if lower.min() < -110 or upper.max()>110 or max_z>220:raise ValueError(f'Extrusion outside AD5M bounds: {lower}, {upper}, Z{max_z}')
    return {'layers':layer_count,'extrusion_xy_bounds_mm':[lower.tolist(),upper.tolist()],'max_z_mm':max_z,'max_width_mm':width}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',default='.');parser.add_argument('--report');parser.add_argument('--check-manifest',action='store_true')
    args=parser.parse_args();root=pathlib.Path(args.release).resolve()
    reportpath=pathlib.Path(args.report).resolve() if args.report else root/'validation/release_qa.json'
    report={'scope':'Independent digital release review; no physical testing','physical_tested':False,'checks':[],'physical_holds':[
      'Actual servo identification/dimensions/spline/voltage/current (reported sg950 and mg950 are tentative)',
      'Actuator supply, fuses, wire and connector ratings',
      'Print calibration, fit, assembly access, combined motion, load and thermal tests',
      'Scope measurements of PCA clock/OE/reset/fault behavior',
      'Original R4 release and voice source absent; audio integration unverified']}
    def check(name,fn):
        try:detail=fn();report['checks'].append({'name':name,'passed':True,'detail':detail})
        except Exception as error:report['checks'].append({'name':name,'passed':False,'error':str(error)})
    def require(paths):
        missing=[n for n in paths if not local(root,n).is_file() or not local(root,n).stat().st_size]
        if missing:raise ValueError('Missing/empty '+', '.join(missing))
        return {'files':len(paths)}
    data=json.loads((root/'bom/parts.json').read_text());parts=data['parts'];report['revision']=data['revision']
    check('required_artifacts',lambda:require(['README_FIRST.md','cad_source/build_release.py','cad_source/base_geometry.py','cad_source/parameters.json','cad_source/scene_contract.json',
      'bom/PRINT_MAP.csv','bom/plates.json','bom/electrical_BOM.csv','docs/Assembly_Manual.md','docs/Assembly_Manual.pdf','docs/Mechanical_Drawings.pdf',
      'docs/electronics.md','docs/printing.md','docs/physical_verification.csv','validation/printing_report.json','validation/mechanical_report.json','validation/firmware_report.json',
      'renders/assembly_three_quarter.png','renders/assembly_exploded.png','renders/wiring.png']))
    def manifest():
        ids=[p['id'] for p in parts]
        assert len(ids)==len(set(ids)) and all(isinstance(p['qty'],int) and p['qty']>0 for p in parts)
        assert all(p.get('revision')==data['revision'] for p in parts)
        require([p[k] for p in parts for k in ('step','stl')])
        return {'unique_parts':len(parts),'printed_pieces':sum(p['qty'] for p in parts)}
    check('parts_manifest',manifest)
    loaded={}
    def geometry():
        import cadquery as cq
        rows=[]
        for p in parts:
            shape=cq.importers.importStep(str(local(root,p['step']))).val()
            assert shape.isValid() and len(shape.Solids())==1,(p['id'],'STEP validity/solid count')
            volume=float(shape.Volume());assert abs(volume-p['volume_mm3'])<=max(0.001,volume*1e-7),(p['id'],'STEP/manifest volume mismatch')
            m=trimesh.load_mesh(local(root,p['stl']));m.merge_vertices()
            assert m.is_watertight and m.is_winding_consistent and m.volume>0,(p['id'],'mesh topology')
            assert abs(m.volume-volume)/volume<0.005,(p['id'],'mesh/STEP volume error')
            oriented=shape
            for axis,degrees in zip(((1,0,0),(0,1,0),(0,0,1)),p['print_rotation_xyz_deg']):
                if degrees:oriented=oriented.rotate((0,0,0),axis,degrees)
            bb=oriented.BoundingBox();cad_extent=np.asarray([bb.xlen,bb.ylen,bb.zlen])
            assert np.all(np.abs(m.extents-cad_extent)<.101),(p['id'],'mesh/rotated STEP extent mismatch')
            assert m.bounds[0,2]>=-0.001 and m.bounds[0,2]<0.001,(p['id'],'not seated at Z0')
            assert np.all(m.extents<=np.asarray([200,200,210])),(p['id'],'build envelope')
            m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
            loaded[p['id']]=m
            rows.append({'id':p['id'],'step_sha256':digest(local(root,p['step'])),'stl_sha256':digest(local(root,p['stl'])),'step_mm3':volume,'mesh_mm3':float(m.volume),'extent_mm':m.extents.tolist()})
        return rows
    check('step_and_mesh_geometry',geometry)
    def assembly():
        import cadquery as cq
        stepfile=root/'step/assembly/Mimic_R5a_E1_complete.step'
        named={}
        for shape,name,location,color in cq.Assembly.load(str(stepfile)):
            if shape is not None:
                short=name.split('/')[-1];assert short not in named,'Duplicate assembly name '+short
                named[short]=shape.moved(location)
        expected_scene={item['name'] for item in data['scene']}
        assert set(named)==expected_scene,{'missing':sorted(expected_scene-set(named)),'extra':sorted(set(named)-expected_scene)}
        count=0
        for part in parts:
            expected=0 if part['id']=='P90' else part['qty']
            assert len(part['assembly_instances'])==expected,(part['id'],'assembly quantity')
            for name in part['assembly_instances']:
                shape=named[name];assert shape.isValid()
                assert abs(shape.Volume()-part['volume_mm3'])<=max(.001,part['volume_mm3']*1e-7),(name,'instance volume drift')
                count+=1
        return {'named_bodies':len(named),'printed_assembly_instances':count,'fit_coupon_excluded':True,'step_sha256':digest(stepfile)}
    check('assembly_instances_match_parts_manifest',assembly)
    def mechanical_evidence():
        reportdata=json.loads((root/'validation/mechanical_report.json').read_text())
        assert reportdata['revision']==data['revision'] and reportdata['all_roundtrip_pass'] and not reportdata['physical_tested']
        byid={p['id']:p for p in parts}
        assert {r['id'] for r in reportdata['source_step_roundtrip']}==set(byid)
        for row in reportdata['source_step_roundtrip']:
            assert row['passed'] and row['valid'] and row['solids']==1
            assert abs(row['source_mm3']-byid[row['id']]['volume_mm3'])<=max(.001,row['source_mm3']*1e-7)
        mr=json.loads((root/'validation/mesh_report.json').read_text());assert mr['all_passed'] and not mr['physical_tested']
        for row in mr['parts']:
            assert row['passed'] and row['watertight'] and row['consistent_winding'] and row['connected_components']==1
            assert digest(local(root,byid[row['id']]['step']))==row['step_sha256']
            assert digest(local(root,byid[row['id']]['stl']))==row['stl_sha256']
        motion=json.loads((root/'validation/motion_report.json').read_text())
        assert not motion['physical_tested'] and motion['sampled_only']
        assert motion['collision_pose_count']==0 and motion['max_closure_mm']<=.01,motion['status']
        assert motion['status']=='PASS_SAMPLED_NOMINAL_GEOMETRY'
        amendments=[]
        for name,expected in motion['source_sha256'].items():
            actual=digest(local(root,name))
            if actual==expected:continue
            amendment=json.loads((root/'validation/source_metadata_amendment.json').read_text(encoding='utf-8'))
            assert name=='cad_source/build_release.py' and amendment['file']==name,'Undocumented motion source change: '+name
            assert amendment['old_sha256']==expected and amendment['new_sha256']==actual
            assert set(amendment['affected_fields'])<=set(('print_rotation_xyz_deg','print_notes'))
            assert amendment['unchanged_assembly_sha256']==digest(root/'step/assembly/Mimic_R5a_E1_complete.step')==motion['source_sha256']['step/assembly/Mimic_R5a_E1_complete.step']
            assert amendment['geometry_changed'] is False and amendment['reason']
            amendments.append(amendment)
        material=json.loads((root/'validation/joint_material_report.json').read_text());assert not material['missing_material'] and not material['physical_tested']
        return {'source_step_roundtrips':len(reportdata['source_step_roundtrip']),'mesh_hashes_match':True,'sampled_poses':motion['pose_count'],
          'collision_pose_count':motion['collision_pose_count'],'max_closure_mm':motion['max_closure_mm'],
          'limitations':motion['limitations'],'joint_material_checks':len(material['checks']),'documented_metadata_amendments':amendments}
    check('mechanical_evidence_current_and_digital_only',mechanical_evidence)
    def individual():
        rows=[]
        for p in parts:
            matches=list((root/'3mf/individual').glob(p['id']+'_*.3mf'));assert len(matches)==1,p['id']
            rows.append(dict(file=matches[0].relative_to(root).as_posix(),**mesh_match(meshes_3mf(matches[0]),[loaded[p['id']]])))
        assert len(list((root/'3mf/individual').glob('*.3mf')))==len(parts),'Stale/extra individual 3MF'
        return rows
    check('individual_3mf_identity',individual)
    def plates():
        plate_data=json.loads((root/'bom/plates.json').read_text());assert plate_data['revision']==data['revision']
        actual=collections.Counter(i['id'] for p in plate_data['plates'] for i in p['items']);expected=collections.Counter({p['id']:p['qty'] for p in parts});assert actual==expected,(actual,expected)
        rows=[]
        with (root/'bom/PRINT_MAP.csv').open(encoding='utf-8-sig',newline='') as stream:print_map=list(csv.DictReader(stream))
        assert collections.Counter({pid:sum(int(x['quantity']) for x in print_map if x['part_id']==pid) for pid in expected})==expected
        for plate in plate_data['plates']:
            em=[]
            for item in plate['items']:
                m=loaded[item['id']].copy();m.apply_translation(item['translation_mm']);em.append(m)
                assert np.all(m.bounds[0]>=np.asarray([-100,-100,-0.001])) and np.all(m.bounds[1]<=np.asarray([100,100,210]))
            model=local(root,plate['model_3mf']);mcheck=mesh_match(meshes_3mf(model),em)
            sliced=root/'3mf/plates'/(plate['id']+'_AD5M_PLA_0p4_sliced.3mf');scheck=mesh_match(meshes_3mf(sliced),em)
            with zipfile.ZipFile(sliced) as archive:
                cfg=json.loads(archive.read('Metadata/project_settings.config'))
                required={'nozzle_diameter':['0.4'],'layer_height':'0.2','wall_loops':'4','sparse_infill_density':'25%','brim_width':'5','enable_support':'1','print_sequence':'by layer','filament_type':['PLA'],'enable_arc_fitting':'0'}
                assert all(cfg.get(k)==v for k,v in required.items()),{k:cfg.get(k) for k in required}
                bounds=gcode_bounds(archive.read('Metadata/plate_1.gcode'))
            rows.append({'plate':plate['id'],'model':mcheck,'sliced_project':scheck,'toolpath':bounds})
        return {'quantity_match':True,'plates':rows}
    check('plates_counts_geometry_settings_toolpaths',plates)
    def firmware():
        info=json.loads((root/'validation/firmware_report.json').read_text());assert info['build']['passed'] and info['host_tests']['passed']
        assert not info['physical_tested'] and not info['flashed'] and not info['mechanical_review_accepted'] and not any(info['calibration_measured'])
        for filename,expected in info['source_sha256'].items():assert digest(local(root,filename))==expected,filename
        cal=(root/'firmware/Mimic_R5a/Calibration.h').read_text();assert 'kMechanicalReviewAccepted = false' in cal and cal.count('false')>=6
        return {'compile_report_verified':True,'host_assertions_recorded':info['host_tests']['assertions'],'source_hashes_match':True,'physical_tested':False}
    check('firmware_evidence_and_safe_defaults',firmware)
    def docs():
        manual=(root/'docs/Assembly_Manual.md').read_text(encoding='utf-8');readme=(root/'README_FIRST.md').read_text(encoding='utf-8')
        assert data['revision'] in readme,'README revision mismatch'
        missing=[p['id'] for p in parts if not re.search(r'\b'+re.escape(p['id'])+r'\b',manual)];assert not missing,'Manual missing part IDs '+str(missing)
        assert 'sg950' in (manual+readme).lower() and 'mg950' in (manual+readme).lower(),'Servo uncertainty omitted'
        assert any(t in (manual+readme).lower() for t in ['not physically','physical testing','physical test','physical verification']),'Physical status omitted'
        import fitz
        pdfs={}
        for name in ('Assembly_Manual.pdf','Mechanical_Drawings.pdf'):
            doc=fitz.open(root/'docs'/name);assert len(doc)>0 and all(p.get_text().strip() for p in doc),'Empty PDF pages'
            pdfs[name]={'pages':len(doc),'sha256':digest(root/'docs'/name)}
        return {'part_ids_present':len(parts),'pdfs':pdfs,'note':'Visual PDF review must be recorded separately; text extraction alone does not establish layout quality.'}
    check('manual_matching_and_pdf_readability',docs)
    def visual_review():
        record=json.loads((root/'validation/release_qa_visual.json').read_text(encoding='utf-8'))
        assert record['passed'],'Independent PDF visual review has an unresolved defect'
        assert not record['physical_tested']
        for item in record['files']:
            assert item['passed'] and digest(local(root,item['file']))==item['sha256'],'Visual review is stale: '+item['file']
        return record
    check('pdf_visual_review_current',visual_review)
    if args.check_manifest:
        def hashes():
            lines=(root/'SHA256SUMS.txt').read_text().splitlines();seen=set()
            for line in lines:
                if not line.strip():continue
                match=re.match(r'^([0-9a-fA-F]{64})\s+\*?(.+)$',line);assert match,'Malformed hash line'
                value,name=match.groups();assert name not in seen,'Duplicate hash entry';seen.add(name)
                assert digest(local(root,name))==value.lower(),'Hash mismatch: '+name
            actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt' and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.blend1')}
            assert seen==actual,{'missing':sorted(actual-seen),'extra':sorted(seen-actual)}
            return {'files':len(seen)}
        check('release_hash_manifest',hashes)
    report['digital_checks_passed']=all(c['passed'] for c in report['checks'])
    report['status']='DIGITAL_CHECKS_PASSED_PHYSICAL_GATES_OPEN' if report['digital_checks_passed'] else 'DIGITAL_RELEASE_CHECKS_INCOMPLETE_OR_FAILED'
    report['audited_source_sha256']={p.relative_to(root).as_posix():digest(p) for p in (root/'cad_source').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    reportpath.parent.mkdir(parents=True,exist_ok=True);reportpath.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for c in report['checks']:print(('PASS ' if c['passed'] else 'FAIL ')+c['name']+(' | '+c.get('error','') if not c['passed'] else ''))
    print(report['status']);return 0 if report['digital_checks_passed'] else 1

if __name__=='__main__':sys.exit(main())
