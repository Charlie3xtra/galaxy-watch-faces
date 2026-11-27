"""Generate Activity Digital resources from the extracted watchOS font and localized names."""
from pathlib import Path
import json, math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, ImageFilter

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132'
res=root/'res'
art=res/'drawable-nodpi'
fontfile=next((fw/'系统字体').rglob('SFCompactRoundedNumeric.ttf'))
def font(size):
    f=ImageFont.truetype(str(fontfile),size)
    try: f.set_variation_by_name('Semibold')
    except (ValueError,OSError): pass
    return f
def add(p,tag,**a):
    return ET.SubElement(p,tag,{k:str(v) for k,v in a.items()})
def box(x,y,w,h):return dict(x=x,y=y,width=w,height=h)
def save(tree,path):
    path.parent.mkdir(exist_ok=True,parents=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def ambient(el,attr,value):
    add(el,'Variant',mode='AMBIENT',target=attr,value=value)
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
add(face,'Metadata',key='CLOCK_TYPE',value='DIGITAL')
add(face,'Metadata',key='PREVIEW_TIME',value='10:09:30')
bitmap=add(add(face,'BitmapFonts'),'BitmapFont',name='activity')
f=font(80)
for i,c in enumerate('0123456789:-'):
    w=round(f.getlength(c))+2
    img=Image.new('RGBA',(w,88))
    ImageDraw.Draw(img).text((1,68),c,font=f,anchor='ls',fill='white',stroke_width=0)
    key=f'g{i}'
    img.save(art/(key+'.png'))
    for char in ([c,chr(0x660+i),chr(0x6f0+i),chr(0x966+i)] if i<10 else [c]):
        add(bitmap,'Character',name=char,resource=key,width=w,height=88)
cfg=add(face,'UserConfigurations')
colors=add(cfg,'ColorConfiguration',id='tint',displayName='color',defaultValue='white')
for id,c in [('white','#FFFFFFFF'),('rose','#FFFF2D55'),('orange','#FFFF9500'),('lemon','#FFF5E900'),('mint','#FF42E6CF'),('blue','#FF58B7FF')]:
    add(colors,'ColorOption',id=id,colors=c)
add(cfg,'BooleanConfiguration',id='seconds',displayName='seconds_label',defaultValue='TRUE')
add(cfg,'BooleanConfiguration',id='steps',displayName='use_steps',defaultValue='TRUE')
scene=add(face,'Scene',backgroundColor='#FF000000')
def group(p,name,**extra):return add(p,'Group',name=name,**box(0,0,480,480),**extra)
def switch(p,key,flag):return add(add(p,'BooleanConfiguration',id=key),'BooleanOption',id=str(flag).upper())
def time(p,fmt):
    clock=add(p,'DigitalClock',**box(0,0,480,480))
    text=add(clock,'TimeText',**box(36,101,402,83),format=fmt,align='END',hourFormat='SYNC_TO_DEVICE')
    add(text,'BitmapFont',family='activity',size=74,color='[CONFIGURATION.tint.0]')
active=group(scene,'time_active');ambient(active,'alpha',0)
for b in (True,False):time(switch(active,'seconds',b),'hh:mm:ss' if b else 'hh:mm')
sleep=group(scene,'time_ambient',alpha=0);ambient(sleep,'alpha',190)
time(sleep,'hh:mm')
cx,cy=150,278
radii=(84,59,34)
inks=('#FFFF165A','#FFA7F600','#FF04DADB')
tracks=('#FF420A1D','#FF2D3C06','#FF033536')
rows=(177,244,311)
def arc(p,r,color,frac=None):
    draw=add(p,'PartDraw',**box(0,0,480,480))
    if frac: add(draw,'Transform',target='alpha',value=f'({frac}) > 0 ? 255 : 0')
    ring=add(draw,'Arc',centerX=cx,centerY=cy,width=r*2,height=r*2,startAngle=0,endAngle=360)
    if frac:add(ring,'Transform',target='endAngle',value=f'360*clamp({frac},0,1)')
    stroke=add(ring,'Stroke',thickness=20,color=color,cap='ROUND')
    if frac:
        start={inks[0]:'#FFF00029',inks[1]:'#FF64D900',inks[2]:'#FF00BCC5'}[color]
        add(stroke,'SweepGradient',centerX=cx,centerY=cy,startAngle=0,endAngle=360,colors=start+' '+color,positions='0 1')
def value(p,idx,expr):
    text=add(add(p,'PartText',**box(244,rows[idx],170,70)),'Text',align='END')
    bf=add(text,'BitmapFont',family='activity',size=64,color=inks[idx])
    t=add(bf,'Template');t.text='%s';add(t,'Parameter',expression=expr)
rings=group(scene,'tracks');ambient(rings,'alpha',120)
for i,r in enumerate(radii):arc(rings,r,tracks[i])
def provider(slot,component,typ,fallback='EMPTY',ftype='EMPTY'):
    kw=dict(defaultSystemProvider=fallback,defaultSystemProviderType=ftype)
    if component:kw.update(primaryProvider=component,primaryProviderType=typ)
    add(slot,'DefaultProviderPolicy',**kw)
def metric(p,i,num,fraction):
    arc(p,radii[i],inks[i],fraction)
    value(p,i,num)
for i,label in enumerate(('move','exercise','stand')):
    slot=add(scene,'ComplicationSlot',slotId=10+i,displayName=label,supportedTypes='RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY',**box(0,0,480,480))
    add(slot,'BoundingRoundBox',**box(248,rows[i]+1,168,64),cornerRadius=12)
    provider(slot,None,None)
    for kind in ('EMPTY','SHORT_TEXT','RANGED_VALUE','GOAL_PROGRESS'):
        comp=add(slot,'Complication',type=kind)
        p=group(comp,f'metric_{i}_{kind}');ambient(p,'alpha',155)
        if i==2:p=switch(p,'steps',False)
        g=group(p,f'content_{i}_{kind}')
        if kind=='EMPTY':value(g,i,"'---'")
        elif kind=='SHORT_TEXT':value(g,i,'[COMPLICATION.TEXT]')
        elif kind=='RANGED_VALUE':
            metric(g,i,'round([COMPLICATION.RANGED_VALUE_VALUE])','([COMPLICATION.RANGED_VALUE_VALUE]-[COMPLICATION.RANGED_VALUE_MIN])/max(1,[COMPLICATION.RANGED_VALUE_MAX]-[COMPLICATION.RANGED_VALUE_MIN])')
        else:metric(g,i,'round([COMPLICATION.GOAL_PROGRESS_VALUE])','[COMPLICATION.GOAL_PROGRESS_VALUE]/max(1,[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE])')
sg=group(switch(scene,'steps',True),'steps_metric');ambient(sg,'alpha',155)
# Footprints distinguish the Galaxy step total from Apple's stand-hours figure.
foot=Image.new('RGBA',(48,38));fd=ImageDraw.Draw(foot)
for x,y in ((10,16),(28,3)):
    fd.ellipse((x,y,x+9,y+14),fill='#04DADB')
    fd.ellipse((x+2,y+16,x+8,y+22),fill='#04DADB')
foot.save(art/'footsteps.png')
add(add(sg,'PartImage',**box(385,371,22,18)),'Image',resource='footsteps')
metric(sg,2,'[STEP_COUNT]','[STEP_COUNT]/max(1,[STEP_GOAL])')
def badge(slot_id,key,x,y,w,h,source,kind):
    slot=add(scene,'ComplicationSlot',slotId=slot_id,displayName=key,supportedTypes='SHORT_TEXT LONG_TEXT MONOCHROMATIC_IMAGE EMPTY',**box(x,y,w,h))
    if w==h:add(slot,'BoundingOval',**box(0,0,w,h))
    else:add(slot,'BoundingRoundBox',**box(0,0,w,h),cornerRadius=12)
    provider(slot,source,kind)
    for typ in ('SHORT_TEXT','LONG_TEXT','MONOCHROMATIC_IMAGE'):
        comp=add(slot,'Complication',type=typ)
        p=add(comp,'Group',name=f'{key}_{typ}',**box(0,0,w,h));ambient(p,'alpha',130)
        if w==h:
            bg=add(add(p,'PartDraw',**box(0,0,w,h)),'Ellipse',**box(0,0,w,h))
            add(bg,'Fill',color='#FF191919')
        if typ=='MONOCHROMATIC_IMAGE' or w==h:
            dim=42 if typ=='MONOCHROMATIC_IMAGE' else 25
            im=add(p,'PartImage',**box((w-dim)//2,(h-dim)//2 if typ=='MONOCHROMATIC_IMAGE' else 4,dim,dim))
            if key=='top_right':im.set('tintColor','#FFADFA00')
            add(im,'Image',resource='[COMPLICATION.MONOCHROMATIC_IMAGE]')
        if typ!='MONOCHROMATIC_IMAGE':
            part=add(p,'PartText',**box(0,29 if w==h else 0,w,31 if w==h else h))
            tx=add(part,'Text',align='CENTER',ellipsis='TRUE')
            ft=add(tx,'Font',family='SYNC_TO_DEVICE',size=17 if w==h else 22,color='#FFFFFFFF')
            t=add(ft,'Template');t.text='%s';add(t,'Parameter',expression='[COMPLICATION.TEXT]')
health='com.samsung.android.wear.shealth/com.samsung.android.wear.shealth.complications.exercise.WorkoutComplicationProviderService'
weather='com.samsung.android.watch.weather/com.samsung.android.watch.weather.complication.'
badge(1,'top_left',104,43,62,62,weather+'WeatherComplicationService','SHORT_TEXT')
badge(2,'top_right',314,43,62,62,health,'MONOCHROMATIC_IMAGE')
badge(3,'bottom',99,385,282,37,weather+'WeatherComplicationService','SHORT_TEXT')
save(face,res/'raw/watchface.xml')
bundle=fw/'解析/属性表/System/Library/NanoTimeKit/FaceBundles/NTKActivityFaceBundle.bundle'
for loc in bundle.glob('*.lproj'):
    own=json.loads((loc/'Localizable.strings.json').read_text('utf8'))
    code=loc.stem
    common=fw/'解析/属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/loc.name/'ClockFaces.strings.json'
    opts=json.loads(common.read_text('utf8')) if common.exists() else {}
    vals=dict(face_name=own['FACE_STYLE_ACTIVITY_DIGITAL_IN_TITLE_CASE'],move='Move',exercise='Exercise',stand='Stand',seconds_label='Show seconds',use_steps='Use steps for inner ring',color=opts.get('EDIT_MODE_LABEL_COLOR','Color'),top_left=opts.get('SLOT_LABEL_TOP_LEFT','Top left'),top_right=opts.get('SLOT_LABEL_TOP_RIGHT','Top right'),bottom=opts.get('SLOT_LABEL_BOTTOM','Bottom'))
    if code.startswith('zh'):
        vals.update(move='活动能量',exercise='锻炼分钟',stand='站立小时',seconds_label='显示秒数',use_steps='内环显示步数',bottom='底部') if code=='zh_CN' else vals.update(move='活動能量',exercise='運動分鐘',stand='站立小時',seconds_label='顯示秒數',use_steps='內環顯示步數',bottom='底部')
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    tree=ET.Element('resources')
    for k,v in vals.items():add(tree,'string',name=k).text=v.replace("'","\\'")
    for s in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):save(tree,res/('values'+s)/'strings.xml')

# Fixed gallery readings, kept out of the live scene.
im=Image.new('RGB',(480,480));d=ImageDraw.Draw(im)
def right(x,y,s,size,color):
    d.text((x,y),s,font=font(size),fill=color,anchor='rt')
right(433,113,'10:09:30',66,'white')
for i,(r,n,pct) in enumerate(zip(radii,('500','30','12'),(.96,.85,.72))):
    b=(cx-r,cy-r,cx+r,cy+r)
    d.ellipse((b[0]-10,b[1]-10,b[2]+10,b[3]+10),outline='#'+tracks[i][3:],width=20)
    col='#'+inks[i][3:]
    d.arc((b[0]-10,b[1]-10,b[2]+10,b[3]+10),-90,-90+360*pct,fill=col,width=20)
    for angle in (-90,-90+360*pct):
        a=math.radians(angle);x=cx+r*math.cos(a);y=cy+r*math.sin(a)
        d.ellipse((x-10,y-10,x+10,y+10),fill=col)
    right(410,rows[i]+7,n,62,col)
# Gallery badges show Apple's reference at its canonical time; live badges come from Wear OS.
ref=Image.open(root.parent/'表盘资料/健身记录数字/官方图1.png').convert('RGB')
for bounds,pos in [((53,48,124,119),(104,43)),((295,48,366,119),(314,43))]:
    im.paste(ref.crop(bounds).resize((62,62),Image.Resampling.LANCZOS),pos)
bottom=ref.crop((89,410,332,438)).resize((244,28),Image.Resampling.LANCZOS)
im.paste(bottom,(118,388))
im.save(art/'preview.png');im.save(root/'screenshots/gallery.png')

