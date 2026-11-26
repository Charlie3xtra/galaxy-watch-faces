"""Generate Nike Hybrid WFF from the 24S132 Olympus and NanoTimeKit resources."""
import json
import math
import corners
import struct
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132/解析'
core=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
catalog=fw/'图集'/core/'Assets.car/资源'
local=fw/'属性表/System/Library/NanoTimeKit/FaceBundles/NTKOlympusFaceBundle.bundle'
res=root/'res'
draw=res/'drawable-nodpi'
def read(p): return json.loads(p.read_text('utf8'))
def add(p,tag,**attrs): return ET.SubElement(p,tag,{k:str(v) for k,v in attrs.items()})
def box(x=0,y=0,w=480,h=480): return dict(x=x,y=y,width=w,height=h)
def save(p,t):
    p.parent.mkdir(exist_ok=True,parents=True)
    ET.indent(t)
    ET.ElementTree(t).write(p,encoding='utf-8',xml_declaration=True)
def group(p,name): return add(p,'Group',name=name,**box())
def image(p,name,x,y,w,h,color):
    part=add(p,'PartImage',**box(x,y,w,h),tintColor=color)
    add(part,'Image',resource=name)
    return part
def transform(p,target,value): add(p,'Transform',target=target,value=value)
def paint(p,color):
    d=add(p,'PartDraw',**box())
    add(add(d,'Rectangle',**box()),'Fill',color=color)
def rgb(name):
    v=read(next(catalog.glob(name+'-*.json')))['Components']
    if len(v)==2:v=v[:1]*3+v[1:]
    return '#FF'+''.join(f'{max(0,min(255,round(c*255))):02X}' for c in v[:3])
def rgbtuple(s): return tuple(bytes.fromhex(s[-6:]))
binary=(fw/'代码/NanoTimeKit/NanoTimeKit').read_bytes()
offset=32
fonts={}
for _ in range(struct.unpack_from('<I',binary,16)[0]):
    typ,size=struct.unpack_from('<II',binary,offset)
    if typ==25:
        for k in range(struct.unpack_from('<I',binary,offset+64)[0]):
            name,seg,_,length,pos=struct.unpack_from('<16s16sQQI',binary,offset+72+80*k)
            if name.startswith(b'__VictoryFont'):
                f=ImageFont.truetype(BytesIO(binary[pos:pos+length]),350)
                fonts['outline' if 'outline' in ' '.join(f.getname()).lower() else 'solid']=f
    offset+=size
assert set(fonts)=={'solid','outline'}
swoosh=Image.open(next(catalog.glob('*Nike-Hybrid-Swoosh*.png'))).convert('RGBA')
im=Image.new('RGBA',swoosh.size,'white');im.putalpha(swoosh.getchannel('A'));im.save(draw/'swoosh.png')
# Use one scale across rows and times; center on the visible ink, including italic overhang.
for style,font in fonts.items():
    scale=131/(font.getbbox('0')[3]-font.getbbox('0')[1])
    for n in range(60):
        for label in ({str(n),f'{n:02}'} if n<10 else {str(n)}):
            bbox=font.getbbox(label)
            glyph=Image.new('L',(bbox[2]-bbox[0],bbox[3]-bbox[1]))
            ImageDraw.Draw(glyph).text((-bbox[0],-bbox[1]),label,font=font,fill=255)
            glyph=glyph.crop(glyph.getbbox())
            glyph=glyph.resize(tuple(max(1,round(z*scale)) for z in glyph.size),Image.Resampling.LANCZOS)
            tile=Image.new('L',(250,140))
            assert glyph.width<=250 and glyph.height<=140
            tile.paste(glyph,((250-glyph.width)//2,(140-glyph.height)//2))
            out=Image.new('RGBA',tile.size,'white');out.putalpha(tile);out.save(draw/f'{style}_{label}.png')

gallery=Image.open(root.parent/'表盘资料/Nike 混合/官方图1.png').convert('RGB')
keys=['purePlatinum','volt','totalOrange','pinkBlast','auroraGreen','midnightTurquoise','chlorineBlue','celestialTeal','obsidianMist','royalPulse','desertSand','spruceAura']
styles=[]
for k in keys:
    base=rgb('victory_'+k)
    accent=rgb('victoryHybrid_orangeLogo') if k=='purePlatinum' else base
    digits='#FF'+bytes(gallery.getpixel((169,170))).hex().upper() if k=='purePlatinum' else base
    dark=rgb('victoryHybrid_'+k+'_darker')
    styles.append((digits,accent,dark))
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=add(face,'UserConfigurations')
color=add(cfg,'ColorConfiguration',id='palette',displayName='color',defaultValue=0)
for i,colors in enumerate(styles):
    add(color,'ColorOption',id=i,displayName='p'+str(i),colors=' '.join(colors))
for field,items in [('time',['digital','analog','minimal']),('dial',['full','circle'])]:
    lst=add(cfg,'ListConfiguration',id=field,displayName=field,defaultValue=items[0])
    for item in items:add(lst,'ListOption',id=item,displayName=item)
def variants(p,key,items):
    conf=add(p,'ListConfiguration',id=key)
    return [(item,add(conf,'ListOption',id=item)) for item in items]
def stacked(p,ambient):
    for idx,(expr,y) in enumerate([('([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])',86),('[MINUTE]',230)]):
        cond=add(p,'Condition');ex=add(cond,'Expressions')
        for n in range(24 if idx==0 else 60):
            name='d'+str(n)
            add(ex,'Expression',name=name).text=f'{expr} == {n}'
            branch=add(cond,'Compare',expression=name)
            # Hours below 10 are single digits, matching the watch time display.
            text=str(n) if idx==0 else f'{n:02}'
            image(branch,('outline' if ambient else 'solid')+'_'+text,129,y+5,232,130,'[CONFIGURATION.palette.0]')
    image(p,'swoosh',45,231,74,27,'[CONFIGURATION.palette.1]')
def ticks():
    im=Image.new('RGBA',(960,960))
    pen=ImageDraw.Draw(im)
    for i in range(60):
        a=i*math.pi/30; r=441 if i%5==0 else 450
        xy=[(480+math.sin(a)*d,480-math.cos(a)*d) for d in [r,458]]
        pen.line(xy,fill='white',width=5 if i%5==0 else 2)
    return im.resize((480,480),Image.Resampling.LANCZOS)
ticks().save(draw/'ticks.png')
for key,length,width in [('hourhand',116,14),('minutehand',160,10),('secondhand',172,3)]:
    im=Image.new('RGBA',(960,960));p=ImageDraw.Draw(im)
    p.rounded_rectangle((480-width,480-length*2,480+width,493),radius=width,fill='white')
    p.ellipse((465,465,495,495),fill='white')
    im.resize((480,480),Image.Resampling.LANCZOS).save(draw/(key+'.png'))
handhour='(([HOUR_0_23]%12)*30 + [MINUTE]*0.5)'
handminute='([MINUTE]*6 + [SECOND]*0.1)'
def analog(p,minimal,ambient):
    if minimal and not ambient:
        d=add(p,'PartDraw',**box())
        arc=add(d,'Arc',centerX=240,centerY=240,width=260,height=260,startAngle=0,endAngle=90)
        transform(arc,'startAngle',handhour)
        transform(arc,'endAngle',handhour+' + (360 + '+handminute+' - '+handhour+')%360')
        add(arc,'Stroke',thickness=260,color='[CONFIGURATION.palette.2]')
    if not minimal:
        image(p,'ticks',0,0,480,480,'[CONFIGURATION.palette.0]')
    image(p,'swoosh',122,225,77,28,'[CONFIGURATION.palette.1]')
    for key,ang,col in [('hourhand',handhour,0),('minutehand',('[MINUTE]*6' if ambient else handminute),0),('secondhand','[SECOND_MILLISECOND]*6',1)]:
        if ambient and key=='secondhand':continue
        hand=image(p,key,0,0,480,480,f'[CONFIGURATION.palette.{col}]')
        transform(hand,'angle',ang)
corners.artwork(draw,catalog,gallery)
corners.configs(cfg)
scene=add(face,'Scene',backgroundColor='#000000')
for ambient in (False,True):
    parent=group(scene,'ambient' if ambient else 'interactive')
    parent.set('alpha','0' if ambient else '255')
    add(parent,'Variant',mode='AMBIENT',target='alpha',value=100 if ambient else 0)
    layout=group(parent,'layout'+str(int(ambient)))
    # The circular dial reserves a visible outer minute track on the digital face.
    for dial,opt in variants(layout,'dial',['full','circle']):
        gr=group(opt,dial+str(int(ambient)))
        if dial=='circle':
            gr.set('scaleX','0.85');gr.set('scaleY','0.85')
        for choice,v in variants(gr,'time',['digital','analog','minimal']):
            v=group(v,choice+dial+str(int(ambient)))
            if choice=='digital':
                if dial=='circle':image(v,'ticks',-35,-35,550,550,'[CONFIGURATION.palette.0]')
                stacked(v,ambient)
            else:analog(v,choice=='minimal',ambient)
corners.corners_scene(scene)
save(res/'raw/watchface.xml',face)
for path in local.glob('*.lproj'):
    code=path.stem
    directory=fw/'属性表'/core/path.name
    labels=read(directory/'ClockFaces.strings.json')
    names=read(directory/'FaceColors.strings.json')
    strings={'face_name':read(path/'Localizable.strings.json')['FACE_STYLE_OLYMPUS_IN_TITLE_CASE'],'time':labels['EDIT_MODE_LABEL_TIME'],'color':labels['EDIT_MODE_LABEL_COLOR'],'dial':labels.get('EDIT_MODE_LABEL_DIAL',labels.get('EDIT_MODE_LABEL_STYLE','Dial'))}
    for k,s in [('digital','DIGITAL'),('analog','ANALOG'),('minimal','MINIMALIST')]:
        strings[k]=labels['EDIT_OPTION_LABEL_VICTORY_WINDRUNNER_STYLE_'+s]
    for k,s in [('full','FULLSCREEN'),('circle','CIRCULAR')]:
        strings[k]=labels['EDIT_OPTION_LABEL_ANALOG_DIAL_SHAPE_'+s]
    for i,k in enumerate(keys): strings['p'+str(i)]=names.get(k,names.get('victory.'+k,k))
    compass=local.parents[1]/'ComplicationBundles/NanoCompassComplications.bundle'
    alt=compass/path.name/'AltimeterComplication.strings.json'
    corners.localization(labels,strings,read(alt if alt.exists() else compass/'en.lproj/AltimeterComplication.strings.json')['ALTITUDE_COMPLICATION_NAME'])
    out=ET.Element('resources')
    for k,v in strings.items():add(out,'string',name=k).text=v.replace("'","\\'")
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save(res/('values'+q)/'strings.xml',out)
prev=Image.new('RGBA',(480,480))
ImageDraw.Draw(prev).ellipse((0,0,479,479),fill='black')
for asset,xy,size,col in [('solid_10',(129,91),(232,130),0),('solid_09',(129,235),(232,130),0),('swoosh',(45,231),(74,27),1)]:
    mask=Image.open(draw/(asset+'.png')).getchannel('A').resize(size,Image.Resampling.LANCZOS)
    prev.paste(rgbtuple(styles[0][col])+(255,),xy,mask)
corners.preview(prev,draw,gallery)
prev.save(draw/'preview.png')
