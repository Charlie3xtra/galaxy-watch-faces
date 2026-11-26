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
glass=set()
def bg(parent,bounds,radius):
    # Antialiased glass rim and a broad upper reflection, rendered once per shape.
    w,h=bounds['width'],bounds['height']
    key=f'glass_{w}_{h}'
    if key not in glass:
        glass.add(key)
        scale=3
        W,H=w*scale,h*scale
        mask=Image.new('L',(W,H))
        ImageDraw.Draw(mask).rounded_rectangle((1,1,W-2,H-2),radius*scale,fill=255)
        surface=Image.new('RGBA',(W,H))
        pixels=surface.load()
        for y in range(H):
            for x in range(W):
                u,v=x/W,y/H
                value=int(24+13*(1-v)**2+8*max(0,1-((u-.23)/.72)**2-((v+.4)/.65)**2))
                pixels[x,y]=(value,value,min(255,value+2),255)
        inner=Image.new('L',(W,H))
        ImageDraw.Draw(inner).rounded_rectangle((4,4,W-5,H-5),max(1,radius*scale-3),fill=255)
        from PIL import ImageChops
        rim=ImageChops.subtract(mask,inner)
        shine=Image.new('RGBA',(W,H))
        sd=ImageDraw.Draw(shine)
        for y in range(H):
            v=int(40+66*(1-y/H)**3)
            sd.line((0,y,W,y),fill=(v,v,v+2,255))
        surface.paste(shine,mask=rim);surface.putalpha(mask)
        surface.resize((w,h),Image.Resampling.LANCZOS).save(out/(key+'.png'))
    node=el(parent,'PartImage',**bounds)
    variant(node,'alpha',0)
    el(node,'Image',resource=key)
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
colors=el(cfg,'ColorConfiguration',id='scheme',displayName='color',defaultValue='multi')
el(colors,'ColorOption',id='multi',displayName='multi',colors='#FF00CFFF')
for i,tone in enumerate(tones):el(colors,'ColorOption',id=i,displayName=tone,colors=ink(tone))
styles=el(cfg,'ListConfiguration',id='layout',displayName='style',defaultValue='default')
sizes=['default','large','xlarge']
for st in sizes:
    for ss in ('','_with_seconds'):
        el(styles,'ListOption',id=st+ss,displayName=st+ss,icon='sample_'+st+ss)
bezel=el(cfg,'ListConfiguration',id='bezel_mode',displayName='edge',defaultValue='elevation')
for mode in ('elevation','seconds','none'):el(bezel,'ListOption',id=mode,displayName=mode)
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
            w=([61,64,68][i] if not ss else [40,42,44][i]) if ch!=':' else (19 if not ss else 13)
            h=[75,85,95][i]
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
edge=el(el(scene,'ListConfiguration',id='bezel_mode'),'ListOption',id='seconds')
ring=el(edge,'Group',name='seconds_ring',**full)
colored(ring,'[CONFIGURATION.scheme.0]',ink('bezelMajorTick_night'),ink('bezelMajorTick.tritium'),ink('bezelMajorTick_night.tritium'))
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
            tt=el(dc,'TimeText',**box(35,99,410,108),format='hh:mm:ss' if show_seconds else 'hh:mm',hourFormat='SYNC_TO_DEVICE',align='CENTER')
            el(tt,'BitmapFont',family=family if show_seconds else st,size=[75,85,95][i],color='#FFFFFFFF')
# The two rows fit inside the circular safe area. Only actual provider data is shown.
slots=[('top_left',145,77,'EMPTY','EMPTY',None),
       ('top',240,75,'DATE','SHORT_TEXT',None),
       ('top_right',335,77,'EMPTY','EMPTY',None),
       ('center',240,259,'WATCH_BATTERY','RANGED_VALUE',None),
       ('bottom_left',145,372,'EMPTY','EMPTY',('com.samsung.android.wear.shealth','complications.heartrate.HeartrateComplicationProviderService','SHORT_TEXT')),
       ('bottom_center',240,372,'EMPTY','EMPTY',('com.samsung.android.wear.shealth','complications.exercise.ExerciseRunningComplicationProviderService','MONOCHROMATIC_IMAGE')),
       ('bottom_right',335,372,'EMPTY','EMPTY',('com.samsung.android.watch.weather','complication.UvIndexComplicationService','SHORT_TEXT'))]
for idx,(key,x,y,default,datatype,provider) in enumerate(slots,1):
    wide=key=='center'
    w,h=(294,118) if wide else ((148,80) if key=='top' else (84,84))
    types=['LONG_TEXT','SHORT_TEXT','RANGED_VALUE','MONOCHROMATIC_IMAGE','EMPTY'] if wide else ['RANGED_VALUE','SHORT_TEXT','MONOCHROMATIC_IMAGE','EMPTY']
    slot=el(scene,'ComplicationSlot',slotId=20+idx,displayName=key,supportedTypes=' '.join(types),**box(x-w//2,y-h//2,w,h))
    if wide or key=='top':el(slot,'BoundingRoundBox',**box(0,0,w,h),cornerRadius=21)
    else:el(slot,'BoundingOval',**box(0,0,w,h))
    policy=dict(defaultSystemProvider=default,defaultSystemProviderType=datatype)
    if provider:
        pkg,cls,typ=provider;policy.update(primaryProvider=pkg+'/'+pkg+'.'+cls,primaryProviderType=typ)
    el(slot,'DefaultProviderPolicy',**policy)
    for typ in types:
        view=el(slot,'Complication',type=typ)
        if typ=='EMPTY':continue
        top=key=='top'
        if not top:bg(view,box(0,0,w,h),21 if wide else w//2)
        g=el(view,'Group',name=key+'_'+typ.lower(),**box(0,0,w,h))
        white='#FFFFFFFF'
        accent={'center':'#FF00D2BF','bottom_left':'#FFFF494B','bottom_center':'#FFAEED00','bottom_right':'#FFFFAE00'}.get(key,'#FFABB2BB')
        def paint(group,color):
            day=f'([CONFIGURATION.scheme.0]==#FF00CFFF ? {color} : [CONFIGURATION.scheme.0])'
            colored(group,day,ink('primaryComplication_night'),day,ink('primaryComplication_night.tritium'))
            variant(group,'alpha',155)
        def layer(name,color):
            node=el(g,'Group',name=key+'_'+typ.lower()+'_'+name,**box(0,0,w,h))
            paint(node,color)
            return node
        detail=layer('detail',accent)
        reading=layer('reading',white)
        val='[COMPLICATION.TEXT]'
        img='[COMPLICATION.MONOCHROMATIC_IMAGE]'
        if top:
            icon(detail,box(63,0,22,22),img)
            text(reading,box(2,33,w-4,39),val,23)
        elif wide and typ=='RANGED_VALUE':
            fraction='clamp(([COMPLICATION.RANGED_VALUE_VALUE]-[COMPLICATION.RANGED_VALUE_MIN])/max(0.001,[COMPLICATION.RANGED_VALUE_MAX]-[COMPLICATION.RANGED_VALUE_MIN]),0,1)'
            for active in (False,True):
                draw=el(detail,'PartDraw',**box(0,0,w,h))
                arc=el(draw,'Arc',centerX=66,centerY=76,width=80,height=80,startAngle=270,endAngle=450)
                if active:el(arc,'Transform',target='endAngle',value=f'270+180*{fraction}')
                el(arc,'Stroke',thickness=14,color='#FFFFFFFF' if active else '#FF505355',cap='ROUND')
            text(detail,box(25,50,82,44),'numberFormat("#",[COMPLICATION.RANGED_VALUE_VALUE])',30)
            cond=el(reading,'Condition')
            el(el(cond,'Expressions'),'Expression',name='has_title').text='textLength([COMPLICATION.TITLE])>0'
            text(el(cond,'Compare',expression='has_title'),box(116,20,170,42),'[COMPLICATION.TITLE]',22)
            default=el(cond,'Default')
            icon(default,box(121,29,20,20),img)
            part=el(default,'PartText',**box(144,20,130,42))
            el(el(part,'Text',align='START'),'Font',family='SYNC_TO_DEVICE',size=20,color='#FFFFFFFF').text='@string/level' 
            text(detail,box(119,59,160,42),f'textLength({val})>0 ? {val} : numberFormat("#",[COMPLICATION.RANGED_VALUE_VALUE])',26)
        elif wide:
            icon(detail,box(22,33,51,51),img)
            if typ!='MONOCHROMATIC_IMAGE':
                text(reading,box(77,17,208,41),'[COMPLICATION.TITLE]',22)
                text(detail,box(77,56,208,47),val,24)
        elif typ=='MONOCHROMATIC_IMAGE':
            icon(detail,box(17,17,50,50),img)
        else:
            if typ=='RANGED_VALUE':
                draw=el(detail,'PartDraw',**box(0,0,w,h))
                arc=el(draw,'Arc',centerX=42,centerY=42,width=72,height=72,startAngle=225,endAngle=495)
                el(arc,'Transform',target='endAngle',value='225+270*clamp(([COMPLICATION.RANGED_VALUE_VALUE]-[COMPLICATION.RANGED_VALUE_MIN])/max(0.001,[COMPLICATION.RANGED_VALUE_MAX]-[COMPLICATION.RANGED_VALUE_MIN]),0,1)')
                el(arc,'Stroke',thickness=5,color='#FFFFFFFF',cap='ROUND')
            icon(detail,box(31,9,22,22),img)
            cond=el(reading,'Condition')
            el(el(cond,'Expressions'),'Expression',name='long_reading').text='textLength([COMPLICATION.TEXT]) > 4'
            text(el(cond,'Compare',expression='long_reading'),box(2,32,80,37),val,17)
            text(el(cond,'Default'),box(3,27,78,45),val,30)
            text(detail,box(5,59,74,21),'[COMPLICATION.TITLE]',13)
from elevation import add_bezel
add_bezel(scene,el,box,colored,ink)
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
    for k in ('elevation','seconds','none'):data[k]=local['EDIT_OPTION_LABEL_FOGHORN_BEZEL_'+k.upper()]
    for k,*_ in slots:data[k]=labels.get('SLOT_LABEL_'+k.upper(),k.replace('_',' ').title())
    for k in tones:data[k]=names.get('foghorn.'+k,names.get(k,k.title()))
    data.update(feet=local.get('FOGHORN_LABEL_FEET','FT'),meters=local.get('FOGHORN_LABEL_METERS','M'))
    data['level']='Level'
    data['multi']=labels.get('EDIT_OPTION_LABEL_MULTICOLOR','Multicolor')
    code=loc.stem
    if code.startswith('zh'):
        data.update(level='当前读数' if code=='zh_CN' else '目前讀數',multi='多色',nightmode='夜间模式' if code=='zh_CN' else '夜間模式',adventurer='探险橙' if code=='zh_CN' else '探險橙',ocean='海洋蓝' if code=='zh_CN' else '海洋藍',performance='金黄' if code=='zh_CN' else '金黃',burgundy='酒红' if code=='zh_CN' else '酒紅',desert='沙色')
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
    tint='#008EAB' if ambient else '#00CFFF'
    white='#ADADAD' if ambient else '#FFFFFF'
    for side,count in [(-1,20),(1,30)]:
        for n in range(count+1):
            angle=math.radians(side*(134-88*n/count))
            def at(r):return (240+r*math.sin(angle),240-r*math.cos(angle))
            d.line((at(233),at(220 if n%(2 if side<0 else 10)==0 else 226)),width=3,fill='#77797D')
        a=math.radians(side*(134-88*.6));x=240+228*math.sin(a);y=240-228*math.cos(a)
        d.ellipse((x-6,y-6,x+6,y+6),fill='black',outline=tint,width=3)
    def label(x,y,v,size,col):
        d.text((x,y),v,font=ImageFont.truetype('segoeui.ttf',size),fill=col,anchor='mm')
    for x,y,v in [(101,67,'FT'),(379,67,'M'),(98,402,'100'),(382,402,'30'),(240,450,'≈ 18 m')]:
        label(x,y,v,15,tint)
    d.rounded_rectangle((232,41,248,57),radius=3,outline='#AAAEB8',width=2)
    d.line((233,47,247,47),fill='#AAAEB8',width=2)
    label(240,88,'1 Apr',23,white)
    time=Image.open(out/'sample_default.png')
    if ambient:time.putalpha(time.getchannel('A').point(lambda v:int(v*.70)))
    img.alpha_composite(time,(70,103))
    if not ambient:img.alpha_composite(Image.open(out/'glass_294_118.png'),(93,200))
    teal='#00D2BF'
    d.arc((119,236,199,316),180,360,fill='#505355',width=13)
    d.arc((119,236,199,316),180,310,fill=teal,width=13)
    label(159,275,'72',28,teal);label(300,239,'Level',22,white);label(300,280,'72%',24,teal)
    for x,col,symbol,reading in [(145,'#FF494B','♥','68'),(240,'#AEED00','',None),(335,'#FFAE00','☀','4')]:
        if not ambient:img.alpha_composite(Image.open(out/'glass_84_84.png'),(x-42,330))
        if reading:
            if symbol=='☀':
                d.ellipse((x-5,345,x+5,355),fill=col)
                for n in range(8):
                    a=n*math.pi/4;d.line((x+7*math.cos(a),350+7*math.sin(a),x+10*math.cos(a),350+10*math.sin(a)),fill=col,width=2)
            else:label(x,350,symbol,20,col)
            label(x,377,reading,30,white)
        else:
            runner=Image.open(root/'artwork/runner.png').convert('RGBA')
            runner.thumbnail((48,48),Image.Resampling.LANCZOS)
            art=Image.new('RGBA',runner.size,col);art.putalpha(runner.getchannel('A'))
            img.alpha_composite(art,(x-art.width//2,372-art.height//2))
    return img
gallery(False).save(out/'preview.png')
for aod,filename in [(False,'gallery.png'),(True,'gallery-ambient.png')]:
    gallery(aod).save(root/'screenshots'/filename)