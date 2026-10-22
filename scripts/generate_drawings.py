"""Generate orthographic SVG reference drawings from final STEP, without changing geometry.
Usage: python scripts/generate_drawings.py --release .
Dimensions are true millimetre overall extents; interface dimensions are in the contract.
These views supplement, not replace, feature/tolerance data in source and assembly manual.
"""
import argparse,pathlib,json,hashlib,html,re
import cadquery as cq
from cadquery.occ_impl.exporters.svg import getSVG

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',default='.');ap.add_argument('--part');a=ap.parse_args()
    root=pathlib.Path(a.release).resolve();d=json.loads((root/'bom/parts.json').read_text())
    out=root/'docs/drawings';out.mkdir(parents=True,exist_ok=True);index=[]
    for row in d['parts']:
        if a.part and row['id']!=a.part:
            index.append({'id':row['id'],'drawing':'docs/drawings/'+row['id']+'_drawing.svg','step_sha256':hashlib.sha256((root/row['step']).read_bytes()).hexdigest()});continue
        pid=row['id'];p=root/row['step'];s=cq.importers.importStep(str(p)).val();bb=s.BoundingBox()
        heading=f"{pid} | {row['name'].replace('_',' ')}"
        body=['<rect width="1200" height="850" fill="white"/>',
            f'<text x="45" y="50" font-size="25" font-weight="bold">{html.escape(heading)}</text>',
            f'<text x="45" y="78" font-size="14">Revision {html.escape(str(d.get("revision","R5a-M1")))} | Units mm | Qty {row["qty"]} | PLA, 0.4 mm nozzle</text>']
        for label,direction,x,y in [('FRONT (look +Y)',(0,-1,0),30,110),('RIGHT (look -X)',(1,0,0),610,110),('TOP (look -Z)',(0,0,1),30,430)]:
            svg=getSVG(s,{'width':530,'height':270,'marginLeft':25,'marginTop':20,'projectionDir':direction,
                'showAxes':False,'showHidden':True,'strokeWidth':.5,'strokeColor':(25,40,50),'hiddenColor':(170,180,190)})
            svg=re.sub(r'<\?xml.*?\?>','',svg,flags=re.S)
            # svglib does not honor nested SVG x/y placement reliably. Flatten
            # the viewport to an ordinary translated group for PDF rendering.
            svg=re.sub(r'<svg\b[^>]*>',f'<g transform="translate({x},{y})">',svg,count=1)
            svg=re.sub(r'</svg>\s*$', '</g>', svg)
            body.append(f'<text x="{x+20}" y="{y-10}" font-size="15" font-weight="bold">{label}</text>');body.append(svg)
        body.extend([
            '<rect x="630" y="465" width="520" height="235" fill="#f2f5f7" stroke="#97a6b0"/>',
            '<text x="650" y="495" font-size="18" font-weight="bold">Overall dimensions in assembly axes</text>',
            f'<text x="650" y="530" font-size="22">X {bb.xlen:.2f}  x  Y {bb.ylen:.2f}  x  Z {bb.zlen:.2f} mm</text>',
            f'<text x="650" y="565" font-size="15">Solid volume: {s.Volume()/1000:.3f} cm3 | Not a slicer mass</text>',
            '<text x="650" y="600" font-size="14">Hole fits, fasteners and datums: see interface contract.</text>',
            '<text x="650" y="625" font-size="14">Verify fits with coupons; do not scale drawing to measure.</text>',
            '<text x="650" y="650" font-size="14">Views fit independently. Dashed/grey lines are hidden edges.</text>',
            '<text x="45" y="757" font-size="14">X right, Y rear, Z up; face toward -Y. STEP is stored in assembly coordinates.</text>',
            f'<text x="45" y="783" font-size="13">Source: {html.escape(row["step"])} | SHA-256 {hashlib.sha256(p.read_bytes()).hexdigest()[:20]}...</text>',
            '<text x="45" y="809" font-size="13">REFERENCE GEOMETRY DRAWING | No physical manufacture or fit test implied.</text>'])
        text='<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="850" viewBox="0 0 1200 850" font-family="Arial, sans-serif">'+''.join(body)+'</svg>'
        target=out/f'{pid}_drawing.svg';target.write_text(text,encoding='utf-8');index.append({'id':pid,'drawing':str(target.relative_to(root)).replace('\\','/'),'step_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    # Dimensioned interface schedule supplements the part-by-part reference views.
    # These values are independently measured in baseline_reconciliation.md and
    # preserved by the revised source; no absent torso geometry is invented.
    b=['<rect width="1200" height="850" fill="white"/>',
       '<text x="45" y="48" font-size="25" font-weight="bold">INTERFACE DATUMS | Recovered R4 reference geometry</text>',
       f'<text x="45" y="78" font-size="15">Revision {html.escape(str(d["revision"]))} | mm | Schematics: use dimensions, not image scale</text>',
       '<text x="45" y="120" font-size="19" font-weight="bold">P20 / P03 head flange — top view</text>',
       '<rect x="70" y="155" width="480" height="305" fill="#f2f5f7" stroke="#223b4b" stroke-width="2"/>',
       '<path d="M310 135V480 M50 307.5H570" stroke="#8698a3" stroke-dasharray="7 5"/>']
    for x in (-40,40):
        for y in (-22.5,22.5):b.append(f'<circle cx="{310+x*5}" cy="{307.5-y*5}" r="8.5" fill="white" stroke="#223b4b" stroke-width="2"/>')
    b += ['<rect x="270" y="222.5" width="80" height="90" fill="white" stroke="#223b4b" stroke-width="2"/>',
      '<path d="M110 185V140 M510 185V140 M110 145H510" fill="none" stroke="#223b4b"/>',
      '<text x="270" y="137" font-size="16">80.00</text>',
      '<path d="M100 195H40 M100 420H40 M45 195V420" fill="none" stroke="#223b4b"/>',
      '<text x="52" y="320" font-size="15" transform="rotate(-90 52 320)">45.00</text>',
      '<text x="75" y="490" font-size="15">4 x Ø3.40 through Z; X = ±40; Y = ±22.5</text>',
      '<text x="75" y="516" font-size="15">Cable: 16 x 18; center X0, Y8</text>',
      '<text x="75" y="542" font-size="15">Flange contact Z0; P03: -6..0; P20: 0..6</text>',
      '<text x="75" y="568" font-size="15">Nominal bolted grip: 12; H_NECK_FLANGE M3x20</text>',
      '<text x="640" y="120" font-size="19" font-weight="bold">P01 torso mounting — rear view (XZ)</text>']
    for x in (-23,23):
        for z in (-55,-31):b.append(f'<circle cx="{865+x*5}" cy="{300-(z+43)*5}" r="8.5" fill="white" stroke="#223b4b" stroke-width="2"/>')
    b += ['<path d="M865 170V430 M690 300H1040" stroke="#8698a3" stroke-dasharray="7 5"/>',
       '<path d="M750 230V190 M980 230V190 M750 195H980 M990 240H1050 M990 360H1050 M1045 240V360" fill="none" stroke="#223b4b"/>',
       '<text x="835" y="185" font-size="16">46.00</text><text x="1055" y="305" font-size="16">24.00</text>',
       '<text x="645" y="460" font-size="15">4 x Ø3.40, parallel Y; X = ±23; Z = -55/-31</text>',
       '<text x="645" y="486" font-size="15">Rear plate Y31..37; mating torso not supplied</text>',
       '<text x="645" y="530" font-size="17" font-weight="bold">Tenon / socket and cross locks</text>',
       '<text x="645" y="558" font-size="15">Tenon 28 x 36; socket 28.6 x 36.6</text>',
       '<text x="645" y="584" font-size="15">Nominal side gap 0.30; fit coupon/assembly required</text>',
       '<text x="645" y="610" font-size="15">Cross locks Ø3.40 along X; Y21, Z-48/-38</text>',
       '<text x="645" y="636" font-size="15">Across-stack 38; H_NECK_LOCK M3x45</text>',
       '<text x="45" y="705" font-size="16" font-weight="bold">Datums: X right; Y rear; Z up; head base underside Z0.</text>',
       '<text x="45" y="739" font-size="15">Exact embedded P01/P03 solids retained. Original standalone R4 and mating torso were not supplied.</text>',
       '<text x="45" y="769" font-size="15">Nominal geometry only: print shrinkage, fastener stack, assembly fit and neck load rating remain untested.</text>',
       '<text x="45" y="805" font-size="13">Evidence: validation/baseline_reconciliation.md | final part STEP and bom/parts.json</text>']
    target=out/'interface_datums.svg'
    target.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="850" viewBox="0 0 1200 850" font-family="Arial, sans-serif">'+''.join(b)+'</svg>',encoding='utf-8')
    index.append({'id':'INTERFACES','drawing':'docs/drawings/interface_datums.svg','step_sha256':'see part drawing references'})
    (out/'index.json').write_text(json.dumps(index,indent=2));print('Drawings',len(index))
if __name__=='__main__':main()
