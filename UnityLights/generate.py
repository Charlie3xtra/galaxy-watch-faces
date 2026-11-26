"""Generate the Unity Lights WFF dial from a locally extracted 24S132 firmware."""
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

root = Path(__file__).resolve().parent
fw = root.parent / 'Watch8_5_24S132'
bundle = Path('System/Library/NanoTimeKit/FaceBundles/NTKColtanFaceBundle.bundle')
res = root / 'res'
out = res / 'drawable-nodpi'
gallery = root / 'screenshots'
for folder in (out, gallery, res/'raw'):
    folder.mkdir(exist_ok=True, parents=True)

def node(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k:str(v) for k,v in attrs.items()})

def save_xml(tree, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path, encoding='utf-8', xml_declaration=True)

def box(x,y,w,h):
    return dict(x=x,y=y,width=w,height=h)

def read(path):
    return json.loads(path.read_text('utf8'))

raw = (fw/'filesystem'/bundle/'Coltan-Hand.art').read_bytes()
assert raw[:8] == bytes.fromhex('0a00010020032003')
mask = np.frombuffer(raw[8:], np.uint8).reshape(800,800,4)
atlas = fw/'解析/图集'/bundle/'Assets.car/资源'
def color(palette, key):
    return np.array(read(next(atlas.glob(f'coltan_{palette}_{key}-*.json')))['Components'][:3])

palettes = ('redgreengold','monochrome')
def sprite(name,img):
    img.save(out/(name+'.png'))

for side, scale in [('hour',.66),('minute',1.10)]:
    # Normalize the native downward hand to the twelve o'clock position.
    size = round(scale*800)
    planes = []
    for i in range(3):
        im = Image.fromarray(mask[:,:,i]).transpose(Image.Transpose.ROTATE_180)
        if side=='hour':
            im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        im=im.resize((size,size),Image.Resampling.LANCZOS)
        canvas=Image.new('L',(680,680))
        canvas.paste(im,((680-size)//2,)*2)
        plane=np.asarray(canvas,dtype=float)/255
        if i==1:
            # Smooth the low-bit diffuse field before expanding its dynamic range.
            smooth=np.asarray(canvas.filter(ImageFilter.GaussianBlur(5)),dtype=float)/255
            plane=np.maximum(0,.65*plane+.35*smooth-.008)
        planes.append(plane)
    core,bloom,body = planes
    edge=np.maximum(0,np.roll(body,3 if side=='hour' else -3,axis=1)-body)
    core=np.maximum(core,edge*.86)
    if side=='hour':
        bloom=np.minimum(1,bloom*1.45)
    silhouette=Image.new('RGBA',(680,680))
    silhouette.putalpha(Image.fromarray(np.uint8(body*255)))
    sprite(side+'_body',silhouette)
    for idx,palette in enumerate(palettes):
        inner=color(palette,side+'HandInnerColor')
        outer=color(palette,side+'HandOuterColor')
        for mode in ('active','ambient'):
            if mode=='active':
                field = bloom**.57*1.26
                rim = core**2.2
            else:
                field = bloom**1.6*.36
                rim = core**1.7*.48
            yy,xx=np.indices(field.shape)
            forward=(340-yy)/np.maximum(1,np.hypot(340-yy,xx-340))
            attenuation=np.clip((forward+.35)/.78,0,1)
            field*=attenuation*attenuation*(3-2*attenuation)
            rgb=np.clip(field[:,:,None]*outer+rim[:,:,None]*inner,0,1)
            # Store straight-alpha light so fully black pixels remain transparent.
            alpha=rgb.max(axis=2)
            rgba=np.dstack((rgb/np.maximum(alpha[:,:,None],1e-8),alpha))
            sprite(f'{side}_{idx}_{mode}',Image.fromarray(np.uint8(rgba*255+.5)))

for idx,pal in enumerate(palettes):
    ink=tuple(np.uint8(color(pal,'secondHandColor')*255))+(255,)
    im=Image.new('RGBA',(480,480))
    d=ImageDraw.Draw(im)
    d.line((240,38,240,256), fill=ink,width=2)
    sprite(f'second_{idx}',im)
    pin=Image.new('RGBA',(12,12))
    ImageDraw.Draw(pin).ellipse((2,2,9,9),fill=tuple(np.uint8(color(pal,'centerGlowColor')*255))+(255,))
    sprite(f'pin_{idx}',pin)
ticks=Image.new('RGBA',(480,480))
for i in range(12):
    tick=Image.new('RGBA',(480,480))
    ImageDraw.Draw(tick).rounded_rectangle((237,19,243,36),radius=3,fill='#959595')
    ticks.alpha_composite(tick.rotate(-30*i,resample=Image.Resampling.BICUBIC))
sprite('ticks',ticks)

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
config=node(face,'UserConfigurations')
palette=node(config,'ColorConfiguration',id='tone',displayName='color',defaultValue='0')
for i,swatch in enumerate(('#FF19D336 #FFFF393D','#FF000000 #FFFFFFFF')):
    node(palette,'ColorOption',id=i,displayName=f'p{i}',colors=swatch)
styles=node(config,'ListConfiguration',id='shape',displayName='dial',defaultValue='full')
for shape in ('full','inset'):
    node(styles,'ListOption',id=shape,displayName=shape,icon='option_'+shape)
density=node(config,'ListConfiguration',id='density',displayName='style',defaultValue='simple')
for style in ('simple','detailed'):
    node(density,'ListOption',id=style,displayName=style,icon='option_'+style)
scene=node(face,'Scene',backgroundColor='#000000')
style_switch=node(scene,'ListConfiguration',id='shape')
def ambient(part,alpha):
    node(part,'Variant',mode='AMBIENT',target='alpha',value=alpha)
def imagepart(parent,name,x,y,w,h):
    part=node(parent,'PartImage',**box(x,y,w,h))
    node(part,'Image',resource=name)
    return part
def hand(clock,side,name,size):
    h=node(clock,side.title()+'Hand',resource=name,**box((480-size)//2,(480-size)//2,size,size),pivotX='.5',pivotY='.5')
    if side=='second':
        node(h,'Sweep',frequency=15)
    return h
for shape in ('full','inset'):
    holder=node(style_switch,'ListOption',id=shape)
    factor=1 if shape=='full' else .69
    group=node(holder,'Group',name=shape,**box(0,0,480,480))
    switch=node(group,'Condition')
    exp=node(switch,'Expressions')
    node(exp,'Expression',name='colored').text='[CONFIGURATION.tone.0] == #FF19D336'
    for idx in range(2):
        branch=node(switch, 'Compare' if idx==0 else 'Default', **({'expression':'colored'} if idx==0 else {}))
        for mode in ('active','ambient'):
            layer=node(branch,'Group',name=f'{shape}_{idx}_{mode}',**box(0,0,480,480),alpha=255 if mode=='active' else 0)
            ambient(layer,0 if mode=='active' else 255)
            for side in ('hour','minute'):
                clock=node(layer,'AnalogClock',**box(0,0,480,480))
                hand(clock,side,f'{side}_{idx}_{mode}',round(680*factor))
            marks=node(node(layer,'ListConfiguration',id='density'),'ListOption',id='detailed')
            dim=round(480*factor)
            imagepart(marks,'ticks',(480-dim)//2,(480-dim)//2,dim,dim)
            clock=node(layer,'AnalogClock',**box(0,0,480,480))
            for side in ('hour','minute'):
                hand(clock,side,side+'_body',round(680*factor))
            if mode=='active':
                hand(clock,'second',f'second_{idx}',dim)
            imagepart(layer,f'pin_{idx}',234,234,12,12)
    if shape=='inset':
        for i,(cx,cy) in enumerate(((99,99),(381,99),(99,381),(381,381))):
            slot=node(scene,'ComplicationSlot',slotId=i+1,displayName=f'corner{i}',supportedTypes='SHORT_TEXT MONOCHROMATIC_IMAGE EMPTY',**box(cx-34,cy-31,68,62))
            node(slot,'BoundingOval',**box(0,0,68,62))
            for kind in ('SHORT_TEXT','MONOCHROMATIC_IMAGE'):
                content=node(slot,'Complication',type=kind)
                comp=node(node(node(content,'Group',name=f'corner_{i}_{kind}',**box(0,0,68,62)),'ListConfiguration',id='shape'),'ListOption',id='inset')
                comp=node(comp,'Group',name=f'data_{i}_{kind}',**box(0,0,68,62))
                imagepart(comp,'[COMPLICATION.MONOCHROMATIC_IMAGE]',22 if kind=='SHORT_TEXT' else 15,3 if kind=='SHORT_TEXT' else 12,24 if kind=='SHORT_TEXT' else 38,24 if kind=='SHORT_TEXT' else 38)
                if kind=='SHORT_TEXT':
                    t=node(node(comp,'PartText',**box(0,27,68,33)),'Text',align='CENTER',ellipsis='TRUE')
                    template=node(node(t,'Font',family='SYNC_TO_DEVICE',size=21,color='#FFE6E6E6'),'Template')
                    template.text='%s'
                    node(template,'Parameter',expression='[COMPLICATION.TEXT]')


def preview(idx=0,inset=False,detailed=False,ambient_mode=False,minute=9):
    canvas=Image.new('RGBA',(480,480),'black')
    def paint(name,angle=0):
        im=Image.open(out/(name+'.png')).convert('RGBA')
        if inset:
            im=im.resize(tuple(round(k*.69) for k in im.size),Image.Resampling.LANCZOS)
        if angle:
            im=im.rotate(-angle,resample=Image.Resampling.BICUBIC)
        canvas.alpha_composite(im,((480-im.width)//2,(480-im.height)//2))
    angles=(300+minute*.5,minute*6)
    for side,angle in zip(('hour','minute'),angles):
        paint(f'{side}_{idx}_'+('ambient' if ambient_mode else 'active'),angle)
    if detailed: paint('ticks')
    for side,angle in zip(('hour','minute'),angles):
        paint(side+'_body',angle)
    if not ambient_mode: paint('second_'+str(idx),180)
    paint('pin_'+str(idx))
    circle=Image.new('L',(480,480))
    ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255)
    canvas=Image.composite(canvas,Image.new('RGBA',canvas.size),circle)
    return canvas
for name,kw in [('preview',{}),('option_full',{}),('option_inset',dict(inset=True)),('option_simple',{}),('option_detailed',dict(detailed=True))]:
    sprite(name,preview(**kw))
for name,kw in [('gallery',{}),('ambient',dict(ambient_mode=True)),('monochrome',dict(idx=1,inset=True,detailed=True,minute=28))]:
    preview(**kw).save(gallery/(name+'.png'))

for loc in (fw/'解析/属性表'/bundle).glob('*.lproj'):
    own=read(loc/'Localizable.strings.json')
    common=fw/'解析/属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/loc.name
    options=read(common/'ClockFaces.strings.json')
    pigments=read(common/'FaceColors.strings.json')
    data=dict(face_name=own['COLTAN_FACE_NAME_IN_TITLE_CASE'],style=own['EDIT_OPTION_LABEL_DENSITY'],simple=own['EDIT_OPTION_LABEL_DENSITY_SIMPLE'],detailed=own['EDIT_OPTION_LABEL_DENSITY_DETAILED'],dial=options.get('EDIT_MODE_LABEL_DIAL',options.get('EDIT_MODE_LABEL_STYLE','Dial')),color=options['EDIT_MODE_LABEL_COLOR'],full=options['EDIT_OPTION_LABEL_ANALOG_DIAL_SHAPE_FULLSCREEN'],inset=options['EDIT_OPTION_LABEL_ANALOG_DIAL_SHAPE_CIRCULAR'],p0=pigments.get('unity.red & unity.green', '🟥 / 🟩'),p1=pigments.get('white','⬛ / ⬜'))
    data['p1']='黑白' if loc.stem.startswith('zh') else ('Black & White' if loc.stem.startswith('en') else '◐')
    for i,key in enumerate(('TOP_LEFT','TOP_RIGHT','BOTTOM_LEFT','BOTTOM_RIGHT')):
        data[f'corner{i}']=options['SLOT_LABEL_'+key]
    tree=ET.Element('resources')
    for k,v in data.items():
        node(tree,'string',name=k).text=v.replace("'","\\'")
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save_xml(tree,res/('values'+s)/'strings.xml')






# Trim transparent margins while keeping the physical rotation center invariant.
for asset in sorted({e.get('resource') for e in face.iter() if e.tag in ('HourHand','MinuteHand','SecondHand')}):
    path=out/(asset+'.png')
    im=Image.open(path).convert('RGBA')
    l,t,r,b=im.getchannel('A').getbbox()
    mid=im.width/2
    l=min(l,int(mid)-1)
    r=max(r,int(mid)+1)
    t=min(t,int(mid)-1)
    b=max(b,int(mid)+1)
    cropped=im.crop((l,t,r,b))
    if asset.endswith('ambient'):
        cropped=cropped.resize(tuple(max(1,round(s*.60)) for s in cropped.size), Image.Resampling.LANCZOS)
    cropped.save(path)
    for el in face.iter():
        if el.get('resource')!=asset: continue
        scale=float(el.get('width'))/im.width
        w=max(1,round((r-l)*scale))
        h=max(1,round((b-t)*scale))
        x=round(240-(mid-l)*scale)
        y=round(240-(mid-t)*scale)
        el.attrib.update({k:str(v) for k,v in box(x,y,w,h).items()})
        el.set('pivotX',str((240-x)/w))
        el.set('pivotY',str((240-y)/h))
save_xml(face,res/'raw/watchface.xml')

