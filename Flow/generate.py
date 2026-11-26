"""Build Flow for a round Wear OS screen from watchOS 24S132 and the Apple gallery reference."""
from pathlib import Path
from io import BytesIO
import json
import os
import struct
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
FW=ROOT.parent/'Watch8_5_24S132/解析'
if os.name=='nt':
    FW=Path('\\\\?\\'+str(FW))
BUNDLE='NTKWarlockFaceBundle'
PROPS=FW/'属性表/System/Library/NanoTimeKit/FaceBundles'/f'{BUNDLE}.bundle'
CORE=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
CAT=FW/'图集'/CORE/'Assets.car/资源'
DRAW=ROOT/'res/drawable-nodpi'
DRAW.mkdir(exist_ok=True,parents=True)
REF=Image.open(ROOT.parent/'表盘资料/流动/官方图1.png').convert('RGB')

def read(p):
    return json.loads(p.read_text('utf8'))
def add(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
def box(x,y,w,h):
    return dict(x=x,y=y,width=w,height=h)
def xml(p,t):
    p.parent.mkdir(exist_ok=True,parents=True)
    ET.indent(t)
    ET.ElementTree(t).write(p,encoding='utf-8',xml_declaration=True)
def group(p,name):
    return add(p,'Group',name=name,**box(0,0,480,480))
def picture(p,name,x,y,w,h):
    add(add(p,'PartImage',**box(x,y,w,h)),'Image',resource=name)
def switch(parent):
    c=add(parent,'Condition')
    return c,add(c,'Expressions')
def case(c,expr,key,test):
    add(expr,'Expression',name=key).text=test
    return add(c,'Compare',expression=key)
def hexcode(rgb):
    return '#FF'+''.join(f'{int(ch):02X}' for ch in rgb)
def version(g,is_ambient):
    g.set('alpha','0' if is_ambient else '255')
    add(g,'Variant',mode='AMBIENT',target='alpha',value=255 if is_ambient else 0)

def source_fonts():
    b=(FW/'代码'/BUNDLE/BUNDLE).read_bytes()
    off=32
    for _ in range(struct.unpack_from('<I',b,16)[0]):
        cmd,n=struct.unpack_from('<II',b,off)
        if cmd==25:
            for j in range(struct.unpack_from('<I',b,off+64)[0]):
                sect,seg,_,size,pos=struct.unpack_from('<16s16sQQI',b,off+72+j*80)
                if b'__FONT_DATA' in seg:
                    yield ('stencil' if b'Stencil' in sect else 'solid'),b[pos:pos+size]
        off+=n

# Interpolate a curved color boundary fitted to the exposed background of the gallery image.
# Interior samples are brighter than exterior samples because of the original glass material.
coords=[(366,220),(374,133),(375,125),(372,114),(59,180)]
palettes=[('gallery',[REF.getpixel(p) for p in coords])]
for name in ('red','orange','turquoise','lightBlue','midnightBlue','lavender','vintageRose'):
    key='seasons.fall2015.'+name
    stem=key.replace('.','_')
    def pigment(suffix):
        c=read(next(CAT.glob(stem+suffix+'-*.json')))['Components'][:3]
        return np.uint8(np.clip(np.array(c)*255,0,255).round())
    dark,base,light=(pigment(s) for s in ('_seasonalDark','','_seasonalLight'))
    palettes.append((key,[dark,(dark*.40+base*.60).round(),base,light,(light*.72+np.array([255,255,255])*.28).round()]))

axis=np.linspace(-110,590,464)
y,x=np.meshgrid(axis,axis,indexing='ij')
def field(colors,lens):
    xx=x
    yy=y
    angle=np.arctan2(yy-275,xx-475)
    radius=np.hypot((xx-475)/323,(yy-275)/155)
    phase=radius+0.13*np.sin(2*angle+0.5)+0.075*np.cos(3*angle-0.75)
    stops=[0.65,0.97,1.00,1.075,1.32]
    ramp=np.array(colors,float)
    if lens:
        ramp=np.minimum(255,ramp*1.22+11)
        # Keep the interior on the same color boundary; local refraction is applied at the rim.
    return Image.fromarray(np.uint8(np.stack([np.interp(phase,stops,ramp[:,i]) for i in range(3)],axis=-1)).round())

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
user=add(face,'UserConfigurations')
cc=add(user,'ColorConfiguration',id='palette',displayName='color',defaultValue='0')
for i,(_,ramp) in enumerate(palettes):
    add(cc,'ColorOption',id=i,displayName=f'p{i}',colors=' '.join(hexcode(ramp[k]) for k in (0,3,4)))
    for material in ('field','glass'):
        field(ramp,material=='glass').save(DRAW/f'{material}_{i}.png')
for key,options in [('typeface',['stencil','solid']),('background',['on','off'])]:
    conf=add(user,'ListConfiguration',id=key,displayName=key,defaultValue=options[0])
    for opt in options:add(conf,'ListOption',id=opt,displayName=opt)

W,H=144,160
directions={'left':(-6,0),'right':(6,0),'up':(0,-6),'down':(0,6)}
fonts=add(face,'BitmapFonts')
for style,blob in source_fonts():
    font=ImageFont.truetype(BytesIO(blob),640)
    masks=[]
    for digit in range(10):
        layer=Image.new('L',(700,850))
        ImageDraw.Draw(layer).text((40,0),str(digit),font=font,fill=255)
        masks.append(layer.crop(layer.getbbox()))
    scale=min((W-6)/max(im.width for im in masks),(H-4)/max(im.height for im in masks))
    bf=add(fonts,'BitmapFont',name=style)
    bevel_fonts={k:add(fonts,'BitmapFont',name=style+'_'+k) for k in directions}
    for n,m in enumerate(masks):
        m=m.resize((round(m.width*scale),round(m.height*scale)),Image.Resampling.LANCZOS)
        tile=Image.new('L',(W,H))
        tile.paste(m,((W-m.width)//2,(H-m.height)//2))
        img=Image.new('RGBA',tile.size,'white')
        img.putalpha(tile)
        name=f'{style}_{n}'
        img.save(DRAW/(name+'.png'))
        for offset in (48,0x660,0x6f0,0x966):add(bf,'Character',name=chr(offset+n),resource=name,width=W,height=H)
        # Directional specular ridges follow both the outer silhouettes and internal cutouts.
        a=np.asarray(tile,dtype=float)/255
        soft=np.asarray(tile.filter(ImageFilter.GaussianBlur(2)),dtype=float)/255
        dy,dx=np.gradient(soft)
        broad=np.asarray(tile.filter(ImageFilter.GaussianBlur(5)),dtype=float)/255
        gy,gx=np.gradient(broad)
        for key,(ox,oy) in directions.items():
            weight=a*np.clip((gx*ox+gy*oy)*2.2,0,1)
            bevel=Image.new('RGBA',(W,H),'white')
            bevel.putalpha(Image.fromarray(np.uint8(255*weight)))
            asset=name+'_'+key
            bevel.save(DRAW/(asset+'.png'))
            for offset in (48,0x660,0x6f0,0x966):
                add(bevel_fonts[key],'Character',name=chr(offset+n),resource=asset,width=W,height=H)
        normal=np.clip(5*(dx+dy),-1,1)
        edge=np.clip(7*np.hypot(dx,dy),0,1)
        rgb=np.where(normal[:,:,None]>=0,np.array([255,233,255]),np.array([144,127,255]))
        rim=np.dstack([rgb,255*a*edge*(.43+.49*np.abs(normal))])
        Image.fromarray(rim.astype('uint8')).save(DRAW/f'{name}_edge.png')

scene=add(face,'Scene',backgroundColor='#000000')
active=group(scene,'interactive')
version(active,False)
def moving(parent,material):
    g=group(parent,material+'_motion')
    # WFF evaluates the motion input independently of minute ticks.
    f=1  # Shared orientation, pivot and translation for every optical layer.
    add(g,'Gyro',angle=f'clamp([ACCELEROMETER_ANGLE_X], -65, 65) * {f}',
        x=f'clamp([ACCELEROMETER_ANGLE_Y], -55, 55) * {f*.52}',
        y=f'clamp([ACCELEROMETER_ANGLE_X], -55, 55) * {-f*.24}')
    c,e=switch(g)
    for i,(_,ramp) in enumerate(palettes):
        p=case(c,e,'p'+str(i),f'[CONFIGURATION.palette.0] == {hexcode(ramp[0])} && [CONFIGURATION.palette.1] == {hexcode(ramp[3])}')
        picture(p,f'{material}_{i}',-110,-110,700,700)
bg=add(active,'ListConfiguration',id='background')
moving(add(bg,'ListOption',id='on'),'field')
group(add(bg,'ListOption',id='off'),'black')
def layouts(parent):
    cfg=add(parent,'ListConfiguration',id='typeface')
    for style in ('solid','stencil'):
        yield style,group(add(cfg,'ListOption',id=style),style)
def clocks(g,style,color):
    for row,y0 in [('hh',72),('mm',248)]:
        c=add(g,'DigitalClock',**box(96,y0,W*2,H))
        t=add(c,'TimeText',**box(0,0,W*2,H),format=row,align='CENTER')
        add(t,'BitmapFont',family=style,size=H,color=color)
glass=group(active,'refracted_color')
moving(glass,'glass')
mask=group(glass,'digits')
mask.set('renderMode','MASK')
for style,g in layouts(mask):clocks(g,style,'#FFFFFFFF')
# Only the narrow, sloping bevel samples a neighboring point of the moving field.
# Offsets are in screen space and are bounded irrespective of wrist angle.
for key,(ox,oy) in directions.items():
    bevel=group(active,'bevel_'+key)
    light=group(bevel,'sample_'+key)
    light.set('x',str(ox))
    light.set('y',str(oy))
    moving(light,'glass')
    mask=group(bevel,'normal_'+key)
    mask.set('renderMode','MASK')
    for style,g in layouts(mask):
        clocks(g,style+'_'+key,'#FFFFFFFF')
for style,g in layouts(active):
    for row,(val,y0) in enumerate([('([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])',72),('[MINUTE]',248)]):
        for col,x0 in enumerate([96,240]):
            c,e=switch(g)
            for n in range((3 if row==0 else 6) if col==0 else 10):
                expr=f'floor({val}/10)' if col==0 else f'({val}%10)'
                p=case(c,e,'n'+str(n),expr+' == '+str(n))
                picture(p,f'{style}_{n}_edge',x0,y0,W,H)
ambient=group(scene,'always_on')
version(ambient,True)
for style,g in layouts(ambient):
    g.set('alpha','85')
    clocks(g,style,'[CONFIGURATION.palette.2]')
xml(ROOT/'res/raw/watchface.xml',face)

# Render the 10:09 thumbnail from the same layers, with the watch held still.
def centered(material):
    return Image.open(DRAW/f'{material}_0.png').resize((700,700),Image.Resampling.LANCZOS).crop((110,110,590,590)).convert('RGBA')
preview=centered('field')
glass_image=centered('glass')
for n,x0,y0 in [(1,96,72),(0,240,72),(0,96,248),(9,240,248)]:
    rect=(x0,y0,x0+W,y0+H)
    preview.paste(glass_image.crop(rect),(x0,y0),Image.open(DRAW/f'stencil_{n}.png').getchannel('A'))
    for key,(ox,oy) in directions.items():
        sample=glass_image.crop((x0-ox,y0-oy,x0+W-ox,y0+H-oy))
        preview.paste(sample,(x0,y0),Image.open(DRAW/f'stencil_{n}_{key}.png').getchannel('A'))
    preview.alpha_composite(Image.open(DRAW/f'stencil_{n}_edge.png'),(x0,y0))
circle=Image.new('L',(480,480))
ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255)
preview.putalpha(circle)
preview.save(DRAW/'preview.png')
for loc in PROPS.glob('*.lproj'):
    l={}
    for p in loc.glob('*.json'):l.update(read(p))
    cd=FW/'属性表'/CORE/loc.name
    ref=read(cd/'ClockFaces.strings.json')
    names=read(cd/'FaceColors.strings.json')
    data={'face_name':l['WARLOCK_FACE_NAME'],'color':ref['EDIT_MODE_LABEL_COLOR'],
          'typeface':ref['EDIT_MODE_LABEL_TYPEFACE'],'background':ref.get('EDIT_MODE_LABEL_BACKGROUND',{'zh_CN':'背景','zh_HK':'背景','zh_TW':'背景'}.get(loc.stem,'Background'))}
    for item in ['TYPEFACE_STENCIL','TYPEFACE_SOLID','BACKGROUND_ON','BACKGROUND_OFF']:
        data[item.split('_')[1].lower()]=l['WARLOCK_EDIT_OPTION_'+item]
    for i,(k,_) in enumerate(palettes):data['p'+str(i)]=names.get(k,'10:09' if i==0 else k.split('.')[-1])
    tree=ET.Element('resources')
    for k,v in data.items():add(tree,'string',name=k).text=v.replace("'","\\'")
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        xml(ROOT/f'res/values{q}/strings.xml',tree)
