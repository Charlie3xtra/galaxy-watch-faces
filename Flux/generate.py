"""Generate the round Flux WFF face using the Dolomite palette and gallery masks."""
import json
from itertools import count
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FW = ROOT.parent / 'Watch8_5_24S132/解析'
bundle = Path('System/Library/NanoTimeKit/FaceBundles/NTKDolomiteFaceBundle.bundle')
assets = FW/'图集'/bundle/'Assets.car/资源'
props = FW/'属性表'/bundle
res = ROOT/'res'
draw = res/'drawable-nodpi'
gallery = Image.open(ROOT.parent/'表盘资料/流转/官方图1.png').convert('RGB')
def load(p):
    return json.loads(p.read_text('utf8'))
group_ids = count()
def add(p,tag,**kw):
    if tag=="Group": kw["name"]=f"group_{next(group_ids)}"
    return ET.SubElement(p,tag,{k:str(v) for k,v in kw.items()})
def save(p,t):
    p.parent.mkdir(exist_ok=True,parents=True)
    ET.indent(t)
    ET.ElementTree(t).write(p,encoding='utf-8',xml_declaration=True)
def box(x=0,y=0,w=480,h=480):
    return dict(x=x,y=y,width=w,height=h)
def group(p,**kw):
    return add(p,'Group',**box(),**kw)
def transform(p,attr,expr):
    add(p,'Transform',target=attr,value=expr)
def rect(p,color):
    part=add(p,'PartDraw',**box())
    add(add(part,'Rectangle',**box()),'Fill',color=color)
    return part
def argb(rgb):
    return '#FF'+''.join(f'{v:02X}' for v in rgb)
def ink(i):
    return f'[CONFIGURATION.palette.{i}]'
reference=[gallery.getpixel(p) for p in [(52,210),(52,260),(148,150),(148,254)]]
palettes=[reference]
for i in range(14):
    palette=[]
    for component in ('northColor','southColor','digitNorthColor','digitSouthColor'):
        file=next(assets.glob(f'dolomite_color{i:02d}_{component}-*.json'))
        palette.append(tuple(np.rint(np.clip(load(file)['Components'][:3],0,1)*255).astype(int)))
    palettes.append(palette)
scripts={'western':(48,'bahnschrift.ttf','ARABIC'),'eastern':(0x660,'tahomabd.ttf','ARABIC_INDIC'),'deva':(0x966,'Nirmala.ttc','DEVANAGARI')}
masks={}
for script,(offset,fontname,_) in scripts.items():
    font=ImageFont.truetype(str(Path('C:/Windows/Fonts')/fontname),340)
    for digit in range(10):
        if script=='western' and digit in (0,1,9):
            bounds={0:(177,67,353,196),1:(69,66,167,273),9:(177,207,353,419)}[digit]
            pixels=np.asarray(gallery.crop(bounds),dtype=float)
            # Recover alpha from each row's two sampled foreground/background colors.
            a=np.empty(pixels.shape[:2])
            for row,rgb in enumerate(pixels):
                side=int(bounds[1]+row>=243)
                bg=np.array(reference[side]); delta=np.array(reference[2+side])-bg
                a[row]=np.clip((rgb-bg)@delta/(delta@delta),0,1)
            # The gallery swipe boundary covers two antialiased scan lines.
            stripe=242-bounds[1]
            if 1 <= stripe < len(a)-2: a[stripe:stripe+2]=(a[stripe-1]+a[stripe+2])*.5
            mask=Image.fromarray(np.uint8(255*a))
        else:
            char=chr(offset+digit)
            x,y,r,b=font.getbbox(char)
            mask=Image.new('L',(r-x,b-y))
            ImageDraw.Draw(mask).text((-x,-y),char,fill=255,font=font)
        mask=mask.resize((180,206),Image.Resampling.LANCZOS)
        masks[script,digit]=mask
        img=Image.new('RGBA',mask.size,'white')
        img.putalpha(mask)
        img.save(draw/f'{script}_{digit}.png')
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
config=add(face,'UserConfigurations')
colors=add(config,'ColorConfiguration',id='palette',displayName='color',defaultValue=0)
for i,pal in enumerate(palettes):
    add(colors,'ColorOption',id=i,displayName=f'p{i}',colors=' '.join(map(argb,pal)))
cfg=add(config,'ListConfiguration',id='numerals',displayName='numerals',defaultValue='western')
for script in scripts:
    add(cfg,'ListOption',id=script,displayName=script)
scene=add(face,'Scene',backgroundColor='#000000')
hour='([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])'
values=[f'floor({hour}/10)',f'({hour}%10)','[MINUTE_TENS_DIGIT]','[MINUTE_UNITS_DIGIT]']
def digits(parent,color,ambient=False):
    # Two independent column splits emulate the unequal digit boxes of the gallery.
    parity='([MINUTE]%2)'
    q=parity if ambient else f'({parity} + (1-2*{parity})*pow(1-clamp([SECOND_MILLISECOND]*2,0,1),3))'
    left=f'(130+33*{q})'
    for i,value in enumerate(values):
        right=i%2
        top=i<2
        cut=f'(159+{24 if right else -24}*(2*{q}-1))'
        height=cut if top else f'(310-{cut})'
        width=f'(310-{left})' if right else left
        g=add(parent,'Group',**box(0,0,180,206),pivotX='0',pivotY='0')
        for attr,expr in [('x',f'(75+{left}+20)' if right else '75'),('y','75' if top else f'(75+{cut}+20)'),('scaleX',f'{width}/180'),('scaleY',f'{height}/206')]:
            transform(g,attr,expr)
        cfg=add(g,'ListConfiguration',id='numerals')
        for script in scripts:
            opt=add(cfg,'ListOption',id=script)
            cond=add(opt,'Condition')
            expressions=add(cond,'Expressions')
            for n in range((3,10,6,10)[i]):
                add(expressions,'Expression',name=f'd{n}').text=f'{value} == {n}'
                part=add(add(cond,'Compare',expression=f'd{n}'),'PartImage',**box(0,0,180,206),tintColor=color)
                add(part,'Image',resource=f'{script}_{n}')
active=group(scene)
add(active,'Variant',mode='AMBIENT',target='alpha',value=0)
parity=add(active,'Condition')
ex=add(parity,'Expressions')
add(ex,'Expression',name='even').text='[MINUTE]%2 == 0'
for side in (0,1):
    stage=add(parity,'Compare',expression='even') if side==0 else add(parity,'Default')
    rect(stage,ink(side))
    digits(stage,ink(2+side))
    sweep=group(stage)
    rect(sweep,ink(1-side))
    digits(sweep,ink(3-side))
    mask=group(sweep,renderMode='MASK')
    transform(rect(mask,'#FFFFFF'),'y','480 - [SECOND_MILLISECOND]*8')
ambient=group(scene,alpha=0)
add(ambient,'Variant',mode='AMBIENT',target='alpha',value=255)
digits(ambient,'#FF707070',True)
save(res/'raw/watchface.xml',face)
for loc in props.glob('*.lproj'):
    labels=load(loc/'Localizable.strings.json')
    colorlabels=load(loc/'FaceColors.strings.json')
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    base=res.parent.parent/'Flow/res'/('values'+suffix)/'strings.xml'
    if not base.exists(): continue
    color=ET.parse(base).find("string[@name='color']").text
    strings={'face_name':labels['FACE_STYLE_DOLOMITE_IN_TITLE_CASE'],'numerals':labels['EDIT_MODE_LABEL_NUMERAL'],'color':color,'p0':'10:09'}
    strings.update({k:labels['EDIT_OPTION_LABEL_NUMERAL_'+v[2]] for k,v in scripts.items()})
    strings.update({f'p{i+1}':colorlabels[f'color{i:02d}'] for i in range(14)})
    t=ET.Element('resources')
    for k,v in strings.items(): add(t,'string',name=k).text=v.replace("'","\\'")
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save(res/('values'+s)/'strings.xml',t)
# Picker thumbnail shows the gallery phase, using the same digit masks and split coordinates.
preview=Image.new('RGB',(480,480),reference[0])
ImageDraw.Draw(preview).rectangle((0,240,479,479),fill=reference[1])
for digit,x,y,w,h in [(1,75,75,130,183),(0,225,75,180,135),(0,75,278,130,127),(9,225,230,180,175)]:
    m=masks['western',digit].resize((w,h),Image.Resampling.LANCZOS)
    pigment=Image.new('RGB',(w,h),reference[2])
    if y+h>240: ImageDraw.Draw(pigment).rectangle((0,max(0,240-y),w,h),fill=reference[3])
    preview.paste(pigment,(x,y),m)
circle=Image.new('L',preview.size)
ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255)
preview.putalpha(circle)
preview.save(draw/'preview.png')
