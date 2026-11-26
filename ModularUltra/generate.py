"""Generate the round Modular Ultra watch face using the watchOS 24S132 bundle."""
import io
import json
import struct
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132/解析'
name='NTKFoghornFaceBundle'
bundle=Path('System/Library/NanoTimeKit/FaceBundles')/(name+'.bundle')
common=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
catalog=fw/'图集'/bundle/'Assets.car/资源'
out=root/'res/drawable-nodpi'
def ink(key):
    record=json.loads(next(catalog.glob('foghorn_'+key+'-*.json')).read_text('utf8'))
    values=record['Components']
    if len(values)==2:values=[values[0]]*3+[values[1]]
    return '#'+''.join(f'{round(max(0,min(1,v))*255):02X}' for v in [values[-1],*values[:3]])
blob=(fw/'代码'/name/name).read_bytes()
p=32
for _ in range(struct.unpack_from('<I',blob,16)[0]):
    cmd,length=struct.unpack_from('<II',blob,p)
    if cmd==25:
        for i in range(struct.unpack_from('<I',blob,p+64)[0]):
            section,_,_,size,offset=struct.unpack_from('<16s16sQQI',blob,p+72+80*i)
            if section.rstrip(b'\0')==b'__FoghornFont':fontdata=blob[offset:offset+size]
    p+=length
def el(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
def box(x,y,w,h):return dict(x=x,y=y,width=w,height=h)
full=box(0,0,480,480)
def write_xml(tree,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def variant(node,target,val):el(node,'Variant',mode='AMBIENT',target=target,value=val)
def colored(node,day,night,ambient,night_ambient):
    el(node,'Transform',target='tintColor',value=f'[CONFIGURATION.night] ? {night} : {day}')
    variant(node,'tintColor',f'[CONFIGURATION.night] ? {night_ambient} : {ambient}')
def bg(parent,bounds,radius):
    node=el(parent,'PartDraw',**bounds)
    variant(node,'alpha',0)
    shape=el(node,'RoundRectangle',**box(0,0,bounds['width'],bounds['height']),cornerRadiusX=radius,cornerRadiusY=radius)
    el(shape,'Fill',color='#FF202022')
def text(parent,bounds,expr,size):
    part=el(parent,'PartText',**bounds)
    font=el(el(part,'Text',align='CENTER',ellipsis='TRUE'),'Font',family='SYNC_TO_DEVICE',size=size,color='#FFFFFFFF')
    t=el(font,'Template');t.text='%s'
    el(t,'Parameter',expression=expr)
def icon(parent,bounds,source):
    el(el(parent,'PartImage',**bounds),'Image',resource=source)

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=el(face,'UserConfigurations')
tones=['adventurer','ocean','performance','burgundy','desert']
colors=el(cfg,'ColorConfiguration',id='tone',displayName='color',defaultValue='0')
for i,tone in enumerate(tones):el(colors,'ColorOption',id=i,displayName=tone,colors=ink(tone))
styles=el(cfg,'ListConfiguration',id='layout',displayName='style',defaultValue='default')
sizes=['default','large','xlarge']
for st in sizes:
    for ss in ('','_with_seconds'):
        el(styles,'ListOption',id=st+ss,displayName=st+ss,icon='sample_'+st+ss)
bezel=el(cfg,'ListConfiguration',id='bezel',displayName='edge',defaultValue='seconds')
for mode in ('seconds','none'):el(bezel,'ListOption',id=mode,displayName=mode)
el(cfg,'BooleanConfiguration',id='night',displayName='nightmode',defaultValue='FALSE')

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
registry=el(face,'BitmapFonts')
glyph_sets={}
for i,st in enumerate(sizes):
    variable=TTFont(io.BytesIO(fontdata))
    buf=io.BytesIO()
    instantiateVariableFont(variable,{'wght':480,'wdth':0,'hght':[0,350,750][i]}).save(buf)
    f=ImageFont.truetype(io.BytesIO(buf.getvalue()),180)
    bounds=[f.getbbox(ch) for ch in '0123456789:']
    top=min(b[1] for b in bounds);bottom=max(b[3] for b in bounds)
    glyph_sets[st]={}
    for ss in ('','_with_seconds'):
        family=st+ss
        bm=el(registry,'BitmapFont',name=family)
        for ch in '0123456789:':
            w=([56,60,64][i] if not ss else [40,42,44][i]) if ch!=':' else (19 if not ss else 13)
            h=[69,82,95][i]
            l,t,r,b=f.getbbox(ch)
            mask=Image.new('L',(r-l+8,bottom-top+4));ImageDraw.Draw(mask).text((4-l,2-top),ch,font=f,fill=255)
            im=Image.new('RGBA',(w,h),'white')
            im.putalpha(mask.resize((w,h),Image.Resampling.LANCZOS))
            key=family+'_'+('colon' if ch==':' else ch)
            im.save(out/(key+'.png'))
            for char in ([ch] if ch==':' else [ch,chr(0x660+int(ch)),chr(0x6f0+int(ch)),chr(0x966+int(ch))]):
                el(bm,'Character',name=char,resource=key,width=w,height=h)
            glyph_sets[st][ss,ch]=im
        sample=Image.new('RGBA',(340,100))
        chars='10:09:30' if ss else '10:09'
        x=(340-sum(glyph_sets[st][ss,ch].width for ch in chars))//2
        for ch in chars:
            im=glyph_sets[st][ss,ch];sample.alpha_composite(im,(x,(100-h)//2));x+=im.width
        sample.save(out/('sample_'+family+'.png'))
scene=el(face,'Scene',backgroundColor='#000000')
mint=ink('timeMinutes')
edge=el(el(scene,'ListConfiguration',id='bezel'),'ListOption',id='seconds')
ring=el(edge,'Group',name='seconds_ring',**full)
colored(ring,'[CONFIGURATION.tone.0]',ink('bezelMajorTick_night'),ink('bezelMajorTick.tritium'),ink('bezelMajorTick_night.tritium'))
for n in range(60):
    major=n%5==0
    part=el(ring,'PartDraw',**full,angle=n*6)
    el(part,'Transform',target='alpha',value=f'[SECOND] >= {n} ? 240 : 62')
    variant(part,'alpha',62 if major else 22)
    rect=el(part,'RoundRectangle',**box(238 if major else 239,6,4 if major else 2,13 if major else 7),cornerRadiusX=1,cornerRadiusY=1)
    el(rect,'Fill',color='#FFFFFFFF')
layouts=el(scene,'ListConfiguration',id='layout')
for i,st in enumerate(sizes):
    for ss in ('','_with_seconds'):
        family=st+ss
        wrapper=el(el(layouts,'ListOption',id=family),'Group',name='clock_'+family,**full)
        colored(wrapper,mint,ink('timeMinutes_night'),ink('timeMinutes.tritium'),ink('timeMinutes_night.tritium'))
        for aod in ([False,True] if ss else [False]):
            show_seconds=bool(ss) and not aod
            dc=el(wrapper,'DigitalClock',**full,alpha=0 if aod else 255)
            if ss:variant(dc,'alpha',255 if aod else 0)
            tt=el(dc,'TimeText',**box(35,132,410,105),format='hh:mm:ss' if show_seconds else 'hh:mm',hourFormat='SYNC_TO_DEVICE',align='CENTER')
            el(tt,'BitmapFont',family=family if show_seconds else st,size=[69,82,95][i],color='#FFFFFFFF')
# The two rows fit inside the circular safe area. Only actual provider data is shown.
slots=[('top_left',143,88,'WATCH_BATTERY','RANGED_VALUE',None),
       ('top',240,77,'DATE','SHORT_TEXT',None),
       ('top_right',337,88,'EMPTY','EMPTY',('com.samsung.android.watch.weather','complication.WeatherComplicationService','SHORT_TEXT')),
       ('center',240,277,'NEXT_EVENT','LONG_TEXT',None),
       ('bottom_left',143,382,'EMPTY','EMPTY',('com.samsung.android.wear.shealth','complications.heartrate.HeartrateComplicationProviderService','SHORT_TEXT')),
       ('bottom_center',240,392,'STEP_COUNT','SHORT_TEXT',('com.samsung.android.wear.shealth','complications.steps.StepsComplicationProviderService','SHORT_TEXT')),
       ('bottom_right',337,382,'SUNRISE_SUNSET','SHORT_TEXT',None)]
for idx,(key,x,y,default,datatype,provider) in enumerate(slots,1):
    wide=key=='center'
    w,h=(318,80) if wide else (74,74)
    types=['LONG_TEXT','SHORT_TEXT','RANGED_VALUE','MONOCHROMATIC_IMAGE','EMPTY'] if wide else ['RANGED_VALUE','SHORT_TEXT','MONOCHROMATIC_IMAGE','EMPTY']
    slot=el(scene,'ComplicationSlot',slotId=idx,displayName=key,supportedTypes=' '.join(types),**box(x-w//2,y-h//2,w,h))
    if wide:el(slot,'BoundingRoundBox',**box(0,0,w,h),cornerRadius=17)
    else:el(slot,'BoundingOval',**box(0,0,w,h))
    policy=dict(defaultSystemProvider=default,defaultSystemProviderType=datatype)
    if provider:
        pkg,cls,typ=provider;policy.update(primaryProvider=pkg+'/'+pkg+'.'+cls,primaryProviderType=typ)
    el(slot,'DefaultProviderPolicy',**policy)
    for typ in types:
        view=el(slot,'Complication',type=typ)
        if typ=='EMPTY':continue
        bg(view,box(0,0,w,h),17 if wide else w//2)
        g=el(view,'Group',name=key+'_'+typ.lower(),**box(0,0,w,h))
        colored(g,'[CONFIGURATION.tone.0]',ink('primaryComplication_night'),'[CONFIGURATION.tone.0]',ink('primaryComplication_night.tritium'))
        variant(g,'alpha',160)
        img='[COMPLICATION.MONOCHROMATIC_IMAGE]'
        val='[COMPLICATION.TEXT]'
        if typ=='MONOCHROMATIC_IMAGE':
            icon(g,box(w//2-20,h//2-20,40,40),img)
        elif wide:
            icon(g,box(16,20,40,40),img)
            text(g,box(63,6,w-75,28),'[COMPLICATION.TITLE]',18)
            text(g,box(60,33,w-72,41),val,24)
        else:
            if typ=='RANGED_VALUE':
                for fg in (False,True):
                    part=el(g,'PartDraw',**box(0,0,w,h),alpha=255 if fg else 52)
                    arc=el(part,'Arc',centerX=37,centerY=37,width=66,height=66,startAngle=215,endAngle=505)
                    if fg:el(arc,'Transform',target='endAngle',value='215+290*clamp(([COMPLICATION.RANGED_VALUE_VALUE]-[COMPLICATION.RANGED_VALUE_MIN])/max(0.001,[COMPLICATION.RANGED_VALUE_MAX]-[COMPLICATION.RANGED_VALUE_MIN]),0,1)')
                    el(arc,'Stroke',color='#FFFFFFFF',thickness=3)
                val=f'textLength({val})>0 ? {val} : numberFormat("#",[COMPLICATION.RANGED_VALUE_VALUE])'
            icon(g,box(25,8,24,24),img)
            cond=el(g,'Condition')
            el(el(cond,'Expressions'),'Expression',name='long_reading').text='textLength([COMPLICATION.TEXT]) > 5'
            text(el(cond,'Compare',expression='long_reading'),box(2,32,70,32),val,15)
            text(el(cond,'Default'),box(3,32,68,32),val,21)
write_xml(face,root/'res/raw/watchface.xml')
for loc in (fw/'属性表'/bundle).glob('*.lproj'):
    def read(path):return json.loads(path.read_text('utf8')) if path.exists() else {}
    local=read(loc/'Localizable.strings.json')
    base=fw/'属性表'/common/loc.name
    labels=read(base/'ClockFaces.strings.json')
    names=read(base/'FaceColors.strings.json')
    data=dict(face_name=local['FOGHORN_FACE_NAME_IN_TITLE_CASE'],style=local['EDIT_MODE_LABEL_FOGHORN_STYLE'],edge=local['EDIT_MODE_LABEL_FOGHORN_BEZEL'],color=labels.get('EDIT_MODE_LABEL_COLOR','Color'),nightmode=labels.get('EDIT_MODE_LABEL_NIGHT_MODE','Night Mode'))
    for st in sizes:
        for ss in ('','_with_seconds'):
            key=st+ss;data[key]=local['EDIT_OPTION_LABEL_FOGHORN_STYLE_'+key.upper()]
    for k in ('seconds','none'):data[k]=local['EDIT_OPTION_LABEL_FOGHORN_BEZEL_'+k.upper()]
    for k,*_ in slots:data[k]=labels.get('SLOT_LABEL_'+k.upper(),k.replace('_',' ').title())
    for k in tones:data[k]=names.get('foghorn.'+k,names.get(k,k.title()))
    code=loc.stem
    if code.startswith('zh'):
        data.update(nightmode='夜间模式' if code=='zh_CN' else '夜間模式',adventurer='探险橙' if code=='zh_CN' else '探險橙',ocean='海洋蓝' if code=='zh_CN' else '海洋藍',performance='金黄' if code=='zh_CN' else '金黃',burgundy='酒红' if code=='zh_CN' else '酒紅',desert='沙色')
    tree=ET.Element('resources')
    for k,v in data.items():el(tree,'string',name=k).text=v.replace("'","\\'")
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        write_xml(tree,root/('res/values'+s)/'strings.xml')
# Gallery artwork uses fixed example readings, independent of personal watch data.
import math
from PIL import ImageColor
def gallery(ambient):
    img=Image.new('RGBA',(480,480),'black')
    d=ImageDraw.Draw(img)
    color='#A74B13' if ambient else '#FF6600'
    for n in range(60):
        a=math.radians(n*6)
        def at(r):return (240+r*math.sin(a),240-r*math.cos(a))
        d.line([at(232),at(220 if n%5==0 else 225)],fill=('#292929' if ambient else color if n<=32 else '#49270D'),width=3 if n%5==0 else 2)
    time=Image.open(out/'sample_default.png')
    if ambient:time.putalpha(time.getchannel('A').point(lambda v:int(v*.70)))
    img.alpha_composite(time,(70,134))
    regular=ImageFont.truetype('segoeui.ttf',21)
    small=ImageFont.truetype('segoeui.ttf',15)
    symbols=ImageFont.truetype('seguisym.ttf',22)
    samples=[('▣','72%'),('▦','1 Apr'),('☀','18°'),('▦','Calendar'),('♥','68'),('↗','2450'),('☼','06:32')]
    for (key,x,y,*_),(symbol,reading) in zip(slots,samples):
        if key=='center':
            if not ambient:d.rounded_rectangle((81,237,399,317),17,fill='#202022')
            d.text((119,y),symbol,font=symbols,fill=color,anchor='mm')
            d.text((255,y),reading,font=regular,fill=color,anchor='mm')
        else:
            if not ambient:d.ellipse((x-37,y-37,x+37,y+37),fill='#202022')
            d.text((x,y-13),symbol,font=symbols,fill=color,anchor='mm')
            d.text((x,y+12),reading,font=small if len(reading)>5 else regular,fill=color,anchor='mm')
    return img
gallery(False).save(out/'preview.png')
for aod,filename in [(False,'gallery.png'),(True,'gallery-ambient.png')]:
    gallery(aod).save(root/'screenshots'/filename)