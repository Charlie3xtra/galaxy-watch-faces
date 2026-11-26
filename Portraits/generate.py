"""Generate WFF Portraits. Requires Pillow, pillow-heif and the unpacked 24S132 firmware."""
import json,os,plistlib
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageStat
import pillow_heif
import xml.etree.ElementTree as ET
pillow_heif.register_heif_opener()
root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132'
if os.name=='nt':fw=Path('\\\\?\\'+str(fw))
bundle=Path('System/Library/NanoTimeKit/FaceBundles/NTKUltraCubeFaceBundle.bundle')
res=root/'res';draw=res/'drawable-nodpi';draw.mkdir(parents=True,exist_ok=True)
def add(p,t,**a):return ET.SubElement(p,t,{k:str(v) for k,v in a.items()})
def box(x=0,y=0,w=480,h=480):return dict(x=x,y=y,width=w,height=h)
def save(p,e):
    p.parent.mkdir(parents=True,exist_ok=True);ET.indent(e);ET.ElementTree(e).write(p,encoding='utf-8',xml_declaration=True)
def image(p,key,rect):
    part=add(p,'PartImage',**rect);add(part,'Image',resource=key);return part
def move(p,strength):
    for axis,start in [('X',-16),('Y',-16)]:
        t=add(p,'Transform',target=axis.lower(),value=f'{start} + clamp([ACCELEROMETER_{axis}],-6,6)*{strength}')
        add(t,'Animation',duration='.16',interpolation='EASE_OUT',fps=30)
def opts(p,key,options):
    config=add(p,'ListConfiguration',id=key)
    return [(v,add(config,'ListOption',id=v)) for v in options]
def choice(p,key,label,items,default):
    config=add(p,'ListConfiguration',id=key,displayName=label,defaultValue=default)
    for v in items:add(config,'ListOption',id=v,displayName=v)
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=add(face,'UserConfigurations')
samples=sorted((fw/'filesystem'/bundle/'SampleResourceDirectories').iterdir())
ids=[f'photo{i:02}' for i in range(1,len(samples)+1)]
styles=['modern','classic','rounded'];effects=['natural','background','duotone']
choice(cfg,'album','photos',ids+['personal'],ids[0]);choice(cfg,'font','typeface',styles,'modern')
choice(cfg,'effect','effect_label',effects,'natural');add(cfg,'PhotosConfiguration',id='user_photos',configType='MULTIPLE')
fonts=add(face,'BitmapFonts');digits={}
for key,file in zip(styles,['SFCompact.ttf','NewYork.ttf','SFCompactRounded.ttf']):
    f=ImageFont.truetype(str(next((fw/'系统字体').rglob(file))),260)
    axes=f.get_variation_axes();f.set_variation_by_axes([min(a['maximum'],max(a['minimum'],700)) if a['name']==b'Weight' else a['default'] for a in axes])
    spec=add(fonts,'BitmapFont',name=key);digits[key]={}
    for ch in '0123456789:':
        b=f.getbbox(ch);im=Image.new('L',(b[2]-b[0],b[3]-b[1]));ImageDraw.Draw(im).text((-b[0],-b[1]),ch,font=f,fill=255)
        im=im.crop(im.getbbox());s=80/(f.getbbox('0')[3]-f.getbbox('0')[1]);im=im.resize(tuple(max(1,round(t*s)) for t in im.size),Image.Resampling.LANCZOS)
        tile=Image.new('L',(im.width+3,92));tile.paste(im,(1,(92-im.height)//2));digits[key][ch]=tile
        asset=key+('_colon' if ch==':' else ch);out=Image.new('RGBA',tile.size,'white');out.putalpha(tile);out.save(draw/(asset+'.png'))
        for v in ([ch,chr(0x660+int(ch)),chr(0x6f0+int(ch))] if ch.isdigit() else [ch]):
            add(spec,'Character',name=v,resource=asset,width=tile.width,height=92)
def time(p,top):
    date=add(p,'PartText',**box(80,top-32,320,32));ft=add(add(date,'Text',align='CENTER'),'Font',family='SYNC_TO_DEVICE',size=21,color='#FFFFFFFF',weight='MEDIUM')
    t=add(ft,'Template');t.text='%s %s';add(t,'Parameter',expression='[DAY_OF_WEEK_S]');add(t,'Parameter',expression='[DAY]')
    for style,option in opts(p,'font',styles):
        option=add(option,'Group',name='type_'+style,**box())
        for shadow in (True,False):
            holder=add(option,'Group',name=f'{style}_{int(shadow)}',**box())
            clock=add(holder,'DigitalClock',**box(0,top+(2 if shadow else 0),480,100))
            txt=add(clock,'TimeText',**box(0,0,480,100),format='h:mm',align='CENTER')
            add(txt,'BitmapFont',family=style,size=92,color='#83000000' if shadow else '#FFFFFFFF')
def dim(p,brightness):
    overlay=add(p,'PartDraw',**box(),alpha=0)
    add(overlay,'Variant',mode='AMBIENT',target='alpha',value=round(255*(1-brightness)))
    add(add(overlay,'Rectangle',**box()),'Fill',color='#FF000000')
def ramp(im):
    return ImageOps.colorize(ImageOps.grayscale(im),'#172639','#E8C7A4')
def scene_layer(p,sid,front):
    # Use the same coordinate system for the inpainted background and the subject.
    options=opts(p,'effect',effects)
    for effect,option in options:
        variant=('tone' if (effect=='duotone' or (effect=='background' and not front)) else 'raw')
        group=add(option,'Group',name=f'{sid}_{effect}_{int(front)}',**box(-16,-16,512,512))
        move(group,1.05 if front else -.36)
        image(group,sid+('_fg_' if front else '_bg_')+variant,box(0,0,512,512))
scene=add(face,'Scene',backgroundColor='#000000')
for idx,(sid,opt) in enumerate(opts(scene,'album',ids+['personal'])):
    if sid=='personal':
        opt=add(opt,'Group',name='personal_album',**box())
        part=add(opt,'PartImage',**box());add(part,'Photos',source='[CONFIGURATION.user_photos]',defaultImageResource='placeholder',change='TAP ON_VISIBLE',changeAfterEvery=3)
        time(opt,85);dim(opt,.28);continue
    folder=samples[idx];meta=plistlib.loads((folder/'Images.plist').read_bytes())['imageList'][0]
    base=Image.open(folder/meta['baseImageURL']).convert('RGB')
    back=Image.open(folder/meta['backgroundImageURL']).convert('RGB')
    mask=Image.open(folder/meta['maskImageURL']).convert('L')
    # Keep the square crop high enough to retain the negative space above the subject.
    w,h=base.size;top=round((h-w)*.25);crop=(0,top,w,top+w)
    base,back,mask=[im.crop(crop).resize((512,512),Image.Resampling.LANCZOS) for im in (base,back,mask)]
    baseline=round((meta['timeElementUnitBaseline']*h-top)*512/w)-16
    y=max(65,min(94,baseline-85))
    # Check each digit region; a large head may hide an entire digit at Apple's rectangular baseline.
    while y>65:
        if max(ImageStat.Stat(mask.crop((x+16,y+22,x+66,y+92))).mean[0] for x in (120,175,248,303))<91:break
        y-=2
    for variant,bg,fg in [('raw',back,base),('tone',ramp(back),ramp(base))]:
        bg.save(draw/(sid+'_bg_'+variant+'.webp'),quality=92,method=4)
        subject=fg.convert('RGBA');subject.putalpha(mask);subject.save(draw/(sid+'_fg_'+variant+'.webp'),quality=94,method=4)
    layer=add(opt,'Group',name=sid,**box());scene_layer(layer,sid,False)
    time(layer,y);scene_layer(layer,sid,True)
    dim(layer,.18+.14*meta['imageAOTBrightness'])
    if idx==0:
        prev=back.convert('RGBA')
        d=ImageDraw.Draw(prev);d.text((256,y-1),'MON 7',fill='white',anchor='mm',font=ImageFont.truetype(str(next((fw/'系统字体').rglob('SFCompact.ttf'))),21))
        x=256-sum(digits['modern'][ch].width for ch in '10:09')//2
        for ch in '10:09':
            stamp=digits['modern'][ch];prev.paste('white',(x,y+16,x+stamp.width,y+16+stamp.height),stamp);x+=stamp.width
        prev.paste(base,(0,0),mask);prev=prev.crop((16,16,496,496));circle=Image.new('L',(480,480));ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255);prev.putalpha(circle);prev.save(draw/'preview.png')
        base.resize((300,300)).save(draw/'placeholder.webp',quality=78)
save(res/'raw/watchface.xml',face)
for loc in (fw/'解析/属性表'/bundle).glob('*.lproj'):
    data=json.loads((loc/'Localizable.strings.json').read_text('utf8'))
    clock=json.loads((fw/'解析/属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/loc.name/'ClockFaces.strings.json').read_text('utf8'))
    labels={'face_name':data['FACE_STYLE_ULTRACUBE_IN_TITLE_CASE'],'photos':clock['EDIT_MODE_LABEL_PHOTO_CONTENT'],'typeface':data['EDIT_MODE_LABEL_TYPEFACE'],'effect_label':clock.get('EDIT_MODE_LABEL_COLOR','Color')}
    for k,v in zip(styles,['SAN_FRANCISCO','NEW_YORK','TOKYO']):labels[k]=data['EDIT_OPTION_LABEL_TYPEFACE_'+v]
    for k,v in zip(effects,['NONE','BACKGROUND','DUOTONE']):labels[k]=data['EDIT_OPTION_LABEL_EFFECT_'+v]
    labels['personal']={'zh_CN':'个人照片','zh_TW':'個人照片','zh_HK':'個人相片','en':'My photos'}.get(loc.stem,clock['EDIT_MODE_LABEL_PHOTO_CONTENT'])
    for i,key in enumerate(ids,1):labels[key]=f'{labels["photos"]} {i:02}'
    tree=ET.Element('resources')
    for k,v in labels.items():add(tree,'string',name=k).text=v.replace("'","\\'")
    code=loc.stem;q={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for suffix in [q]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):save(res/('values'+suffix)/'strings.xml',tree)
