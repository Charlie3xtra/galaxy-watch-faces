"""Build the circular Squall dial from watchOS 24S132 fonts, wordmark and palette."""
from pathlib import Path
from io import BytesIO
import math, struct, json
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132/解析'
bundle=Path('System/Library/NanoTimeKit/FaceBundles/NTKSquallFaceBundle.bundle')
assets=fw/'图集'/bundle/'Assets.car/资源'
props=fw/'属性表'/bundle
res=root/'face/res'; host=root/'engine/res'
draw=res/'drawable-nodpi';draw.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text('utf8'))
def add(p,t,**a):return ET.SubElement(p,t,{k:str(v) for k,v in a.items()})
def box(x=0,y=0,w=480,h=480):return dict(x=x,y=y,width=w,height=h)
def save(p,e):
    p.parent.mkdir(parents=True,exist_ok=True);ET.indent(e);ET.ElementTree(e).write(p,encoding='utf-8',xml_declaration=True)
def color(name):
    c=read(next(assets.glob('squall_'+name+'-*.json')))['Components']
    if len(c)==2:c=c[:1]*3+c[1:]
    return '#'+''.join(f'{max(0,min(255,round(c[i]*255))):02X}' for i in (3,0,1,2))
def bitmap(mask,key):
    i=Image.new('RGBA',mask.size,'white');i.putalpha(mask);i.save(draw/(key+'.png'))
logo=Image.open(next(assets.glob('hermes-logo*'))).convert('RGBA').getchannel('A')
bitmap(logo,'wordmark')
b=(fw/'代码/NTKSquallFaceBundle/NTKSquallFaceBundle').read_bytes()
def loadfont(section):
    i=b.index(section+b'\0');_,size,pos=struct.unpack_from('<QQI',b,i+32)
    return ImageFont.truetype(BytesIO(b[pos:pos+size]),380)
for style,sec in [('day',b'__SquallFontV'),('night',b'__SquallFontL')]:
    f=loadfont(sec)
    if style=='night':f.set_variation_by_axes([90,1])
    for n in range(60):
        for s in {str(n),f'{n:02}'}:
            bounds=f.getbbox(s);im=Image.new('L',(bounds[2]-bounds[0],bounds[3]-bounds[1]))
            ImageDraw.Draw(im).text((-bounds[0],-bounds[1]),s,font=f,fill=255)
            im=im.crop(im.getbbox());im=im.resize((round(im.width*137/im.height),137),Image.Resampling.LANCZOS)
            tile=Image.new('L',(264,148));tile.paste(im,((264-im.width)//2,(148-im.height)//2));bitmap(tile,style+s)
def ring(p,col,fraction='1'):
    part=add(p,'PartDraw',**box());a=add(part,'Arc',centerX=240,centerY=240,width=444,height=444,startAngle=0,endAngle=360)
    if fraction!='1':add(a,'Transform',target='endAngle',value=f'360 * clamp({fraction},0,1)')
    add(a,'Stroke',color=col,thickness=21)
def paint(p,col):
    rect=add(add(p,'PartDraw',**box()),'Rectangle',**box());add(rect,'Fill',color=col)
def pic(p,src,rect,col):
    add(add(p,'PartImage',**rect,tintColor=col),'Image',resource=src)
def text(p,rect,size,col,pattern,*args):
    race=pattern=='%02d:%02d'
    f=add(add(add(p,'PartText',**rect),'Text',align='CENTER'),'BitmapFont' if race else 'Font',
          family='race_digits' if race else 'SYNC_TO_DEVICE',size=size,color=col)
    if args:
        t=add(f,'Template');t.text=pattern
        for a in args:add(t,'Parameter',expression=a)
    else:f.text=pattern
def cond(p,expr):
    c=add(p,'Condition');add(add(c,'Expressions'),'Expression',name='test').text=expr
    return add(c,'Compare',expression='test'),add(c,'Default')
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=add(add(face,'UserConfigurations'),'ColorConfiguration',id='palette',displayName='color',defaultValue=0)
for i,k in enumerate(('noir','blanc')):
    fields=['background' if not i else 'blanc_background',k+'_hourNumeralsFill',k+'_bezelDimmed',k+'_bezelHighlighted',k+'_logoDimmed',k+'_logoHighlighted',k+'_bezelHighlightedFinal',k+'_bezelCountUpHighlighted']
    add(cfg,'ColorOption',id=i,displayName=k,colors=' '.join(map(color,fields[:5])))
def col(i):return f'[CONFIGURATION.palette.{i}]' if i<5 else {5:'#FF071518',6:color('noir_bezelHighlightedFinal'),7:color('noir_bezelCountUpHighlighted')}[i]
racefont=add(add(face,'BitmapFonts'),'BitmapFont',name='race_digits')
font=loadfont(b'__SquallFontV')
for char in '0123456789:':
    bounds=font.getbbox(char);im=Image.new('L',(bounds[2]-bounds[0],bounds[3]-bounds[1]))
    ImageDraw.Draw(im).text((-bounds[0],-bounds[1]),char,font=font,fill=255)
    im=im.crop(im.getbbox());scale=76/(font.getbbox('0')[3]-font.getbbox('0')[1])
    im=im.resize(tuple(max(1,round(v*scale)) for v in im.size),Image.Resampling.LANCZOS)
    cell=Image.new('L',(im.width+4,84));cell.paste(im,(2,(84-im.height)//2))
    name='race_'+('colon' if char==':' else char);bitmap(cell,name)
    add(racefont,'Character',name=char,resource=name,width=cell.width,height=84)
scene=add(face,'Scene',backgroundColor='#000000')
for night in (False,True):
    p=add(scene,'Group',name='ambient' if night else 'daytime',**box(),alpha=0 if night else 255)
    add(p,'Variant',mode='AMBIENT',target='alpha',value=255 if night else 0)
    paint(p,'#FF000000' if night else col(0))
    ring(p,'#FF123441' if night else col(2))
    if not night:ring(p,col(3),'[SECOND_MILLISECOND]/60')
    for hour,y in [(True,86 if not night else 95),(False,235 if not night else 229)]:
        exp='([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])' if hour else '[MINUTE]'
        c=add(p,'Condition');ex=add(c,'Expressions')
        for i in range(24 if hour else 60):
            key=f'n{i}';add(ex,'Expression',name=key).text=f'{exp} == {i}'
            ink=(color('hourNumeralsFillLinked' if hour else 'minuteNumeralsFillLinked') if night else col(1))
            pic(add(c,'Compare',expression=key),('night' if night else 'day')+(str(i) if hour else f'{i:02}'),box(108,y,264,148),ink)
    if night:pic(p,'wordmark',box(12,197,11,86),'#FF4295BC')
    else:
        lit,dim=cond(p,'[SECOND] >= 45')
        for layer,idx in ((lit,5),(dim,4)):pic(layer,'wordmark',box(12,197,11,86),col(idx))
slot=add(scene,'ComplicationSlot',**box(),slotId=1,displayName='face_name',supportedTypes='RANGED_VALUE EMPTY')
add(slot,'DefaultProviderPolicy',primaryProvider='local.hermes.maritime/local.hermes.maritime.RaceProvider',primaryProviderType='RANGED_VALUE',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
add(slot,'BoundingOval',**box());add(slot,'Complication',type='EMPTY')
c=add(slot,'Complication',type='RANGED_VALUE')
active,_=cond(c,'[COMPLICATION.TEXT] == "running" || [COMPLICATION.TEXT] == "paused" || [COMPLICATION.TEXT] == "overtime"')
mn='[COMPLICATION.RANGED_VALUE_MIN]';mx='[COMPLICATION.RANGED_VALUE_MAX]';v='[COMPLICATION.RANGED_VALUE_VALUE]'
def race_layer(parent,theme,night):
    p=add(parent,'Group',name='race_'+theme+str(int(night)),**box(),alpha=255 if not night else 0)
    add(p,'Variant',mode='AMBIENT',target='alpha',value=255 if night else 0)
    paint(p,'#FF000000' if night else color('background' if theme=='noir' else 'blanc_background'))
    content=add(p,'Group',name='readout_'+theme+str(int(night)),**box(),alpha=95 if night else 255)
    ring(content,'#FF27323A' if night else color(theme+'_bezelDimmed'))
    running,paused=cond(content,'[COMPLICATION.TEXT] == "running"')
    before,after=cond(paused,'[COMPLICATION.TEXT] == "paused"')
    for view,left,span in [(running,f'(({v}-([SECONDS_SINCE_EPOCH]%86400))-(floor([SECONDS_SINCE_EPOCH]/86400)+{mn})*86400)',f'({mx}-86400)'),(before,v,f'(-{mn})'),(after,f'(-{v})',f'(-{mn})')]:
        down,up=cond(view,left+' > 0')
        for layer,ink,fraction in [(down,color(theme+'_bezelHighlighted'),f'({left})/({span})'),(up,color(theme+'_bezelCountUpHighlighted'),f'1.0*(abs({left})%60)/60.0')]:
            if layer is down:
                final,normal=cond(layer,left+' <= 60')
                ring(final,color(theme+'_bezelHighlightedFinal'),f'({left})/60.0');ring(normal,ink,fraction)
            else:ring(layer,ink,fraction)
            fg='#FFFFFFFF' if night else color(theme+('_numeralsFill' if layer is down else '_numeralsCountUpFill'))
            text(layer,box(58,161,364,125),82,fg,'%02d:%02d',f'floor(abs({left})/60)',f'floor(abs({left})%60)')
    text(content,box(115,120,250,44),25,'#FFADBFC9' if night else color(theme+'_smallTime'),'%s:%s',
         '([IS_24_HOUR_MODE] ? [HOUR_0_23_Z] : [HOUR_1_12])','[MINUTE_Z]')
    paused,_=cond(content,'[COMPLICATION.TEXT] != "running"');text(paused,box(105,303,270,52),22,color(theme+'_pausedLabel'),'@string/paused')
dark,light=cond(active,col(0)+' == #FF000000')
for branch,theme in ((dark,'noir'),(light,'blanc')):
    for night in (False,True):race_layer(branch,theme,night)
for condition in face.iter('Condition'):
    fallback=condition.find('Default')
    if fallback is not None and len(fallback)==0:condition.remove(fallback)
save(res/'raw/watchface.xml',face)
prev=Image.new('RGBA',(480,480));d=ImageDraw.Draw(prev);d.ellipse((0,0,479,479),fill='black')
d.ellipse((8,8,472,472),outline='#002F4C',width=21);d.arc((8,8,472,472),-90,90,fill='#009EFF',width=21)
for s,y in [('10',86),('09',235)]:prev.paste('white',(108,y,372,y+148),Image.open(draw/('day'+s+'.png')).getchannel('A'))
prev.paste('#FF6700',(12,197,23,283),logo.resize((11,86),Image.Resampling.LANCZOS))
for folder in (res,host):
    (folder/'drawable-nodpi').mkdir(exist_ok=True,parents=True);prev.save(folder/'drawable-nodpi/preview.png')
for path in props.glob('*.lproj'):
    lab=read(path/'Localizable.strings.json')
    core=fw/'属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/path.name
    colors=read(core/'FaceColors.strings.json');clock=read(core/'ClockFaces.strings.json')
    keys={'face_name':lab['FACE_STYLE_SQUALL_IN_TITLE_CASE'],'color':clock['EDIT_MODE_LABEL_COLOR'],'noir':colors.get('noir',colors.get('black','Noir')),'blanc':colors.get('blanc',colors.get('white','Blanc'))}
    for k in ('start','resume','sync','reset','pause'):keys[k]=lab['SQUALL_ACTION_BUTTON_'+k.upper()]
    keys.update(minutes=lab['SQUALL_PICKER_MINUTES'],paused=lab['SQUALL_PAUSED_VIEW_STATE_PAUSED'])
    code=path.stem;suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        for target in (res,host):
            tree=ET.Element('resources')
            if target==host:
                source=root.parent/'Artist/v4/engine/res'/('values'+q)/'strings.xml'
                if source.exists():
                    for old in ET.parse(source).getroot():
                        if old.get('name') in ('setup_error','retry','manual_selection'):tree.append(old)
            for k,v in keys.items():add(tree,'string',name=k).text=v.replace("'","\\'")
            save(target/('values'+q)/'strings.xml',tree)
