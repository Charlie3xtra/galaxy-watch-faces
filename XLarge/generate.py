"""Generate the Galaxy round-screen X-Large face from the extracted 24S132 resources."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parent
FW = ROOT.parent / 'Watch8_5_24S132'
FRAME = 'System/Library/PrivateFrameworks/NanoTimeKit.framework'
PROPS = FW / '解析/属性表'
BUNDLE = PROPS / 'System/Library/NanoTimeKit/FaceBundles/NTKExtraLargeFaceBundle.bundle'
ASSETS = FW / '解析/图集' / FRAME / 'Assets.car/资源'
RES = ROOT/'res'
DRAW = RES/'drawable-nodpi'
DRAW.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(path.read_text('utf8'))

def add(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k:str(v) for k,v in attrs.items()})

def box(x,y,w,h):
    return dict(x=x,y=y,width=w,height=h)

def write(path, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)

ref = Image.open(ROOT.parent/'表盘资料/大文字/官方图1.png').convert('RGB')
purple = ref.getpixel((200,120))
def mask_crop(rect):
    a=np.asarray(ref.crop(rect))[:,:,0].astype(float)
    return Image.fromarray(np.uint8(np.clip(a*255/purple[0],0,255)))
references = {0:mask_crop((235,66,355,237)), 1:mask_crop((144,69,211,234)), 9:mask_crop((237,257,357,427))}
def glyph(font,n):
    mask=Image.new('L',(360,360))
    ImageDraw.Draw(mask).text((20,0),str(n),fill=255,font=font)
    return mask.crop(mask.getbbox())
# Compare complete silhouettes, including the counters, against the promotional image.
best=(2,None)
for filename,weights in [('SFCompactRounded.ttf',range(300,801,20)),('SFCompactRoundedNumeric.ttf',[0,1,2]),('SFCompactNumeric.ttf', [None])]:
    font=ImageFont.truetype(str(next((FW/'系统字体').rglob(filename))),220)
    for weight in weights:
        if weight is not None: font.set_variation_by_axes([weight])
        err=np.mean([np.abs(np.asarray(glyph(font,n).resize(m.size),float)-np.asarray(m,float)).mean()/255 for n,m in references.items()])
        if err<best[0]: best=(err,(filename,weight))
filename,weight=best[1]
font=ImageFont.truetype(str(next((FW/'系统字体').rglob(filename))),220)
if weight is not None: font.set_variation_by_axes([weight])
print('Font match:',filename,weight,'normalized mask error',round(best[0],3))
base=glyph(font,0)
masks={}
for n in range(10):
    raw=glyph(font,n)
    w=round(109*raw.width/base.width)
    h=round(154*raw.height/base.height)
    if n in references:
        raw=references[n]
        w,h=round(raw.width*.905),round(raw.height*.905)
    mask=raw.resize((w,h),Image.Resampling.LANCZOS)
    img=Image.new('RGBA',mask.size,'white')
    img.putalpha(mask)
    img.save(DRAW/f'digit_{n}.png')
    masks[n]=mask
mask=mask_crop((51,285,86,403)).resize((32,107),Image.Resampling.LANCZOS)
img=Image.new('RGBA',mask.size,'white')
img.putalpha(mask)
img.save(DRAW/'dots.png')
cfg=read(PROPS/FRAME/'FaceColors.color.plist.json')['shared-collections']
keys=['standard.'+n for n in cfg['standard']['items']]+['gossamer.'+n for n in read(PROPS/FRAME/'FaceColors-Gossamer.color.plist.json')['shared-collections']['gossamer']]
palette={'gallery':'#FF%02X%02X%02X'%purple}
for key in keys:
    path=next(ASSETS.glob(key.replace('.','_')+'-*.json'),None)
    if path:
        rgb=read(path)['Components'][:3]
        if len(rgb)==3: palette[key]='#FF'+''.join('%02X'%round(v*255) for v in rgb)
def label(key):
    return key.lower().replace('.','_')
for loc in BUNDLE.glob('*.lproj'):
    data=read(next(loc.glob('Localizable.strings.json')))
    code=loc.stem
    colors={}
    for path in (PROPS/FRAME/loc.name).glob('FaceColors*.strings.json'):
        colors.update(read(path))
    values={'face_name':data['EXTRA_LARGE_FACE_NAME_IN_TITLE_CASE'],'gallery':{'zh_CN':'官方预览','zh_TW':'官方預覽','zh_HK':'官方預覽'}.get(code,'10:09')}
    for name in palette:
        if name in colors: values[label(name)]=colors[name]
    if code=='en':
        for name in palette: values.setdefault(label(name),name.split('.')[-1])
    root=ET.Element('resources')
    for name,value in values.items():add(root,'string',name=name).text=value.replace("'","\\'")
    q={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for qual in [q]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        write(RES/f'values{qual}/strings.xml',root)

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
config=add(add(face,'UserConfigurations'),'ColorConfiguration',id='ink',displayName='ink_label',defaultValue='0')
for i,(key,color) in enumerate(palette.items()):
    add(config,'ColorOption',id=i,displayName=label(key),colors=color)
for p in RES.glob('values*/strings.xml'):
    # Use system-translated "Color" when present in the firmware's editor dictionary.
    code=p.parent.name
    tree=ET.parse(p).getroot()
    title={'values':'Color','values-zh':'颜色','values-zh-rCN':'颜色','values-b+zh+Hans':'颜色','values-zh-rTW':'顏色','values-zh-rHK':'顏色','values-b+zh+Hant':'顏色','values-ja':'カラー','values-ko':'색상','values-fr':'Couleur','values-de':'Farbe','values-es':'Color','values-it':'Colore','values-ru':'Цвет','values-pt':'Cor'}.get(code)
    if title: add(tree,'string',name='ink_label').text=title
    write(p,tree)
scene=add(face,'Scene',backgroundColor='#000000')
ink='[CONFIGURATION.ink.0]'
hour='([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])'
def ambient(element,alpha):
    add(element,'Variant',mode='AMBIENT',target='alpha',value=alpha)
group_index=0
def group(parent):
    global group_index
    group_index+=1
    return add(parent,'Group',name=f'layer{group_index}',**box(0,0,480,480))
large=group(scene)
ambient(large,67)
rows=[(hour,76),('[MINUTE]',249)]
preview=Image.new('RGB',(480,480))
for row,(source,y) in enumerate(rows):
    for tens,right in [(True,247),(False,369)]:
        condition=add(large,'Condition')
        expressions=add(condition,'Expressions')
        for n in (range(1,3) if not row and tens else range(6) if tens else range(10)):
            test=f'floor({source} / 10)' if tens else f'({source} % 10)'
            add(expressions,'Expression',name=f'n{n}').text=f'{test} == {n}'
            branch=add(condition,'Compare',expression=f'n{n}')
            m=masks[n]
            x=right-m.width
            top=y+(154-m.height)//2
            part=add(branch,'PartImage',**box(x,top,m.width,m.height),tintColor=ink)
            add(part,'Image',resource=f'digit_{n}')
            if n==((10,9)[row]//10 if tens else (10,9)[row]%10):
                preview.paste(purple,(x,top,x+m.width,top+m.height),m)
part=add(large,'PartImage',**box(90,272,32,107),tintColor=ink)
add(part,'Image',resource='dots')
preview.paste(purple,(90,272,122,379),mask)
preview.save(DRAW/'preview.png')
types=['SHORT_TEXT','MONOCHROMATIC_IMAGE','SMALL_IMAGE','PHOTO_IMAGE']
slot=add(scene,'ComplicationSlot',**box(0,0,480,480),slotId=1,supportedTypes='EMPTY '+' '.join(types))
add(slot,'BoundingOval',**box(12,12,456,456))
add(slot,'Complication',type='EMPTY')
for kind in types:
    g=group(add(slot,'Complication',type=kind))
    bg=add(g,'PartDraw',**box(0,0,480,480))
    add(add(bg,'Rectangle',**box(0,0,480,480)),'Fill',color='#000000')
    fg=group(g)
    ambient(fg,70)
    clock=add(fg,'DigitalClock',**box(72,57,336,96))
    t=add(clock,'TimeText',**box(0,0,336,96),format='h:mm',align='CENTER')
    add(t,'Font',family='SYNC_TO_DEVICE',size=76,color=ink)
    if kind=='SHORT_TEXT':
        part=add(fg,'PartImage',**box(188,174,104,104),tintColor=ink)
        add(part,'Image',resource='[COMPLICATION.MONOCHROMATIC_IMAGE]')
        part=add(fg,'PartText',**box(83,284,314,86))
        text=add(part,'Text',align='CENTER')
        f=add(text,'Font',family='SYNC_TO_DEVICE',size=52,color=ink)
        temp=add(f,'Template')
        temp.text='%s'
        add(temp,'Parameter',expression='[COMPLICATION.TEXT]')
    else:
        part=add(fg,'PartImage',**box(145,197,190,190),**({'tintColor':ink} if kind=='MONOCHROMATIC_IMAGE' else {}))
        add(part,'Image',resource=f'[COMPLICATION.{kind}]')
write(RES/'raw/watchface.xml',face)
print(len(palette),'colors')



