"""Build Nike Bounce from the 24S132 Magma palette, logo and Victory fonts."""
from pathlib import Path
from io import BytesIO
import json, math, os, struct
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132/解析'
if os.name=='nt': fw=Path('\\\\?\\'+str(fw))
relative=Path('System/Library/NanoTimeKit/FaceBundles/NTKMagmaFaceBundle.bundle')
atlas=fw/'图集'/relative/'Assets.car/资源'
core=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
draw=root/'res/drawable-nodpi'
draw.mkdir(parents=True,exist_ok=True)
def read(path): return json.loads(path.read_text('utf8'))
def sub(p,tag,**attrs): return ET.SubElement(p,tag,{k:str(v) for k,v in attrs.items()})
def box(x,y,w,h):return dict(x=x,y=y,width=w,height=h)
def save(path,node):
    path.parent.mkdir(parents=True,exist_ok=True);ET.indent(node)
    ET.ElementTree(node).write(path,encoding='utf-8',xml_declaration=True)
def color(path):
    c=read(path)['Components']; c=c if len(c)>2 else [c[0]]*3+[c[1]]
    return '#FF'+''.join(f'{max(0,min(255,round(v*255))):02X}' for v in c[:3])
fonts={}
data=(fw/'代码/NanoTimeKit/NanoTimeKit').read_bytes(); offset=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,length=struct.unpack_from('<II',data,offset)
    if cmd==25:
        for i in range(struct.unpack_from('<I',data,offset+64)[0]):
            sec,seg,addr,size,start=struct.unpack_from('<16s16sQQI',data,offset+72+80*i)
            if sec.startswith(b'__VictoryFont'):
                font=ImageFont.truetype(BytesIO(data[start:start+size]),360)
                fonts['line' if 'outline' in str(font.getname()).lower() else 'ink']=font
    offset+=length
logo=Image.open(next(atlas.glob('logo21*.png'))).convert('RGBA')
logo=logo.getchannel('A');logo=logo.crop(logo.getbbox())
white=Image.new('RGBA',logo.size,'white');white.putalpha(logo);white.save(draw/'swoosh.png')
palette={'purePlatinum':color(next((fw/'图集'/core/'Assets.car/资源').glob('victory_purePlatinum-*')))}
for p in sorted(atlas.glob('magma_fall2022_*.json')):
    palette[p.name.split('_')[2].split('-')[0]]=color(p)
logo_color=color(next(atlas.glob('magma_logo-*')))
width,height=148,176
yy,xx=np.mgrid[:height,:width].astype(np.float32)
def warp_coordinates(effect,frame):
    # A travelling local impulse displaces the texture. Each successive swing loses amplitude.
    t=frame/30
    cx,cy=(width*.42,height*.53) if effect=='tap' else (width*.5,height*.9)
    dist=np.hypot((xx-cx)*.82,yy-cy)
    age=np.maximum(0,t-dist/(610 if effect=='tap' else 760))
    phase=age*(23 if effect=='tap' else 19)
    swing=np.sin(phase)*np.exp(-age*5.1)*np.exp(-dist/135)
    envelope=min(1,(26-frame)/4)
    dx=(8+(yy-cy)*.24)*swing*envelope
    dy=(15+(yy-cy)*.18)*swing*envelope
    return xx-dx,yy-dy
def sample(a,coords):
    x,y=coords;x=np.clip(x,0,width-1.001);y=np.clip(y,0,height-1.001)
    ix=x.astype('int32');iy=y.astype('int32');u=x-ix;v=y-iy
    value=(1-v)*((1-u)*a[iy,ix]+u*a[iy,ix+1])+v*((1-u)*a[iy+1,ix]+u*a[iy+1,ix+1])
    return Image.fromarray((255-value).round().astype('uint8')).convert('RGB')
coords={e:[warp_coordinates(e,k) for k in range(27)] for e in ('tap','wake')}
masks={}; widths={}
for name,font in fonts.items():
    scale=148/(font.getbbox('0')[3]-font.getbbox('0')[1])
    for d in range(10):
        s=str(d);bounds=font.getbbox(s)
        tile=Image.new('L',(bounds[2]-bounds[0],bounds[3]-bounds[1]))
        ImageDraw.Draw(tile).text((-bounds[0],-bounds[1]),s,font=font,fill=255)
        tile=tile.crop(tile.getbbox());tile=tile.resize(tuple(round(i*scale) for i in tile.size),Image.Resampling.LANCZOS)
        canvas=Image.new('L',(width,height));canvas.paste(tile,((width-tile.width)//2,(height-tile.height)//2))
        if name=='line':
            asset=Image.new('RGBA',canvas.size,'white');asset.putalpha(canvas);asset.save(draw/f'line{d}.png');continue
        masks[d]=canvas;widths[d]=tile.width
        base=Image.eval(canvas,lambda a:255-a).convert('RGB');base.save(draw/f'idle{d}.png')
        for effect,maps in coords.items():
            frames=[sample(np.asarray(canvas),m) for m in maps]
            frames[0].save(draw/f'{effect}{d}.webp',save_all=True,append_images=frames[1:],duration=[33,33,34]*9,
                           lossless=True,method=2,loop=1)
def img(parent,src,b,**attrs):
    p=sub(parent,'PartImage',**b,**attrs);sub(p,'Image',resource=src);return p
def fill(parent,col,**attrs):
    p=sub(parent,'PartDraw',**box(0,0,480,480),**attrs);sub(sub(p,'Rectangle',**box(0,0,480,480)),'Fill',color=col)
def xf(p,attr,expr):return sub(p,'Transform',target=attr,value=expr)
def expr_width(v):
    out=str(widths[9])
    for d in reversed(range(9)):out=f'({v} == {d} ? {widths[d]} : {out})'
    return out
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=sub(face,'UserConfigurations'); pal=sub(cfg,'ColorConfiguration',id='tone',displayName='color',defaultValue=0)
for i,v in enumerate(palette.values()):sub(pal,'ColorOption',id=i,displayName=f'c{i}',colors=v)
sub(cfg,'BooleanConfiguration',id='background',displayName='bg',defaultValue='TRUE')
scene=sub(face,'Scene',backgroundColor='#000000')
for ambient in (False,True):
    g=sub(scene,'Group',name='ambient' if ambient else 'interactive',**box(0,0,480,480),alpha=0 if ambient else 255)
    sub(g,'Variant',mode='AMBIENT',target='alpha',value=255 if ambient else 0)
    if not ambient: fill(g,'#FFFFFFFF')
    for row,num,y in [('h','([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])',56),('m','[MINUTE]',225)]:
        tens=f'floor({num}/10)';ones=f'({num}%10)'
        for side,selector,other in [('l',tens,ones),('r',ones,tens)]:
            c=sub(g,'Condition');ex=sub(c,'Expressions')
            for d in range(10):
                single=row=='h' and d==0 and side=='l'
                if single:continue
                key=f'd{d}';sub(ex,'Expression',name=key).text=f'{selector} == {d}'
                branch=sub(c,'Compare',expression=key)
                # Composite each opaque sprite separately so its white padding cannot cover its neighbour.
                shift=-1 if side=='l' else 1
                left=f'{240-width/2} + {shift} * ({expr_width(other)}+10)/2'
                if row=='h' and side=='r':left=f'({num}<10 ? {240-width/2} : {left})'
                group=sub(branch,'Group',name=f'{row}{side}{d}_{int(ambient)}',**box(0,y,width,height));xf(group,'x',left)
                if ambient:
                    img(group,'line'+str(d),box(0,0,width,height),tintColor='#FF878B8C');continue
                # Opposing transforms cancel gravity at rest. Different response times
                # leave a brief elastic displacement when wrist acceleration changes.
                moving=sub(group,'Group',name=f'motion_{row}{side}{d}',**box(0,0,width,height))
                for attr,axis,mult in [('angle','X',1.65*shift),('scaleY','Y',.019*shift)]:
                    signal=f'clamp([ACCELEROMETER_{axis}],-6,6)*{mult:.3f}'
                    value=f'1+({signal})' if attr=='scaleY' else signal
                    xf(group,attr,value)
                    inverse=f'1/({value})' if attr=='scaleY' else f'-({value})'
                    trans=xf(moving,attr,inverse)
                    sub(trans,'Animation',interpolation='OVERSHOOT',duration='0.30',fps=30)
                group=moving
                cell=widths[d]+10
                crop=sub(group,'PartDraw',**box(0,0,width,height),renderMode='MASK')
                sub(sub(crop,'Rectangle',**box((width-cell)/2,1,cell,height-2)),'Fill',color='#FFFFFFFF')
                img(group,'idle'+str(d),box(0,0,width,height))
                for event,effect in [('ON_VISIBLE','wake'),('ON_NEXT_MINUTE','wake'),('TAP','tap')]:
                    p=sub(group,'PartAnimatedImage',**box(0,0,width,height))
                    sub(p,'AnimatedImage',resource=effect+str(d),format='WEBP',thumbnail='idle'+str(d))
                    sub(p,'AnimationController',play=event,beforePlaying='HIDE',afterPlaying='HIDE',repeat='FALSE')
    if not ambient:
        opt=sub(g,'BooleanConfiguration',id='background')
        fill(sub(opt,'BooleanOption',id='FALSE'),'#FFFFFFFF',blendMode='DIFFERENCE')
        fill(g,'[CONFIGURATION.tone.0]',blendMode='MULTIPLY')
    img(g,'swoosh',box(198,405,84,30),tintColor='#FF6E6E6E' if ambient else logo_color)
save(root/'res/raw/watchface.xml',face)
for loc in (fw/'属性表'/relative).glob('*.lproj'):
    src=read(loc/'Localizable.strings.json')
    base=fw/'属性表'/core/loc.name
    labels=read(base/'ClockFaces.strings.json'); colors=read(base/'FaceColors.strings.json')
    overrides=loc/'FaceColors-Magma.strings.json'
    if overrides.exists():colors.update(read(overrides))
    strings={'face_name':src['FACE_STYLE_MAGMA_IN_TITLE_CASE'],'bg':src['EDIT_MODE_LABEL_MAGMA_STYLE'],'color':labels['EDIT_MODE_LABEL_COLOR']}
    for i,k in enumerate(palette):strings[f'c{i}']=colors.get(k,colors.get('magma.fall2022.'+k,k))
    tree=ET.Element('resources')
    for k,v in strings.items():sub(tree,'string',name=k).text=v.replace("'","\\'")
    lang=loc.stem;suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(lang,'-'+lang.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(lang,[]):save(root/f'res/values{q}/strings.xml',tree)
preview=Image.new('RGBA',(480,480));tone=palette['purePlatinum'][-6:];ImageDraw.Draw(preview).ellipse((0,0,479,479),fill='#'+tone)
for row,y in [('10',56),('09',225)]:
    a,b=map(int,row)
    for d,x in [(a,240-(widths[b]+10)/2),(b,240+(widths[a]+10)/2)]:
        preview.paste('black',(round(x-width/2),y,round(x-width/2)+width,y+height),masks[d])
preview.paste('#'+logo_color[-6:],(198,405,282,435),logo.resize((84,30),Image.Resampling.LANCZOS))
preview.save(draw/'preview.png')
