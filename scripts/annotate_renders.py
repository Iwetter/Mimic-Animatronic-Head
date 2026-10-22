"""Add geometry-derived part-ID callouts to final Blender renders.

Reads the exact tessellated scene JSON consumed by render_blender.py. Camera
parameters match that script. Leaders terminate at projected mesh centroids;
hidden hardware is not inferred or depicted. No design geometry is changed.
Run: python scripts/annotate_renders.py --release . --scene SCRATCH/scene.json
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def font(size,bold=False):
    for name in ([r'C:/Windows/Fonts/arialbd.ttf',r'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else [r'C:/Windows/Fonts/arial.ttf',r'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']):
        if Path(name).exists():return ImageFont.truetype(name,size)
    return ImageFont.load_default(size=size)

def projection(point,eye,target,scale,w,h):
    eye=np.array(eye);target=np.array(target);forward=target-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,np.array([0.,0.,1.]));right/=np.linalg.norm(right)
    up=np.cross(right,forward);d=np.array(point)-target
    return w/2+float(d@right)*w/scale,h/2-float(d@up)*w/scale

def annotate(root,scene,kind):
    raw=root/'renders'/f'{kind}.png';im=Image.open(raw).convert('RGB');w,h=im.size
    contract=json.loads((root/'bom/parts.json').read_text(encoding='utf-8'));names={p['id']:p['name'].replace('_',' ') for p in contract['parts']}
    if kind=='assembly_exploded':
        eye=(.7,-1,.55);target=(0,-.02,.09);scale=.58
        offsets=json.loads((root/'renders/exploded_offsets.json').read_text())['offsets']
        include=set(names)-{'P90'}
    else:
        eye=(.36,-.6,.3);target=(0,0,.11);scale=.31;offsets={}
        include={'P33','P34','P36','P37','P38','P39','P40','P41','P44','P45','P46','P49'}
    items=[];seen=set()
    for item in scene:
        pid=item['name'][:3]
        if pid not in include or pid in seen:continue
        seen.add(pid)
        vs=np.array(item['v']);center=(vs.min(axis=0)+vs.max(axis=0))/2+np.array(offsets.get(item['name'],[0,0,0]))
        x,y=projection(center,eye,target,scale,w,h);items.append((x,y,pid,names[pid]))
    margin=400;top=110;bottom=60
    out=Image.new('RGB',(w+margin*2,h+top+bottom),'#f7f9fa');out.paste(im,(margin,top));dr=ImageDraw.Draw(out)
    dr.text((30,22),'MIMIC R5a | '+('Exploded assembly' if kind=='assembly_exploded' else 'Eye and jaw mechanisms'),font=font(31,True),fill='#173443')
    dr.text((30,65),'Geometry-derived ID callouts. Repeated part IDs label one representative instance; quantities are in the BOM.',font=font(19),fill='#445963')
    # Split by image half, then distribute labels to avoid collisions.
    for left in [True,False]:
        group=sorted([i for i in items if (i[0]<w/2)==left],key=lambda x:x[1]);n=len(group)
        for j,(x,y,pid,name) in enumerate(group):
            ly=top+60+(h-120)*(j/max(n-1,1));sx=35 if left else margin+w+35
            edge=margin-18 if left else margin+w+18
            point=(margin+x,top+y);dr.line([point,(edge,ly+17),(sx+330 if left else sx-12,ly+17)],fill='#467b88',width=2)
            dr.ellipse((point[0]-5,point[1]-5,point[0]+5,point[1]+5),fill='#167e88',outline='white',width=1)
            dr.text((sx,ly-7),pid,font=font(26,True),fill='#173443')
            words=name.split();lines=[];line=''
            for word in words:
                if dr.textlength((line+' '+word).strip(),font=font(21))>335:lines.append(line);line=word
                else:line=(line+' '+word).strip()
            if line:lines.append(line)
            for k,s in enumerate(lines):dr.text((sx,ly+24+26*k),s,font=font(21),fill='#173443')
    dr.text((30,h+top+17),'Presentation view only. Fastener locations, pivot stacks and installation order are specified in the assembly manual.',font=font(19),fill='#445963')
    path=root/'renders'/f'{kind}_labeled.png';out.save(path)
    return {'image':str(path.relative_to(root)).replace('\\','/'),'ids':[x[2] for x in items],'method':'projection of exact scene bounding-box centers; camera constants from render_blender.py'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',default='.');ap.add_argument('--scene',required=True);a=ap.parse_args();root=Path(a.release).resolve();scene=json.loads(Path(a.scene).read_text())
    result=[annotate(root,scene,k) for k in ('assembly_exploded','mechanism_view')]
    (root/'renders/annotation_provenance.json').write_text(json.dumps(result,indent=2));print('Annotated final assembly and mechanism views')
if __name__=='__main__':main()
