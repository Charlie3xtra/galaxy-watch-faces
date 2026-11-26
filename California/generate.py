"""Generate the round California dial from watchOS 24S132 and its gallery reference."""
import io, json, math, struct
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, ImageColor

root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132/解析'
if os.name=='nt':fw=Path('\\\\?\\'+str(fw))
core=Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
bundle='NTKCaliforniaFaceBundle'
assets=fw/'图集'/core/'Assets.car/资源'
labels=fw/'属性表/System/Library/NanoTimeKit/FaceBundles'/(bundle+'.bundle')
out=root/'res/drawable-nodpi'
out.mkdir(exist_ok=True,parents=True)
blob=(fw/'代码'/bundle/bundle).read_bytes()
pos=32
for _ in range(struct.unpack_from('<I',blob,16)[0]):
    cmd,length=struct.unpack_from('<II',blob,pos)
    if cmd==25:
        for i in range(struct.unpack_from('<I',blob,pos+64)[0]):
            name,seg,addr,size,off=struct.unpack_from('<16s16sQQI',blob,pos+72+i*80)
            if name.rstrip(b'\0')==b'__SFNumeralsB':
                facefont=blob[off:off+size]
    pos+=length

def el(node,tag,**a):return ET.SubElement(node,tag,{k:str(v) for k,v in a.items()})
def box(x=0,y=0,w=480,h=480):return dict(x=x,y=y,width=w,height=h)
def save(path,tree):
    path.parent.mkdir(exist_ok=True,parents=True);ET.indent(tree);ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def hexcolor(v):return '#'+''.join(f'{c:02X}' for c in v)
def pigment(key,fallback):
    path=next(assets.glob('california_'+key+'-*.json'),None)
    if not path:return fallback
    v=json.loads(path.read_text('utf8'))['Components']
    if len(v)==2:v=v[:1]*3+v[-1:]
    return hexcolor([round(v[i]*255) for i in [3,0,1,2]])
def mask(key,size,paint):
    scale=3;im=Image.new('L',(size[0]*scale,size[1]*scale))
    paint(ImageDraw.Draw(im),scale)
    white=Image.new('RGBA',size,'white');white.putalpha(im.resize(size,Image.Resampling.LANCZOS));white.save(out/(key+'.png'))
def tickmarks(d,s,major):
    for t in range(60):
        if (t%5==0)!=major:continue
        a=t*math.pi/30
        def pt(r):return ((240+r*math.sin(a))*s,(240-r*math.cos(a))*s)
        w=(5 if major else 4)*s
        p,q=pt(231),pt(217 if major else 223);d.line([p,q],255,w)
        for x,y in (p,q):d.ellipse((x-w/2,y-w/2,x+w/2,y+w/2),255)
for major,key in [(True,'large_ticks'),(False,'small_ticks')]:mask(key,(480,480),lambda d,s:tickmarks(d,s,major))
styles=['california','roman','numerals','pills','arabic','hindi']
def numerals(d,s,style):
    font=ImageFont.truetype(io.BytesIO(facefont),57*s)
    for i in range(12):
        n=i or 12;a=i*math.pi/6;x=(240+178*math.sin(a))*s;y=(240-178*math.cos(a))*s
        if style in ('california','pills') and i==0:
            # Rounded inverted triangle from the gallery's twelve-o'clock marker.
            points=[(x-21*s,y-17*s),(x+21*s,y-17*s),(x,y+24*s)]
            d.polygon(points,255);d.line(points+[points[0]],255,4*s,joint='curve');continue
        if style=='pills' or (style=='california' and i in (3,6,9)):
            w,h=(42,13) if (i in (3,6,9) or style=='california') else (11,26)
            if style=='pills' and i not in (3,6,9):
                dx,dy=math.sin(a)*10*s,-math.cos(a)*10*s
                d.line([(x-dx,y-dy),(x+dx,y+dy)],255,10*s)
                for xx,yy in ((x-dx,y-dy),(x+dx,y+dy)):d.ellipse((xx-5*s,yy-5*s,xx+5*s,yy+5*s),255)
            else:d.rounded_rectangle((x-w*s/2,y-h*s/2,x+w*s/2,y+h*s/2),radius=h*s/2,fill=255)
            continue
        if style=='roman' or (style=='california' and i in (1,2,10,11)):txt=chr(0x2160+n-1)
        else:
            txt=str(n)
            if style in ('arabic','hindi'):txt=''.join(chr((0x660 if style=='arabic' else 0x966)+int(c)) for c in txt)
        l,t,r,b=font.getbbox(txt);d.text((x-(l+r)/2,y-(t+b)/2),txt,font=font,fill=255)
for style in styles:mask('dial_'+style,(480,480),lambda d,s:numerals(d,s,style))
def hand(d,s,length,inlay):
    x=14*s; center=(length+4)*s
    if not inlay:d.line([(x,center),(x,center-20*s)],255,5*s)
    w=(8 if inlay else 14)*s
    d.rounded_rectangle((x-w/2,(7 if inlay else 4)*s,x+w/2,center-(24 if inlay else 20)*s),radius=w/2,fill=255)
for key,length in [('hour',98),('minute',177)]:
    for suffix,fill in [('',False),('_inlay',True)]:mask(key+suffix,(28,length+12),lambda d,s:hand(d,s,length,fill))
def second(d,s):
    d.line((9*s,3*s,9*s,227*s),255,3*s);d.ellipse((3*s,184*s,15*s,196*s),255)
mask('second',(18,230),second)
def argb(color,opacity):
    return hexcolor((round(opacity*255),))+color[3:]
def cap_value(color,maximum=150):
    rgb=bytes.fromhex(color[3:]);factor=min(1,maximum/max(1,max(rgb)))
    return hexcolor([255]+[round(c*factor) for c in rgb])
def primary(key):
    path=next(assets.glob(key+'-*.json'))
    components=json.loads(path.read_text('utf8'))['Components']
    return hexcolor([255]+[round(v*255) for v in components[:3]])
palettes=[]
for code in ['standard_cream','evergreen_black','seasons_fall2021_stardust','seasons_fall2021_blue11','seasons_fall2021_green3','seasons_fall2021_red2sg']:
    def color(k,f):return pigment(code+'_'+k,f)
    main=primary(code)
    evergreen=code.startswith('evergreen_')
    bg=color('circularBackground',pigment('circularBackground',main))
    ink=color('digit',main)
    major=color('largeTick',argb(ink,.7 if evergreen else .9))
    # With no bezel complication the circle asks for smallTickCircular;
    # its normal method falls back to _smallTick, independently of smallTick assets.
    minor=color('smallTickCircular',argb(ink,.2 if evergreen else .4))
    edge=color('clockHands','#FFFFFFFF')
    inlay=color('clockHandsInlay',pigment('clockHandsInlay','#FF000000'))
    active=[bg,ink,major,minor,edge,inlay,color('simpleTextComplication',ink)]
    bezel=color('bezelComplication',main)
    night_ink=color('digit.tritium',cap_value(bezel) if evergreen else ink)
    night_major=color('largeTick.tritium',argb(night_ink,.5) if evergreen else major)
    night_minor=color('smallTickCircular.tritium',minor)
    night_text=color('simpleTextComplication.tritium',night_ink if evergreen else active[6])
    # Use the firmware's vibrancy-capable device branch for the hands.
    ambient=[pigment('background.tritium','#FF000000'),night_ink,night_major,night_minor,'#FFFFFFFF','#FF000000',night_text]
    palettes.append((code,active,ambient))
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=el(face,'UserConfigurations')
colors=el(cfg,'ColorConfiguration',id='palette',displayName='color',defaultValue='0')
for i,(_,p,night) in enumerate(palettes):el(colors,'ColorOption',id=i,displayName='color_'+str(i),colors=' '.join(p[:2]))
numbers=el(cfg,'ListConfiguration',id='numbers',displayName='numbers',defaultValue='california')
for st in styles:el(numbers,'ListOption',id=st,displayName=st)
scene=el(face,'Scene',backgroundColor='#000000')
def image(parent,key,tint):
    part=el(parent,'PartImage',**box(),tintColor=tint);el(part,'Image',resource=key)
def dial(parent,tint):
    opts=el(parent,'ListConfiguration',id='numbers')
    for st in styles:image(el(opts,'ListOption',id=st),'dial_'+st,tint)
def render(parent,p,aod):
    base,ink,large,small,edge,inlay,dim=p
    el(el(el(parent,'PartDraw',**box()),'Rectangle',**box()),'Fill',color=base)
    image(parent,'small_ticks',small);image(parent,'large_ticks',large);dial(parent,argb(ink,200/255) if aod else ink)
def hands(parent,p,aod):
    clk=el(parent,'AnalogClock',**box())
    for tag,key,length in [('HourHand','hour',98),('MinuteHand','minute',177)]:
        for suffix,col in [('',p[4]),('_inlay',p[5])]:
            el(clk,tag,resource=key+suffix,x=226,y=236-length,width=28,height=length+12,pivotX='.5',pivotY=(length+4)/(length+12),tintColor=col)
    if not aod:el(el(clk,'SecondHand',resource='second',x=231,y=50,width=18,height=230,pivotX='.5',pivotY=190/230,tintColor=pigment('secondHand','#FFFF3B30')),'Sweep',frequency=15)
def variants(parent,fn):
    cond=el(parent,'Condition');exp=el(cond,'Expressions')
    for i,(_,p,night) in enumerate(palettes):
        key=f'p{i}';el(exp,'Expression',name=key).text=f'[CONFIGURATION.palette.0] == {p[0]} && [CONFIGURATION.palette.1] == {p[1]}'
        case=el(cond,'Compare',expression=key)
        for aod in (False,True):
            g=el(case,'Group',name=f'{fn.__name__}_{i}_{int(aod)}',**(box(0,0,156,52) if fn.__name__=='complication' else box()),alpha=0 if aod else 255)
            el(g,'Variant',mode='AMBIENT',target='alpha',value=255 if aod else 0);fn(g,night if aod else p,aod)
variants(scene,render)
slot=el(scene,'ComplicationSlot',slotId=1,displayName='date',supportedTypes='SHORT_TEXT EMPTY',**box(162,119,156,52))
el(slot,'BoundingRoundBox',**box(0,0,156,52),cornerRadius=12)
el(slot,'DefaultProviderPolicy',defaultSystemProvider='DATE',defaultSystemProviderType='SHORT_TEXT')
comp=el(slot,'Complication',type='SHORT_TEXT')
def complication(parent,p,aod):
    pt=el(parent,'PartText',**box(0,0,156,52))
    text=el(pt,'Text',align='CENTER')
    font=el(text,'Font',family='SYNC_TO_DEVICE',size=30,weight='BOLD',color=p[6])
    tpl=el(font,'Template');tpl.text='%s';el(tpl,'Parameter',expression='[COMPLICATION.TEXT]')
variants(comp,complication)
variants(scene,hands);save(root/'res/raw/watchface.xml',face)
for loc in labels.glob('*.lproj'):
    strings=json.loads((loc/'Localizable.strings.json').read_text('utf8'))
    common=fw/'属性表'/core/loc.name
    clock=json.loads((common/'ClockFaces.strings.json').read_text('utf8'))
    names=json.loads((common/'FaceColors.strings.json').read_text('utf8')) if (common/'FaceColors.strings.json').exists() else {}
    tree=ET.Element('resources');v={'face_name':strings['FACE_STYLE_CALIFORNIA_IN_TITLE_CASE'],'numbers':clock.get('EDIT_MODE_LABEL_NUMERALS','Numerals'),'color':clock.get('EDIT_MODE_LABEL_COLOR','Color'),'date':clock.get('EDIT_MODE_LABEL_COMPLICATION',clock.get('EDIT_OPTION_LABEL_DATE',{'zh_CN':'日期','zh_TW':'日期','zh_HK':'日期'}.get(loc.stem,'Date')))}
    for st in styles:v[st]=strings['EDIT_OPTION_LABEL_CALIFORNIA_STYLE_'+st.upper()]
    for i,(code,p,night) in enumerate(palettes):
        key=code.replace('_','.');v['color_'+str(i)]=names.get(key,names.get('black' if i==1 else key,code.rsplit('_',1)[-1]))
    for k,val in v.items():el(tree,'string',name=k).text=val.replace("'","\\'")
    code=loc.stem;q={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for suffix in [q]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):save(root/('res/values'+suffix)/'strings.xml',tree)
def preview(p,ambient):
    def rgb(argb):return ImageColor.getrgb('#'+argb[3:])
    prev=Image.new('RGBA',(480,480),rgb(p[0]))
    def stamp(key,pos,col,angle=0):
        im=Image.open(out/(key+'.png'));ink=Image.new('RGBA',im.size,rgb(col))
        alpha=int(col[1:3],16)/255
        ink.putalpha(im.getchannel('A').point(lambda x:round(x*alpha)))
        layer=Image.new('RGBA',prev.size);layer.alpha_composite(ink,pos)
        prev.alpha_composite(layer.rotate(-angle,Image.Resampling.BICUBIC,center=(240,240)) if angle else layer)
    for k,c in [('small_ticks',p[3]),('large_ticks',p[2]),('dial_california',argb(p[1],200/255) if ambient else p[1])]:stamp(k,(0,0),c)
    ImageDraw.Draw(prev).text((240,145),'27',font=ImageFont.truetype(io.BytesIO(facefont),30),fill=rgb(p[6]),anchor='mm')
    for k,l,ang in [('hour',98,304.5),('minute',177,54)]:
        for suffix,col in [('',p[4]),('_inlay',p[5])]:stamp(k+suffix,(226,236-l),col,ang)
    if not ambient:stamp('second',(231,50),'#FFFF3B30',180)
    alpha=Image.new('L',prev.size);ImageDraw.Draw(alpha).ellipse((0,0,479,479),255);prev.putalpha(alpha)
    return prev
preview(palettes[0][1],False).save(out/'preview.png')
