"""Build geometry-only individual/plate 3MFs and optionally slice actual Orca projects.
python scripts/package_prints.py --release . --orca PATH --profiles-source PATH --work WORK
Requires reviewed final STEP/STL and bom/parts.json. No printer is contacted.
"""
import argparse,pathlib,json,csv,collections,subprocess,sys,shutil,zipfile,itertools
import numpy as np
import trimesh
from printing_tools import write_3mf,validate_3mf,plate_image,parse_gcode,layer_image,sha256,complete_orca_thumbnail_parts

def profiles(source,out):
    out.mkdir(parents=True,exist_ok=True)
    names=['Flashforge Adventurer 5M 0.4 Nozzle','0.20mm Standard @Flashforge AD5M 0.4 Nozzle','Flashforge Generic PLA']
    registry={}
    # Resolve only the vendor tree: it contains the required parent chains.
    for p in source.rglob('*.json'):
        try:
            d=json.loads(p.read_text(encoding='utf-8'))
            if 'name' in d:registry[d['name']]=(d,p)
        except (ValueError,UnicodeError):pass
    provenance={}
    def resolve(n):
        d,p=registry[n];provenance[n]={'file':p.name,'sha256':sha256(p)}
        result=resolve(d['inherits']) if d.get('inherits') else {}
        result.update(d);result.pop('inherits',None);return result
    machine,process,filament=map(resolve,names)
    modifications=dict(wall_loops='4',sparse_infill_density='25%',outer_wall_speed='40',inner_wall_speed='60',
       initial_layer_speed='20',initial_layer_infill_speed='25',top_surface_speed='35',enable_support='1',
       support_type='normal(auto)',support_on_build_plate_only='0',brim_type='outer_only',brim_width='5',
       print_sequence='by layer',sparse_infill_speed='80',internal_solid_infill_speed='60',gap_infill_speed='40',
       support_speed='50',support_interface_speed='30',travel_speed='200',default_acceleration='2000',
       outer_wall_acceleration='1000',inner_wall_acceleration='1500',travel_acceleration='3000',
       internal_solid_infill_acceleration='1500',top_surface_acceleration='1000',enable_prime_tower='0',
       bottom_shell_layers='5',bottom_shell_thickness='1',support_top_z_distance='0.2',support_bottom_z_distance='0.2')
    process.update(modifications)
    filament_modifications={'filament_max_volumetric_speed':['12']}
    filament.update(filament_modifications)
    for n,d in [('printer',machine),('process',process),('filament',filament)]:
        (out/f'{n}.json').write_text(json.dumps(d,indent=2))
    (out/'provenance.json').write_text(json.dumps({'tool':'OrcaSlicer 2.4.2','source':'https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.4.2','profiles':provenance,
        'process_overrides':modifications,'filament_overrides':filament_modifications,
        'user_confirmed':'0.4 mm nozzle, PLA; physical calibration remains required'},indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',default='.');ap.add_argument('--orca')
    ap.add_argument('--profiles-source');ap.add_argument('--work',required=True);ap.add_argument('--no-slice',action='store_true')
    ap.add_argument('--slice-plates',help='Comma-separated changed plates; reuse previously validated slices for unchanged arrangements')
    a=ap.parse_args();root=pathlib.Path(a.release).resolve();work=pathlib.Path(a.work).resolve();work.mkdir(parents=True,exist_ok=True)
    selected=set(a.slice_plates.split(',')) if a.slice_plates else None
    old_slices={};old_plates={}
    if selected:
        old_slices={x['plate']:x for x in json.loads((root/'validation/printing_report.json').read_text())['slicing']}
        old_plates={x['id']:x for x in json.loads((root/'bom/plates.json').read_text())['plates']}
    data=json.loads((root/'bom/parts.json').read_text());parts=data['parts'];meshes={};checks=[]
    assert parts and len({p['id'] for p in parts})==len(parts),'Empty parts list or duplicate part IDs'
    assert all(isinstance(p['qty'],int) and p['qty']>0 for p in parts),'Quantity must be a positive integer'
    for row in parts:
        p=root/row['stl'];m=trimesh.load_mesh(p);m.merge_vertices()
        assert m.is_watertight and m.is_winding_consistent and m.volume>0,row['id']
        assert np.all(m.extents<=np.array([200,200,210])),(row['id'],m.extents)
        m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
        meshes[row['id']]=m
        path=root/'3mf/individual'/f'{row["id"]}_{row["name"]}.3mf'
        write_3mf(path,{row['id']:m},[(row['id'],np.eye(4))],f'{row["id"]} {row["name"]} | {data["revision"]}')
        result=validate_3mf(path,[m]);result['file']=str(path.relative_to(root)).replace('\\','/')
        result['source_stl']=row['stl'];result['source_stl_sha256']=sha256(p)
        if row.get('step'):result['source_step_sha256']=sha256(root/row['step'])
        planar_bottom=np.all(np.abs(m.triangles[:,:,2]-m.bounds[0,2])<.001,axis=1)
        result['flat_bed_contact_area_mm2']=float(m.area_faces[planar_bottom].sum())
        result['print_rotation_xyz_deg']=row.get('print_rotation_xyz_deg')
        result['print_notes']=row.get('print_notes','')
        result['orientation_review']='Final orientation supplied by CAD manifest; contact metric is planar mesh area, not adhesion proof.'
        checks.append(result)
    # Row shelf packing with 14 mm model separation, 10 mm to bed boundary.
    groups=collections.defaultdict(list)
    for row in parts:
        group='00_fit_coupons' if row['id'].startswith('P9') or 'coupon' in row['name'] else row.get('print_group','structure')
        for copy in range(1,int(row['qty'])+1):groups[group].append({'id':row['id'],'copy':copy})
    plates=[]
    for group,instances in sorted(groups.items()):
        instances.sort(key=lambda x:(-meshes[x['id']].extents[1],-meshes[x['id']].extents[0],x['id']))
        current=None;x=y=-100;rowdepth=0
        for item in instances:
            m=meshes[item['id']];w,h=m.extents[:2]
            if current is None:
                current={'id':f'PL{len(plates)+1:02d}','group':group,'items':[]};plates.append(current);x=y=-100;rowdepth=0
            if x+w>100+1e-6:x=-100;y+=rowdepth+14;rowdepth=0
            if y+h>100+1e-6:
                current={'id':f'PL{len(plates)+1:02d}','group':group,'items':[]};plates.append(current);x=y=-100;rowdepth=0
            current['items'].append(dict(item,translation_mm=[float(x-m.bounds[0,0]),float(y-m.bounds[0,1]),0]))
            x+=w+14;rowdepth=max(rowdepth,h)
    counts=collections.Counter(i['id'] for p in plates for i in p['items'])
    assert counts==collections.Counter({p['id']:int(p['qty']) for p in parts})
    # Center each packed plate as a rigid group; all pairwise spacings are retained.
    for plate in plates:
        b=np.array([meshes[it['id']].bounds+it['translation_mm'] for it in plate['items']])
        center=(b[:,0,:].min(axis=0)+b[:,1,:].max(axis=0))/2
        for it in plate['items']:
            it['translation_mm'][0]-=float(center[0]);it['translation_mm'][1]-=float(center[1])
    platechecks=[]
    for plate in plates:
        expected=[];items=[]
        for it in plate['items']:
            tr=np.eye(4);tr[:3,3]=it['translation_mm'];items.append((it['id'],tr))
            m=meshes[it['id']].copy();m.apply_transform(tr);expected.append(m)
            assert np.all(m.bounds[0]>=np.array([-100,-100,-.001])) and np.all(m.bounds[1]<=np.array([100,100,210])),plate['id']
        plate['model_3mf']=f'3mf/plates/{plate["id"]}_{plate["group"]}_models.3mf'
        write_3mf(root/plate['model_3mf'],{i['id']:meshes[i['id']] for i in plate['items']},items,plate['id']+' | '+data['revision'])
        check=validate_3mf(root/plate['model_3mf'],expected);check['file']=plate['model_3mf'];platechecks.append(check)
        clearances=[]
        for ma,mb in itertools.combinations(expected,2):
            # Axis-aligned footprint distance is a conservative lower bound to model distance.
            gap=np.maximum(0,np.maximum(ma.bounds[0,:2]-mb.bounds[1,:2],mb.bounds[0,:2]-ma.bounds[1,:2]))
            clearance=float(np.linalg.norm(gap));clearances.append(clearance)
            assert clearance>=14-1e-6,(plate['id'],'model spacing',clearance)
        check['minimum_xy_box_clearance_mm']=min(clearances) if clearances else None
        plate_image(root/'renders/plates'/f'{plate["id"]}.png',plate,meshes)
    (root/'bom/plates.json').write_text(json.dumps({'revision':data['revision'],'bed_mm':[220,220,220],'edge_margin_mm':10,'model_spacing_mm':14,'plates':plates},indent=2))
    rows=[];lookup={r['id']:r for r in parts}
    for plate in plates:
        for pid,n in collections.Counter(i['id'] for i in plate['items']).items():
            p=lookup[pid];rows.append({'plate':plate['id'],'print_once':1,'part_id':pid,'name':p['name'],'quantity':n,'material':'PLA','nozzle_mm':.4,'layer_mm':.2,
                'model_3mf':plate['model_3mf'],'sliced_project':f'3mf/plates/{plate["id"]}_AD5M_PLA_0p4_sliced.3mf' if not a.no_slice else '',
                'orientation':str(p.get('print_rotation_xyz_deg','see delivered geometry')),'notes':p.get('print_notes','Review support removal')})
    with (root/'bom/PRINT_MAP.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    reports={'revision':data['revision'],'parts_manifest_sha256':sha256(root/'bom/parts.json'),
        'source_cad_sha256':{str(p.relative_to(root)).replace('\\','/'):sha256(p) for p in (root/'cad_source').glob('*.py')},
        'individual':checks,'plates':platechecks,'quantity_match':True,'slicing':[],'hardware_tested':False,
        'mesh_identity_tolerance_mm':.002,'status':'software checks only; physical fit and print calibration required'}
    if not a.no_slice:
        assert a.orca and a.profiles_source,'Pass --orca and --profiles-source, or --no-slice'
        proot=root/'scripts/profiles';profiles(pathlib.Path(a.profiles_source).resolve(),proot)
        for plate in plates:
            if selected is not None and plate['id'] not in selected:
                assert plate['items']==old_plates[plate['id']]['items'],'Unchanged plate arrangement changed'
                record=old_slices[plate['id']]
                assert record['success']
                record['reused_unchanged_plate']=True
                reports['slicing'].append(record)
                continue
            scratch=work/plate['id'];scratch.mkdir(exist_ok=True)
            filename=plate['id']+'_AD5M_PLA_0p4_sliced.3mf'
            args=[str(pathlib.Path(a.orca).resolve()),str(root/plate['model_3mf']),
                '--load-settings',str(proot/'process.json')+';'+str(proot/'printer.json'),
                '--load-filaments',str(proot/'filament.json'),'--arrange','0','--orient','0',
                '--slice','0','--outputdir',str(scratch),'--export-3mf',filename,'--debug','2']
            result=subprocess.run(args,capture_output=True,timeout=900)
            (scratch/'log.txt').write_bytes(result.stdout+result.stderr)
            logfile=root/'validation'/f'printing_{plate["id"]}.log';logfile.write_bytes(result.stdout+result.stderr)
            record={'plate':plate['id'],'return_code':result.returncode,'tool':'OrcaSlicer 2.4.2','command':args,
                'log':str(logfile.relative_to(root)).replace('\\','/'),'digital_only':True,'success':False}
            if result.returncode==0 and (scratch/filename).exists():
                target=root/'3mf/plates'/filename
                record['thumbnail_completion']=complete_orca_thumbnail_parts(scratch/filename,target,root/'renders/plates'/f'{plate["id"]}.png')
                record['slicer_original_content_unchanged']=True
                record['sliced_3mf']='3mf/plates/'+filename
                expected=[]
                for it in plate['items']:
                    m=meshes[it['id']].copy();m.apply_translation(it['translation_mm']);expected.append(m)
                record['model_validation']=validate_3mf(target,expected)
                record['model_validation']['file']=record['sliced_3mf']
                expected_count=len(plate['items']);assert record['model_validation']['instances']==expected_count,(plate['id'],'slicer changed quantity')
                layers,summary,picks=parse_gcode(scratch/'plate_1.gcode')
                record['toolpath']=summary;record['preview_layers_1based']=[i+1 for i in picks]
                layer_image(root/'renders/layers'/f'{plate["id"]}_layers.png',plate['id'],layers,picks)
                # G-code is retained inside the sliced 3MF as evidence, not separately advertised as verified printer execution.
                assert summary['within_bed'],(plate['id'],'toolpaths outside bed',summary)
                with zipfile.ZipFile(target) as z:
                    cfg=json.loads(z.read('Metadata/project_settings.config'))
                    required={'nozzle_diameter':['0.4'],'layer_height':'0.2','wall_loops':'4','sparse_infill_density':'25%',
                         'brim_width':'5','enable_support':'1','print_sequence':'by layer','filament_type':['PLA']}
                    record['settings_checked']={k:cfg.get(k) for k in required}
                    assert all(cfg.get(k)==v for k,v in required.items()),record['settings_checked']
                    record['embedded_gcode_sha256']=sha256(scratch/'plate_1.gcode')
                    assert z.read('Metadata/plate_1.gcode')==(scratch/'plate_1.gcode').read_bytes()
                record['success']=True
            reports['slicing'].append(record)
            (root/'validation/printing_report.json').write_text(json.dumps(reports,indent=2))
            print(plate['id'],'slice',result.returncode,flush=True)
    reports['all_slices_pass']=len(reports['slicing'])==len(plates) and all(x['success'] for x in reports['slicing'])
    (root/'validation/printing_report.json').write_text(json.dumps(reports,indent=2))
    print('Packaged',len(parts),'unique parts,',sum(counts.values()),'pieces,',len(plates),'plates',flush=True)
if __name__=='__main__':main()
