from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from html import escape
root=Path(__file__).resolve().parents[2]
W,H=1800,1340
im=Image.new('RGB',(W,H),'#f6f8fb');d=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="#f6f8fb"/>']
fontpath='C:/Windows/Fonts/segoeui.ttf';boldpath='C:/Windows/Fonts/segoeuib.ttf'
def box(x,y,w,h,fill='#ffffff',stroke='#b5c3d1'):
 d.rounded_rectangle((x,y,x+w,y+h),radius=12,fill=fill,outline=stroke,width=2)
 svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
def text(x,y,s,size=24,color='#183247',bold=False):
 font=ImageFont.truetype(boldpath if bold else fontpath,size)
 d.text((x,y),s,font=font,fill=color)
 svg.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(s)}</text>')
def line(points,color='#183247',width=4):
 d.line(points,fill=color,width=width)
 svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')
def labelbox(x,y,w,h,title,lines):
 box(x,y,w,h);text(x+18,y+15,title,25,bold=True)
 for n,s in enumerate(lines):text(x+18,y+55+30*n,s,21)
text(45,25,'MIMIC R5a  |  Power + signal wiring',38,bold=True)
text(45,78,'Revision 1.0.0  •  Net diagram, not board connector placement  •  Physical verification pending',23)
text(50,125,'1  ACTUATOR POWER — separate from logic and audio',27,bold=True)
labelbox(50,180,230,145,'Servo supply',['Regulated DC','Voltage/current TBD','Nominal 5 V scenario'])
labelbox(340,180,205,145,'Main DC fuse',['Near source','Value pending','wire/current review'])
labelbox(605,180,220,145,'DC disconnect',['DC-rated maintained','switch / contactor','Accessible to operator'])
labelbox(885,180,300,145,'Fused distribution',['5 protected branches','Bulk C: 1000 µF start','Capacitor ≥10 V'])
labelbox(1260,180,490,145,'Five servo power pairs',['Each + from its fused branch','Each return directly to distribution','No motor current through ESP32/PCA'])
for start,end in [(280,340),(545,605),(825,885),(1185,1260)]:line([(start,250),(end,250)],'#c8463b',6)
line([(165,325),(165,385),(1500,385),(1500,325)],'#465363',6)
line([(1035,325),(1035,335),(1185,335),(1185,385)],'#465363',6)
text(400,340,'COMMON GROUND: servo returns + logic reference + audio return',22,color='#465363')
text(50,410,'PCA V+ is UNCONNECTED here. Split servo harnesses take + directly from the protected distribution.',23,bold=True)
text(50,472,'2  LOGIC / I2C — classic ESP32-WROOM-32',27,bold=True)
box(50,530,260,485,fill='#e8f1fa');box(650,530,290,485,fill='#e8f1fa')
text(75,550,'ESP32',31,bold=True);text(675,550,'PCA9685',31,bold=True)
text(75,590,'USB logic supply',21);text(675,590,'Address 0x40',21)
signals=[(655,'GPIO21','SDA','#ae8100'),(720,'GPIO22','SCL','#31856a'),(785,'GPIO27','OE (active LOW)','#8b5cb3'),(875,'3V3','VCC only','#2a73b9'),(955,'GND','GND','#465363')]
for y,left,right,col in signals:
 text(75,y-18,left,25,bold=True);text(675,y-18,right,23,bold=True);line([(310,y),(650,y)],col,4)
text(345,625,'I2C 100 kHz',21)
text(345,740,'External 1 kΩ pull-up',21,color='#8b5cb3')
line([(440,785),(440,820)],'#8b5cb3',3)
box(421,820,38,35,fill='#fff',stroke='#8b5cb3')
line([(440,855),(440,875)],'#2a73b9',3)
text(482,818,'OE → 3V3',20)
text(345,918,'To common reference',20)
box(50,1040,890,235,fill='#fff5e5',stroke='#d49c3c')
text(70,1055,'Startup and fault behavior',25,bold=True)
for i,s in enumerate(['OE HIGH disables pulses; it does not remove servo power.',
 'External pull-up keeps outputs disabled during ESP32 reset.',
 'Default calibration is locked. Identify servos and supply first.',
 'PCA V+ remains unconnected; do not bridge it to 3V3.',
 'Support gravity loads. Verify rail discharge before servicing.']):text(70,1100+i*31,s,22)
box(1000,470,750,345)
text(1020,490,'3  SERVO SIGNALS',27,bold=True)
for i,s in enumerate(['CH0  →  linked eye yaw','CH1  →  jaw','CH2  →  linked eye pitch',
                      'CH3  →  left upper eyelid','CH4  →  right upper eyelid']):text(1030,540+i*36,s,25)
text(1020,742,'Signal from PCA; servo +/return from distribution.',22)
text(1020,777,'Confirm connector pin order on the actual hardware.',21)
box(1000,840,750,435)
text(1020,855,'4  AUDIO — hardware reservations only',26,bold=True)
for i,s in enumerate(['GPIO26 → INMP441 SCK + MAX98357A BCLK',
 'GPIO25 → INMP441 WS + MAX98357A LRC',
 'INMP441 SD → GPIO34; L/R → GND',
 'INMP441 VDD → 3V3; GND → common reference',
 'GPIO32 → MAX98357A DIN',
 'MAX98357A VIN → clean fused 5 V audio branch',
 'Speaker between OUT+ and OUT−; neither to GND',
 'Confirm amplifier SD / GAIN straps on actual module.',
 'Original voice source absent; no audio test claimed.']):text(1020,905+i*37,s,22)
text(50,1295,'Read docs/electronics.md and firmware/README.md before energizing. Fuse, wire, supply and servo identities remain measurement holds.',21)
svg.append('</svg>')
(root/'renders/wiring.svg').write_text('\n'.join(svg),encoding='utf-8')
im.save(root/'renders/wiring.png')
print('Wrote wiring.svg and wiring.png',im.size)
