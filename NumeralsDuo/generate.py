"""Generate Numerals Duo from the watchOS 24S132 embedded OpenType fonts and palette."""
from pathlib import Path
from io import BytesIO
import json
import struct
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
RES = ROOT / 'res'
DRAW = RES / 'drawable-nodpi'
DRAW.mkdir(parents=True, exist_ok=True)
FW = ROOT.parent / 'Watch8_5_24S132/解析'
BUNDLE = 'NTKBigNumeralsDigitalFaceBundle'
FRAME = Path('System/Library/PrivateFrameworks/NanoTimeKit.framework')
PROPS = FW / '属性表' / FRAME
FACE = FW / '属性表/System/Library/NanoTimeKit/FaceBundles' / (BUNDLE + '.bundle')
ASSETS = FW / '图集' / FRAME / 'Assets.car/资源'

def read(path):
    return json.loads(path.read_text('utf8'))

def sub(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})

def write(path,tree):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path, encoding='utf-8',xml_declaration=True)

def box(x,y,w,h):
    return dict(x=x,y=y,width=w,height=h)

def fonts():
    blob=(FW/'代码'/BUNDLE/BUNDLE).read_bytes()
    offset=32
    for _ in range(struct.unpack_from('<I',blob,16)[0]):
        cmd,length=struct.unpack_from('<II',blob,offset)
        if cmd==25:
            for j in range(struct.unpack_from('<I',blob,offset+64)[0]):
                name,seg,_,size,pos=struct.unpack_from('<16s16sQQI',blob,offset+72+j*80)
                if seg.rstrip(b'\0')==b'__FONT_DATA':
                    yield name.rstrip(b'\0').decode(),blob[pos:pos+size]
        offset+=length

def asset_color(key):
    path=next(ASSETS.glob(key.replace('.','_')+'-*.json'),None)
    if path:
        c=read(path)['Components']
        if len(c)==4:
            return '#FF'+''.join(f'{round(x*255):02X}' for x in c[:3])

def strings(root,data):
    for name,val in data.items():
        sub(root,'string',name=name).text=val.replace("'","\\'")

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
cfg=sub(face,'UserConfigurations')
colors=sub(cfg,'ColorConfiguration',id='palette',displayName='color',defaultValue='62')
reference=Image.open(ROOT.parent/'表盘资料/双行数字/官方图1.png').convert('RGB')
def sample(x,y):
    return '#FF%02X%02X%02X'%reference.getpixel((x,y))
palette=[('gallery',sample(175,125),sample(175,300))]
shared=read(PROPS/'FaceColors.color.plist.json')['shared-collections']
for season,keys in shared['seasons']['collections'].items():
    for key in keys:
        if ' & ' not in key:continue
        pair=[k if '.' in k else f'seasons.{season}.{k}' for k in key.split(' & ')]
        a,b=map(asset_color,pair)
        if a and b and (a,b) not in [(x,y) for _,x,y in palette]:
            palette.append((' & '.join(pair),a,b))
for key in shared['standard']['items']:
    name='standard.'+key
    base=asset_color(name)
    if base:palette.append((name,base,base))
for i,(_,a,b) in enumerate(palette):
    sub(colors,'ColorOption',id=i,displayName=f'palette_{i}',colors=a+' '+b)
# 24S132 NTKPrideColorUtils.prideColorGradientColors2020 reads six RGBA entries.
# The axial factory sets (0.5,0) -> (0.5,1), with nil locations (equal spacing).
rainbow=['#FFE13454','#FFFF8542','#FFFFDE44','#FF84E98C','#FF1785B8','#FF8548B3']
sub(colors,'ColorOption',id='62',displayName='rainbow',colors=' '.join(rainbow[:3]+rainbow[-2:]))
modes={'symbols':['western','eastern','deva'],'style':['filled','mixed','outline']}
for key,choices in modes.items():
    conf=sub(cfg,'ListConfiguration',id=key,displayName=key,defaultValue=choices[0])
    for name in choices:sub(conf,'ListOption',id=name,displayName=name)

assets=dict(fonts())
bitmap=sub(face,'BitmapFonts')
bases={'western':48,'eastern':0x660,'deva':0x966}
preview=Image.new('RGB',(480,480))
width,height=155,166
# Render on a shared baseline. Respect the font's side bearings, notably the narrow 1.
for kind,suffix in [('filled','D'),('outline','DO')]:
    font=ImageFont.truetype(BytesIO(assets['__TokyoFont'+suffix]),800)
    for script,base in bases.items():
        family=script+'_'+kind
        bf=sub(bitmap,'BitmapFont',name=family)
        bounds=[font.getbbox(chr(base+n),anchor='ls') for n in range(10)]
        top=min(r[1] for r in bounds)-3
        bottom=max(r[3] for r in bounds)+3
        source_height=bottom-top
        source_width=max(540,round(source_height*width/height))
        left=(source_width-538)//2
        for n in range(10):
            canvas=Image.new('RGBA',(source_width,source_height))
            ImageDraw.Draw(canvas).text((left,-top),chr(base+n),font=font,fill='white',anchor='ls')
            glyph=canvas.resize((width,height),Image.Resampling.LANCZOS)
            name=f'{family}_{n}'
            glyph.save(DRAW/(name+'.png'))
            # Accept localized clock output while explicitly honoring the chosen symbols.
            for b in bases.values():sub(bf,'Character',name=chr(b+n),resource=name,width=width,height=height)
            if family=='western_filled':
                for row,digits in enumerate(((1,0),(0,9))):
                    for col,digit in enumerate(digits):
                        if n==digit:
                            x,y=85+col*width,(65,249)[row]
                            preview.paste('#'+palette[0][row+1][-6:],(x,y,x+width,y+height),glyph.getchannel('A'))
# Match the static gallery thumbnail to the new default.
for y in range(65,415):
    position=(y-65)*5/349
    i=min(4,int(position))
    f=position-i
    rgb=tuple(round(int(rainbow[i][k:k+2],16)*(1-f)+int(rainbow[i+1][k:k+2],16)*f) for k in (3,5,7))
    original=tuple(int(palette[0][1 if y<249 else 2][k:k+2],16) for k in (3,5,7))
    for x in range(85,395):
        alpha=preview.getpixel((x,y))[2]/original[2]
        preview.putpixel((x,y),tuple(round(c*alpha) for c in rgb))
preview.save(DRAW/'preview.png')

def clock_row(parent,row,font,color,rect,**attrs):
    clock=sub(parent,'DigitalClock',**rect,**attrs)
    t=sub(clock,'TimeText',**box(0,0,width*2,height),format=('h','mm')[row],align='END')
    sub(t,'BitmapFont',family=font,size=height,color=color)

def rainbow_row(parent,row,y,script,kind):
    rect=box(0,0,width*2,height)
    layer=sub(parent,'Group',name=f'rainbow_{script}_{kind}_{row}',**box(85,y,width*2,height))
    paint=sub(layer,'PartDraw',**rect)
    sub(paint,'Variant',mode='AMBIENT',target='alpha',value=212)
    fill=sub(sub(paint,'Rectangle',**rect),'Fill',color='#FFFFFFFF')
    sub(fill,'LinearGradient',startX=155,startY=65-y,endX=155,endY=415-y,
        positions='0 0.2 0.4 0.6 0.8 1',colors=' '.join(rainbow))
    mask=sub(layer,'Group',name='time_mask',renderMode='MASK',**rect)
    normal=sub(mask,'Group',name='normal_ink',**rect)
    # At the AOD endpoint the original glyph retains 0.3 alpha on supported devices.
    sub(normal,'Variant',mode='AMBIENT',target='alpha',value=76)
    clock_row(normal,row,script+'_'+kind,'#FFFFFFFF',rect)
    outline=sub(mask,'Group',name='ambient_outline',alpha=0,**rect)
    sub(outline,'Variant',mode='AMBIENT',target='alpha',value=255)
    clock_row(outline,row,script+'_outline','#FFFFFFFF',rect)

scene=sub(face,'Scene',backgroundColor='#000000')
scripts=sub(scene,'ListConfiguration',id='symbols')
for script in bases:
    wrapper=sub(sub(scripts,'ListOption',id=script),'Group',name=script,**box(0,0,480,480))
    styles=sub(wrapper,'ListConfiguration',id='style')
    for style in modes['style']:
        layer=sub(sub(styles,'ListOption',id=style),'Group',name=script+'_'+style,**box(0,0,480,480))
        switch=sub(layer,'Condition')
        exp=sub(sub(switch,'Expressions'),'Expression',name='rainbow')
        exp.text='[CONFIGURATION.palette.0] == #FFE13454 && [CONFIGURATION.palette.1] == #FFFF8542'
        multi=sub(sub(switch,'Compare',expression='rainbow'),'Group',name='pride',**box(0,0,480,480))
        solid=sub(sub(switch,'Default'),'Group',name='solid',**box(0,0,480,480))
        sub(solid,'Variant',mode='AMBIENT',target='alpha',value=52)
        for row,y in enumerate((65,249)):
            kind='outline' if style=='outline' or (style=='mixed' and row==1) else 'filled'
            rainbow_row(multi,row,y,script,kind)
            clock_row(solid,row,script+'_'+kind,f'[CONFIGURATION.palette.{row}]',box(85,y,width*2,height))
write(RES/'raw/watchface.xml',face)

editkeys={'color':'EDIT_MODE_LABEL_COLOR','style':'EDIT_MODE_LABEL_STYLE','symbols':'EDIT_MODE_LABEL_NUMERALS',
          'western':'EDIT_OPTION_LABEL_BIG_NUMERALS_TYPEFACE_WESTERN_ARABIC_COMPATIBILITY',
          'eastern':'EDIT_OPTION_LABEL_BIG_NUMERALS_TYPEFACE_EASTERN_ARABIC_COMPATIBILITY',
          'deva':'EDIT_OPTION_LABEL_BIG_NUMERALS_TYPEFACE_DEVANAGARI','filled':'EDIT_OPTION_LABEL_BIG_NUMERALS_STYLE_FILL',
          'mixed':'EDIT_OPTION_LABEL_BIG_NUMERALS_STYLE_HALF_FILL','outline':'EDIT_OPTION_LABEL_BIG_NUMERALS_STYLE_OUTLINE'}
for loc in FACE.glob('*.lproj'):
    face_labels=read(loc/'Localizable.strings.json')
    labels=read(PROPS/loc.name/'ClockFaces.strings.json')
    cnames={}
    for p in (PROPS/loc.name).glob('FaceColors*.strings.json'):cnames.update(read(p))
    data={'face_name':face_labels['FACE_STYLE_BIG_NUMERALS_DIGITAL_IN_TITLE_CASE']}
    data.update({k:labels[v] for k,v in editkeys.items() if v in labels})
    for i,(key,_,_) in enumerate(palette):
        data[f'palette_{i}']=cnames.get(key,' / '.join(cnames.get(k,k.split('.')[-1]) for k in key.split(' & '))) if i else '10:09'
    data['rainbow']=cnames.get('special.rainbow',cnames.get('rainbow','Rainbow'))
    tree=ET.Element('resources')
    strings(tree,data)
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        write(RES/f'values{q}/strings.xml',tree)
print('Palette choices:',len(palette)+1)
