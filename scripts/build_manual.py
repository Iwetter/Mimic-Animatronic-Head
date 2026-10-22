"""Build revision-bound assembly manual and mechanical reference drawing PDFs.

Run from release root: python scripts/build_manual.py --release .
Requires reportlab, pillow, svglib and pymupdf. Inputs must be final geometry,
parts contract, print map, assembly notes, electronics and firmware documents.
This generator never creates mechanical dimensions or infers hardware identity.
"""
from __future__ import annotations
import argparse, csv, html, json, re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, Preformatted, KeepTogether
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from PIL import Image as PILImage

INK=colors.HexColor('#173443'); TEAL=colors.HexColor('#167e88'); GREY=colors.HexColor('#eef3f5')
PAGE_W,PAGE_H=A4; MARGIN=43; WIDTH=PAGE_W-2*MARGIN
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ManualBody',fontName='Helvetica',fontSize=9.1,leading=13,spaceAfter=6,textColor=INK))
styles.add(ParagraphStyle(name='ManualH1',fontName='Helvetica-Bold',fontSize=22,leading=26,spaceAfter=14,textColor=INK,keepWithNext=True))
styles.add(ParagraphStyle(name='ManualH2',fontName='Helvetica-Bold',fontSize=14,leading=18,spaceBefore=12,spaceAfter=8,textColor=TEAL,keepWithNext=True))
styles.add(ParagraphStyle(name='ManualH3',fontName='Helvetica-Bold',fontSize=10.5,leading=14,spaceBefore=9,spaceAfter=5,textColor=INK,keepWithNext=True))
styles.add(ParagraphStyle(name='ManualCell',fontName='Helvetica',fontSize=7.3,leading=10,textColor=INK))
styles.add(ParagraphStyle(name='ManualSmall',fontName='Helvetica',fontSize=7.5,leading=10,spaceAfter=6,textColor=INK))
styles.add(ParagraphStyle(name='ManualCode',fontName='Courier',fontSize=7,leading=10,backColor=GREY,borderPadding=6,spaceAfter=10))

def ascii_text(s):
    return str(s).translate(str.maketrans({'\u2013':'-','\u2014':' - ','\u2011':'-','\u2212':'-','\u00d7':' x ','\u00b1':'+/-','\u2264':'<=','\u2265':'>=','\u2192':' -> ','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u03a9':'ohm','\u00b5':'u','\u03bc':'u','\u0394':'Delta','\u03b8':'theta','\u00b0':' deg'}))

def rich(s):
    s=html.escape(ascii_text(s))
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',s)
    s=re.sub(r'\[([^]]+)\]\(([^)]+)\)',lambda m:f'<link href="{m[2]}">{m[1]}</link>',s)
    return s

def p(s,style='ManualBody'): return Paragraph(rich(s),styles[style])

def table(rows,widths=None):
    data=[[p(x,'ManualCell') for x in row] for row in rows]
    t=Table(data,colWidths=widths or [WIDTH/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREY),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d2dce1')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    return t

def image(path,width=WIDTH,height=260):
    with PILImage.open(path) as im: w,h=im.size
    scale=min(width/w,height/h)
    return Image(str(path),w*scale,h*scale)

def footer(c,doc):
    c.saveState();c.setStrokeColor(TEAL);c.line(MARGIN,34,PAGE_W-MARGIN,34)
    c.setFont('Helvetica',7);c.setFillColor(INK)
    c.drawString(MARGIN,23,'MIMIC R5a-E1 | Digital engineering package | Physical verification pending')
    c.drawRightString(PAGE_W-MARGIN,23,str(doc.page));c.restoreState()

def md_flow(text,root):
    """Small deterministic renderer for the authored Markdown subset."""
    lines=text.splitlines();out=[];i=0
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line: continue
        if line=='<!-- pagebreak -->':out.append(PageBreak());continue
        if line.startswith('```'):
            block=[]
            while i<len(lines) and not lines[i].strip().startswith('```'):
                raw=ascii_text(lines[i]);i+=1
                # Long commands stay complete in Markdown; PDF wraps for legibility.
                while len(raw)>106:
                    cut=raw.rfind(' ',0,104)
                    if cut<40: cut=104
                    block.append(raw[:cut]);raw='    '+raw[cut:].lstrip()
                block.append(raw)
            i+=1;out.append(Preformatted('\n'.join(block),styles['ManualCode']));continue
        im=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',line)
        if im:
            target=(root/'docs'/im[2]).resolve()
            if not target.exists():raise FileNotFoundError(target)
            out.append(image(target));out.append(p(im[1],'ManualSmall'));continue
        if line.startswith('|'):
            rows=[]
            while True:
                if not re.fullmatch(r'[|:\-\s]+',line):rows.append([x.strip() for x in line.strip('|').split('|')])
                if i>=len(lines) or not lines[i].strip().startswith('|'):break
                line=lines[i].strip();i+=1
            out.append(table(rows));out.append(Spacer(1,8));continue
        if line.startswith('# '):out.append(p(line[2:],'ManualH1'));continue
        if line.startswith('## '):out.append(p(line[3:],'ManualH2'));continue
        if line.startswith('### '):out.append(p(line[4:],'ManualH3'));continue
        if line.startswith('- '):out.append(p('• '+line[2:]));continue
        out.append(p(line))
    return out

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def csv_md(path,columns):
    rows=read_csv(path);headers=[label for key,label in columns]
    result=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    for row in rows:result.append('| '+' | '.join(str(row.get(key,'')).replace('|','/').replace('\n',' ') for key,label in columns)+' |')
    return '\n'.join(result)

def generate_hardware(root,d):
    rows=['Each quantity below counts one complete fastener/retention set described in that row, not one individual washer. Locations are assembly-coordinate reference points and the direction is the nominal fastener axis. Verify actual engagement, clearance and access during dry assembly. All physical fits remain unverified.','| Hardware ID | Qty | Complete set | Grip (mm) |','| --- | --- | --- | --- |']
    for h in d['hardware']:
        rows.append(f'| {h["id"]} | {h["qty"]} | {h["description"]} | {h.get("nominal_grip_mm","-")} |')
    rows+=['','## Installation and location schedule','The notes below come directly from the current hardware contract. Use these notes together with the numbered sequence; do not clamp a running pivot by tightening it like a structural bolt.']
    for h in d['hardware']:
        loc='; '.join('('+', '.join(f'{v:.2f}'.rstrip('0').rstrip('.') for v in xyz)+')' for xyz in h.get('location_mm',[]))
        axis=', '.join(str(v) for v in h.get('axis',[]))
        rows.extend([f'### {h["id"]}',f'{h["installation"]} Location(s) X,Y,Z: {loc}. Axis: ({axis}).'])
    (root/'docs/manual_hardware.md').write_text('\n\n'.join(rows[:1])+'\n\n'+'\n'.join(rows[1:]),encoding='utf-8')

def build_manual(root):
    d=json.loads((root/'bom/parts.json').read_text(encoding='utf-8'))
    generate_hardware(root,d)
    sections=[]
    intro=(root/'docs/manual_introduction.md').read_text(encoding='utf-8')
    sections.append(intro)
    parts=['<!-- pagebreak -->\n# 2. Printed components','The IDs below are generated from the final geometry contract. Quantities are assembly quantities; print extras only when the plate map explicitly identifies coupons or spares. STEP components retain assembly coordinates. Use the oriented 3MF files for printing.','| ID | Printed component | Qty |','| --- | --- | --- |']
    for row in d['parts']:parts.append(f'| {row["id"]} | {row["name"].replace("_"," ")} | {row["qty"]} |')
    sections.append('\n\n'.join(parts[:2])+'\n\n'+'\n'.join(parts[2:]))
    # Mechanical hardware is deliberately authored from the final assembly contract.
    sections.append('<!-- pagebreak -->\n# 3. Mechanical hardware\n\n'+(root/'docs/manual_hardware.md').read_text(encoding='utf-8'))
    sections.append('<!-- pagebreak -->\n# 4. Electrical BOM\n\nThe final actuator model, supply and fuse ratings are unresolved. Quantities and definitions below are purchasing/inspection requirements, not assertions that hardware is in hand.\n\n'+csv_md(root/'bom/electrical_BOM.csv',[('item_id','ID'),('quantity','Qty'),('description','Component'),('specification','Specification'),('status','Status')]))
    sections.append('<!-- pagebreak -->\n# 5. Print and inspect\n\n'+(root/'docs/printing.md').read_text(encoding='utf-8'))
    sections.append('## Quantity-complete plate map\n\nPrint each named plate once. The grouped plates already contain all BOM quantities, including the bench coupon; individual 3MFs are replacements and should not be added to this total.\n\n'+csv_md(root/'bom/PRINT_MAP.csv',[('plate','Plate'),('part_id','Part ID'),('name','Component'),('quantity','Qty'),('orientation','Rotation XYZ (deg)')]))
    plates=json.loads((root/'bom/plates.json').read_text(encoding='utf-8'))['plates']
    for plate in plates:
        sections.append(f'### {plate["id"]} arrangement\n\n![{plate["id"]} - labeled final plate arrangement](../renders/plates/{plate["id"]}.png)')
    sections.append('<!-- pagebreak -->\n# 6. Mechanical assembly\n\n'+(root/'docs/manual_mechanical.md').read_text(encoding='utf-8'))
    sections.append('<!-- pagebreak -->\n# Mechanical load and speed assessment\n\n'+(root/'docs/load_speed_assessment.md').read_text(encoding='utf-8'))
    sections.append('<!-- pagebreak -->\n# 7. Electrical installation\n\n'+(root/'docs/electronics.md').read_text(encoding='utf-8'))
    sections.append('<!-- pagebreak -->\n# 8. Flash, calibrate and commission\n\n'+(root/'firmware/README.md').read_text(encoding='utf-8'))
    sections.append('<!-- pagebreak -->\n# 9. Physical acceptance and maintenance\n\n'+(root/'docs/maintenance.md').read_text(encoding='utf-8'))
    text='\n\n'.join(sections)
    md=root/'docs/Assembly_Manual.md';md.write_text(text,encoding='utf-8')
    doc=SimpleDocTemplate(str(root/'docs/Assembly_Manual.pdf'),pagesize=A4,rightMargin=MARGIN,leftMargin=MARGIN,topMargin=42,bottomMargin=46,title='Mimic R5a-E1 Assembly and Commissioning Manual',author='Mimic engineering release')
    doc.build(md_flow(text,root),onFirstPage=footer,onLaterPages=footer)

def build_drawings(root):
    index=json.loads((root/'docs/drawings/index.json').read_text(encoding='utf-8'))
    target=root/'docs/Mechanical_Drawings.pdf';c=canvas.Canvas(str(target),pagesize=landscape(A4));w,h=landscape(A4)
    c.setTitle('Mimic R5a-E1 Mechanical Reference Drawings');c.setAuthor('Mimic engineering release')
    for n,row in enumerate(index,1):
        drawing=svg2rlg(str(root/row['drawing']))
        if drawing is None:raise ValueError(f'Cannot read drawing {row}')
        scale=min((w-36)/drawing.width,(h-46)/drawing.height);drawing.scale(scale,scale)
        renderPDF.draw(drawing,c,18,30)
        c.setFont('Helvetica',7);c.drawString(22,15,'R5a-E1 | Reference geometry; fits and acceptance requirements in Assembly Manual')
        c.drawRightString(w-22,15,f'{n}/{len(index)}');c.showPage()
    c.save()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',default='.');ap.add_argument('--manual-only',action='store_true');a=ap.parse_args();root=Path(a.release).resolve()
    build_manual(root)
    if not a.manual_only:build_drawings(root)
    print('Generated Assembly_Manual.md, Assembly_Manual.pdf'+('' if a.manual_only else ', Mechanical_Drawings.pdf'))
if __name__=='__main__':main()
