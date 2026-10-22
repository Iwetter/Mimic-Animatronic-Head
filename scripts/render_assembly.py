"""Render named STEP solids with Blender. No design geometry is modified.
Usage: python render_assembly.py ASSEMBLY.step --blender PATH --out renders --work WORK
Requires CadQuery and Blender. The assembly STEP is the geometry authority.
"""
import argparse,json,pathlib,subprocess
import cadquery as cq

def main():
    ap=argparse.ArgumentParser();ap.add_argument('assembly');ap.add_argument('--blender',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--work',required=True)
    a=ap.parse_args();out=pathlib.Path(a.out).resolve();scratch=pathlib.Path(a.work).resolve()
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    assembly=cq.Assembly.load(a.assembly);items=[]
    for shape,name,loc,color in assembly:
        if shape is None:continue
        s=shape.moved(loc);vertices,triangles=s.tessellate(.15,.15)
        items.append({'name':name.split('/')[-1], 'v':[[v.x/1000,v.y/1000,v.z/1000] for v in vertices],
                      'f':[list(t) for t in triangles]})
    (scratch/'scene.json').write_text(json.dumps(items))
    script=pathlib.Path(__file__).with_name('render_blender.py')
    command=[a.blender,'--background','--factory-startup','--python',str(script),'--',str(scratch/'scene.json'),str(out)]
    r=subprocess.run(command,capture_output=True,text=True)
    (scratch/'blender_render.log').write_text(r.stdout+'\n'+r.stderr)
    if r.returncode:raise RuntimeError(f'Blender failed: {r.returncode}; see render log')
    print('Rendered',len(items),'named components to',out)
if __name__=='__main__':main()
