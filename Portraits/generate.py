"""Generate WFF Portraits. Requires Pillow and the unpacked 24S132 firmware."""
import json,os
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import xml.etree.ElementTree as ET
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
def opts(p,key,options):
    config=add(p,'ListConfiguration',id=key)
    return [(v,add(config,'ListOption',id=v)) for v in options]
def choice(p,key,label,items,default):
    config=add(p,'ListConfiguration',id=key,displayName=label,defaultValue=default)
    for v in items:add(config,'ListOption',id=v,displayName=v)
face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=add(face,'UserConfigurations')
styles=['modern','classic','rounded'];effects=['natural','background','duotone']
choice(cfg,'font','typeface',styles,'modern')
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
scene=add(face,'Scene',backgroundColor='#000000')
base=Image.open(root/'assets/dog.webp').resize((480,480),Image.Resampling.LANCZOS)
mask=Image.open(root/'assets/subject.png').resize(base.size,Image.Resampling.LANCZOS)
tone=ramp(base)
for name,bg in [('natural',base),('background',Image.composite(base,tone,mask)),('duotone',tone)]:
    bg.save(draw/('dog_'+name+'.webp'),quality=94)
for name,option in opts(scene,'effect',effects):
    image(option,'dog_'+name,box())
time(scene,57)
for variant,fg in [('raw',base),('tone',tone)]:
    layer=fg.convert('RGBA');layer.putalpha(mask);layer.save(draw/('subject_'+variant+'.webp'),quality=94)
for name,option in opts(scene,'effect',effects):
    image(option,'subject_'+('tone' if name=='duotone' else 'raw'),box())
Image.new('RGBA',(1,1)).save(draw/'empty_photo.png')
album=add(scene,'Group',name='personal_album',**box())
part=add(album,'PartImage',renderMode='ALL',**box())
add(part,'Photos',source='[CONFIGURATION.user_photos]',defaultImageResource='empty_photo',change='TAP ON_VISIBLE',changeAfterEvery=3)
time(album,57)
dim(scene,.28)
prev=base.convert('RGBA')
d=ImageDraw.Draw(prev);d.text((240,41),'MON 7',fill='white',anchor='mm',font=ImageFont.truetype(str(next((fw/'系统字体').rglob('SFCompact.ttf'))),21))
x=240-sum(digits['modern'][ch].width for ch in '10:09')//2
for ch in '10:09':
    stamp=digits['modern'][ch];prev.paste('white',(x,61,x+stamp.width,61+stamp.height),stamp);x+=stamp.width
prev.paste(base,(0,0),mask);circle=Image.new('L',base.size);ImageDraw.Draw(circle).ellipse((0,0,479,479),fill=255);prev.putalpha(circle);prev.save(draw/'preview.png')
save(res/'raw/watchface.xml',face)
for loc in (fw/'解析/属性表'/bundle).glob('*.lproj'):
    data=json.loads((loc/'Localizable.strings.json').read_text('utf8'))
    clock=json.loads((fw/'解析/属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/loc.name/'ClockFaces.strings.json').read_text('utf8'))
    labels={'face_name':data['FACE_STYLE_ULTRACUBE_IN_TITLE_CASE'],'photos':clock['EDIT_MODE_LABEL_PHOTO_CONTENT'],'typeface':data['EDIT_MODE_LABEL_TYPEFACE'],'effect_label':clock.get('EDIT_MODE_LABEL_COLOR','Color')}
    for k,v in zip(styles,['SAN_FRANCISCO','NEW_YORK','TOKYO']):labels[k]=data['EDIT_OPTION_LABEL_TYPEFACE_'+v]
    for k,v in zip(effects,['NONE','BACKGROUND','DUOTONE']):labels[k]=data['EDIT_OPTION_LABEL_EFFECT_'+v]
    tree=ET.Element('resources')
    for k,v in labels.items():add(tree,'string',name=k).text=v.replace("'","\\'")
    code=loc.stem;q={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for suffix in [q]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):save(res/('values'+suffix)/'strings.xml',tree)

