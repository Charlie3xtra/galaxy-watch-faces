"""Build Contour from the Neptune fonts embedded in the 24S132 face binary."""
from pathlib import Path
import io, json, math, struct, shutil
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.basePen import BasePen

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_1_24S132'/'解析'
binary='NTKProteusFaceBundle'
blob=(fw/'代码'/binary/binary).read_bytes()
fonts={}
p=32
for _ in range(struct.unpack_from('<I',blob,16)[0]):
    cmd,length=struct.unpack_from('<II',blob,p)
    if cmd==25:
        for i in range(struct.unpack_from('<I',blob,p+64)[0]):
            name,_,addr,size,offset=struct.unpack_from('<16s16sQQI',blob,p+72+i*80)
            if b'Neptune' in name:
                fonts['soft' if b'Sft' in name else 'sharp']=TTFont(io.BytesIO(blob[offset:offset+size]))
    p+=length
glyphs='twelve one two three four five six seven eight nine ten eleven'.split()
out=root/'res/drawable-nodpi'
out.mkdir(parents=True,exist_ok=True)
def project(point):
    x=(point[0]-1568.5)/1568.5
    y=(1916-point[1])/1916
    angle=math.atan2(x,-y)
    # The outlines share a rounded rectangular perimeter. Preserve their depth
    # below that perimeter while bending the band onto the Galaxy circle.
    dx,dy=abs(x),abs(y)
    norm=math.hypot(dx,dy)
    ux,uy=dx/norm,dy/norm
    t=min(1/max(ux,1e-9),1/max(uy,1e-9))
    corner=.36
    if min(t*ux,t*uy)>1-corner:
        dot=(1-corner)*(ux+uy)
        t=dot+math.sqrt(max(0,dot*dot-2*(1-corner)**2+corner**2))
    r=233-237*(t-norm)
    return np.array((240+r*math.sin(angle),240-r*math.cos(angle)))

class Outline(BasePen):
    def __init__(self,glyphset):
        super().__init__(glyphset)
        self.loops=[]
    def _moveTo(self,p):
        self.start=p
        self.loops.append([project(p)])
    def _lineTo(self,p):
        start=np.array(self._getCurrentPoint())
        for t in np.linspace(0,1,max(2,int(np.linalg.norm(start-p)/25)),endpoint=True)[1:]:
            self.loops[-1].append(project(start*(1-t)+np.array(p)*t))
    def _qCurveToOne(self,control,p):
        start=np.array(self._getCurrentPoint())
        for t in np.linspace(0,1,17)[1:]:
            self.loops[-1].append(project((1-t)**2*start+2*t*(1-t)*np.array(control)+t*t*np.array(p)))
    def _curveToOne(self,a,b,p):
        start=np.array(self._getCurrentPoint())
        for t in np.linspace(0,1,21)[1:]:
            self.loops[-1].append(project((1-t)**3*start+3*t*(1-t)**2*np.array(a)+3*t*t*(1-t)*np.array(b)+t**3*np.array(p)))
    def _closePath(self):
        self._lineTo(self.start)

from PIL import ImageFont
from fontTools.varLib.instancer import instantiateVariableFont
levels=22
locations={}
for style,font in fonts.items():
    for table in font['cmap'].tables:
        if table.isUnicode():
            table.cmap.update({0xe000+i:g for i,g in enumerate(glyphs)})
    for level in range(levels+1):
        buf=io.BytesIO()
        instantiateVariableFont(font,{'wght':level/levels,'STIN':0}).save(buf)
        raster=ImageFont.truetype(io.BytesIO(buf.getvalue()),1916)
        glyphset=font.getGlyphSet(location={'wght':level/levels})
        for index,key in enumerate(glyphs):
            pen=Outline(glyphset)
            glyphset[key].draw(pen)
            points=np.concatenate(pen.loops)
            left,top=np.floor(points.min(axis=0)-3).astype(int)
            right,bottom=np.ceil(points.max(axis=0)+3).astype(int)
            width,height=right-left,bottom-top
            # FreeType resolves the overlapping contours of the variable font
            # before resampling. Even-odd polygon fill leaves triangular seams.
            ch=chr(0xe000+index)
            l,t,r,b=raster.getbbox(ch,anchor='ls')
            tile=Image.new('L',(r-l+4,b-t+4))
            ImageDraw.Draw(tile).text((2-l,2-t),ch,font=raster,anchor='ls',fill=255)
            yy,xx=np.mgrid[0:height*3,0:width*3]
            x=left+(xx+.5)/3-240
            y=top+(yy+.5)/3-240
            rad=np.hypot(x,y)
            ux=x/rad
            uy=y/rad
            ax,ay=abs(ux),abs(uy)
            edge=1/np.maximum(ax,ay)
            corner=.36
            dot=(1-corner)*(ax+ay)
            edge=np.where(np.minimum(ax,ay)*edge>1-corner,dot+np.sqrt(np.maximum(0,dot*dot-2*(1-corner)**2+corner**2)),edge)
            norm=edge-(233-rad)/237
            sx=np.rint((1+ux*norm)*784.25-l+2).astype(int)
            sy=np.rint((uy*norm-1)*958-t+2).astype(int)
            valid=(sx>=0)&(sx<tile.width)&(sy>=0)&(sy<tile.height)
            pixels=np.zeros(sx.shape,'uint8')
            pixels[valid]=np.asarray(tile)[sy[valid],sx[valid]]
            im=Image.new('RGBA',(width,height),'white')
            im.putalpha(Image.fromarray(pixels).resize(im.size,Image.Resampling.LANCZOS))
            name=f'{style}_{index}_{level}'
            im.save(out/(name+'.png'))
            locations[name]=(left,top,width,height)

def el(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
def save(tree,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def box(x=0,y=0,w=480,h=480):
    return dict(x=x,y=y,width=w,height=h)
def group(parent):
    return el(parent,'Group',name='colored_background',**box())
def ambient(node,target,value):
    el(node,'Variant',mode='AMBIENT',target=target,value=value)

core=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
bundle=Path('System/Library/NanoTimeKit/FaceBundles')/(binary+'.bundle')
def ink(asset,container):
    path=next((fw/'图集'/container/'Assets.car/资源').glob(asset+'-*.json'))
    rgb=json.loads(path.read_text('utf8'))['Components']
    return '#FF'+''.join(f'{round(c*255):02X}' for c in rgb[:3])
colors=['standard_cream','standard_blue','standard_red','standard_yellow','seasons_spring2015_white','victory_volt']
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
config=el(face,'UserConfigurations')
palette=el(config,'ColorConfiguration',id='tone',displayName='color',defaultValue='0')
for i,key in enumerate(colors):
    main=ink(key,core)
    contrast=ink('proteus_'+key+'_digitContrast',bundle) if i>=3 else '#FF161616'
    el(palette,'ColorOption',id=i,displayName=f'c{i}',colors=main+' '+contrast)
stylecfg=el(config,'ListConfiguration',id='style',displayName='style',defaultValue='sharp')
for style in fonts:el(stylecfg,'ListOption',id=style,displayName=style)
el(config,'BooleanConfiguration',id='colored',displayName='dial',defaultValue='FALSE')
scene=el(face,'Scene',backgroundColor='#000000')
bg=group(scene)
ambient(bg,'alpha','0')
opt=el(el(bg,'BooleanConfiguration',id='colored'),'BooleanOption',id='TRUE')
el(el(el(opt,'PartDraw',**box()),'Rectangle',**box()),'Fill',color='[CONFIGURATION.tone.0]')
styles=el(scene,'ListConfiguration',id='style')
# Outside the two-second turnover window all expressions use the civil hour.
phase='([MINUTE] == 59 ? clamp(([SECOND_MILLISECOND]-58)/2,0,1) : 0)'
for style in fonts:
    parent=el(el(styles,'ListOption',id=style),'Group',name=style,**box())
    for index in range(12):
        dist=f'(({index}+24-([HOUR_0_23]%12)-{phase})%12)'
        weight=f'round({levels}*({dist}<1 ? 1-{dist} : ({dist}-1)/11))'
        cond=el(parent,'Condition')
        expressions=el(cond,'Expressions')
        for level in range(levels+1):
            label=f'w{level}'
            el(expressions,'Expression',name=label).text=f'{weight} == {level}'
            case=el(cond,'Compare',expression=label)
            name=f'{style}_{index}_{level}'
            part=el(case,'PartImage',**box(*locations[name]),tintColor='[CONFIGURATION.tone.0]')
            el(part,'Transform',target='tintColor',value='[CONFIGURATION.colored] ? [CONFIGURATION.tone.1] : [CONFIGURATION.tone.0]')
            ambient(part,'tintColor','[CONFIGURATION.tone.0]')
            ambient(part,'alpha',135)
            el(part,'Image',resource=name)
# Native optional short-text data source. Empty by default like the gallery shot.
slot=el(scene,'ComplicationSlot',slotId=1,displayName='comp',supportedTypes='SHORT_TEXT EMPTY',**box(174,284,132,44))
el(slot,'BoundingRoundBox',**box(0,0,132,44),cornerRadius=21)
comp=el(slot,'Complication',type='SHORT_TEXT')
font=el(el(el(comp,'PartText',**box(0,0,132,44)),'Text',align='CENTER'),'Font',family='SYNC_TO_DEVICE',size=27,color='#FFFFFFFF')
tpl=el(font,'Template');tpl.text='%s';el(tpl,'Parameter',expression='[COMPLICATION.TEXT]')
clock=el(scene,'AnalogClock',**box())
for tag,key,length in [('HourHand','hour',87),('MinuteHand','minute',145),('SecondHand','second',178)]:
    w=22
    tail=15 if key=='second' else 4
    h=length+tail+4
    im=Image.new('RGBA',(w*4,h*4))
    d=ImageDraw.Draw(im);cx=w*2;cy=(length+2)*4
    if key=='second':
        d.line((cx,8,cx,h*4-4),fill='#FF3B30',width=7)
        d.ellipse((cx-16,cy-16,cx+16,cy+16),fill='#FF3B30')
        d.ellipse((cx-6,cy-6,cx+6,cy+6),fill='black')
    else:
        d.line((cx,20,cx,cy),fill='white',width=13)
        d.rounded_rectangle((cx-22,8,cx+22,cy-40),radius=22,fill='white')
    im.resize((w,h),Image.Resampling.LANCZOS).save(out/(key+'.png'))
    hand=el(clock,tag,resource=key,**box(240-w//2,238-length,w,h),pivotX='.5',pivotY=(length+2)/h)
    if key=='second':
        ambient(hand,'alpha',0)
        el(hand,'Sweep',frequency=15)
save(face,root/'res/raw/watchface.xml')
labels=fw/'属性表'/bundle
for loc in labels.glob('*.lproj'):
    def read(path):return json.loads(path.read_text('utf8')) if path.exists() else {}
    names=read(loc/'Localizable.strings.json')
    common=fw/'属性表'/core/loc.name
    options=read(common/'ClockFaces.strings.json')
    pigments=read(common/'FaceColors.strings.json')
    data={'face_name':names['FACE_STYLE_PROTEUS_IN_TITLE_CASE'],'style':names['EDIT_MODE_LABEL_PROTEUS_STYLE'],'sharp':names['EDIT_OPTION_LABEL_PROTEUS_STYLE_SHARP'],'soft':names['EDIT_OPTION_LABEL_PROTEUS_STYLE_SOFT'],'dial':names['EDIT_MODE_LABEL_PROTEUS_CONTENT'],'color':options.get('EDIT_MODE_LABEL_COLOR','Color'),'comp':options.get('EDIT_MODE_LABEL_COMPLICATION','Complication')}
    for i,key in enumerate(colors):
        data[f'c{i}']=pigments.get(key.replace('_','.'),key.split('_')[-1].title())
    code=loc.stem
    if code.startswith('zh'):
        data.update(comp='复杂功能' if code=='zh_CN' else '複雜功能',c4='白色',c5='荧光黄' if code=='zh_CN' else '螢光黃')
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    tree=ET.Element('resources')
    for k,v in data.items():el(tree,'string',name=k).text=v.replace("'","\\'")
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save(tree,root/('res/values'+s)/'strings.xml')

def preview(hour,minute,aod):
    dial=Image.new('RGBA',(480,480),'black')
    for index in range(12):
        dist=(index-hour)%12
        level=22 if dist==0 else 2*(dist-1)
        key=f'sharp_{index}_{level}'
        mask=Image.open(out/(key+'.png')).getchannel('A')
        color=Image.new('RGBA',mask.size,'#'+ink(colors[0],core)[3:])
        color.putalpha(mask.point(lambda x:round(x*135/255)) if aod else mask)
        dial.alpha_composite(color,locations[key][:2])
    for key,length,angle in [('hour',87,hour*30+minute/2),('minute',145,minute*6),('second',178,180)]:
        if key=='second' and aod:continue
        layer=Image.new('RGBA',dial.size)
        layer.alpha_composite(Image.open(out/(key+'.png')),(229,238-length))
        dial.alpha_composite(layer.rotate(-angle,resample=Image.Resampling.BICUBIC,center=(240,240)))
    mask=Image.new('L',dial.size);ImageDraw.Draw(mask).ellipse((0,0,479,479),fill=255)
    dial.putalpha(mask)
    return dial
screens=root/'screenshots'
screens.mkdir(exist_ok=True)
preview(10,9,False).save(out/'preview.png')
shutil.copy(out/'preview.png',screens/'preview.png')
preview(10,9,True).save(screens/'ambient-preview.png')
