"""Generate the round Flux WFF face using the Dolomite palette and gallery masks."""
import json
from itertools import count
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dolomite import dynamic_colors

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
backgrounds,foregrounds=dynamic_colors()
palettes.append(reference)
# Unique pair identifies the dynamic selection in WFF regardless of locale.
palettes[0]=[backgrounds[0], backgrounds[7], foregrounds[0], foregrounds[7]]
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
config=add(face,'UserConfigurations')
colors=add(config,'ColorConfiguration',id='palette',displayName='color',defaultValue=0)
for i,pal in enumerate(palettes):
    add(colors,'ColorOption',id=i,displayName=f'p{i}',colors=' '.join(map(argb,pal)))
cfg=add(config,'ListConfiguration',id='numerals',displayName='numerals',defaultValue='western')
for script in scripts:
    add(cfg,'ListOption',id=script,displayName=script)
scene=add(face,'Scene',backgroundColor='#000000')
def choices(parent,items):
    block=add(parent,'Condition')
    ex=add(block,'Expressions')
    for key,expr in items: add(ex,'Expression',name=key).text=expr
    return block

def digits(parent,ambient=False):
    cfg=add(parent,'ListConfiguration',id='numerals')
    # Phase zero is the resting outline. The 16 transition samples straddle :00.
    frame='0' if ambient else '(clamp(floor(([SECOND_MILLISECOND] - 59.875)*64 + 0.5),0,8) + clamp(1 - floor([SECOND_MILLISECOND]*8),0,1)*(9 + floor([SECOND_MILLISECOND]*64)))'
    index=f'([MINUTE]*17+{frame})'
    alphabet=''.join(chr(0xe000+i) for i in range(60*17))
    for script in scripts:
        opt=add(cfg,'ListOption',id=script)
        items=[]
        for mode,count_hours in enumerate((24,12)):
            for h in range(count_hours):
                expr=f'[IS_24_HOUR_MODE] && [HOUR_0_23]=={h}' if mode==0 else f'!([IS_24_HOUR_MODE]) && [HOUR_1_12]=={h+1}'
                items.append((f'h{mode}_{h}',expr))
        cond=choices(opt,items)
        for key,_ in items:
            branch=add(cond,'Compare',expression=key)
            part=add(branch,'PartText',**box(30,22,420,436))
            text=add(part,'Text',align='CENTER')
            font=add(text,'Font',family=f'flux_{script}_{key[1:]}' + ('a' if ambient else ''),size=410,color='#FF707070' if ambient else '#FFFFFFFF')
            template=add(font,'Template')
            template.text='%s'
            add(template,'Parameter',expression=f'subText("{alphabet}",{index},{index}+1)')

def split(parent,upper,lower):
    rect(parent,upper)
    part=rect(parent,lower)
    transform(part,'y','480 - [SECOND_MILLISECOND]*8')

def paint(parent,foreground):
    # setPalette: uses display-hour (including the 12-hour conversion) and dayOfYear.
    hour='([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])'
    ix=f'(([DAY_OF_YEAR]*11+{hour}*60+[MINUTE])%14)'
    dynamic=f'{ink(0)} == {argb(palettes[0][0])} && {ink(1)} == {argb(palettes[0][1])}'
    cond=choices(parent,[('dynamic',dynamic)])
    options=choices(add(cond,'Compare',expression='dynamic'),[(f'c{i}',f'{ix}=={i}') for i in range(14)])
    table=foregrounds if foreground else backgrounds
    for i in range(14):
        split(add(options,'Compare',expression=f'c{i}'),argb(table[i]),argb(table[(i+1)%14]))
    fixed=choices(add(cond,'Default'),[('even','[MINUTE]%2 == 0')])
    j=2 if foreground else 0
    split(add(fixed,'Compare',expression='even'),ink(j),ink(j+1))
    split(add(fixed,'Default'),ink(j+1),ink(j))

active=group(scene)
add(active,'Variant',mode='AMBIENT',target='alpha',value=0)
paint(active,False)
text_layer=group(active)
paint(text_layer,True)
digits(group(text_layer,renderMode='MASK'))
ambient=group(scene,alpha=0)
add(ambient,'Variant',mode='AMBIENT',target='alpha',value=255)
digits(ambient,True)
save(res/'raw/watchface.xml',face)
for loc in props.glob('*.lproj'):
    labels=load(loc/'Localizable.strings.json')
    colorlabels=load(loc/'FaceColors.strings.json')
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    base=res.parent.parent/'Flow/res'/('values'+suffix)/'strings.xml'
    if not base.exists(): continue
    color=ET.parse(base).find("string[@name='color']").text
    strings={'face_name':labels['FACE_STYLE_DOLOMITE_IN_TITLE_CASE'],'numerals':labels['EDIT_MODE_LABEL_NUMERAL'],'color':color,'p0':colorlabels['dynamic'],'p15':'10:09'}
    strings.update({k:labels['EDIT_OPTION_LABEL_NUMERAL_'+v[2]] for k,v in scripts.items()})
    strings.update({f'p{i+1}':colorlabels[f'color{i:02d}'] for i in range(14)})
    t=ET.Element('resources')
    for k,v in strings.items(): add(t,'string',name=k).text=v.replace("'","\\'")
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save(res/('values'+s)/'strings.xml',t)
# The same static font used on the watch supplies the picker preview.
font=ImageFont.truetype(str(res/'font/flux_western_0_10.otf'),410)
mask=Image.new('L',(480,480))
ImageDraw.Draw(mask).text((35,445),chr(0xe000+9*17),font=font,fill=255,anchor='ls')
preview=Image.new('RGB',(480,480),reference[0])
pigment=Image.new('RGB',preview.size,reference[2])
for layer,color in ((preview,reference[1]),(pigment,reference[3])):
    ImageDraw.Draw(layer).rectangle((0,240,479,479),fill=color)
preview.paste(pigment,mask=mask)
circle=Image.new('L',preview.size)
ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255)
preview.putalpha(circle)
preview.save(draw/'preview.png')
