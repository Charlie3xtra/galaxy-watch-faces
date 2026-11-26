"""Build Nike Globe WFF resources from the 24S132 Vivaldi bundle. Needs Pillow and fontTools."""
from pathlib import Path
from io import BytesIO
import json
import os
import re
import struct
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parent
FW=ROOT.parent/'Watch8_5_24S132/解析'
if os.name=='nt':
    FW=Path('\\\\?\\'+str(FW))
bundle='NTKVivaldiFaceBundle'
relative=Path('System/Library/NanoTimeKit/FaceBundles')/(bundle+'.bundle')
catalog=FW/'图集'/relative/'Assets.car/资源'
props=FW/'属性表'/relative
draw=ROOT/'res/drawable-nodpi'
draw.mkdir(exist_ok=True,parents=True)

def sub(parent,tag,**attrs):
    return ET.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
def rect(x,y,w,h):
    return dict(x=x,y=y,width=w,height=h)
def save_xml(path,tree):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(tree)
    ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
def picture(parent,name,x,y,w,h,color=None):
    attrs={} if color is None else {'tintColor':color}
    p=sub(parent,'PartImage',**rect(x,y,w,h),**attrs)
    sub(p,'Image',resource=name)
def mask_asset(src,name,size):
    im=Image.open(src).convert('RGBA')
    mask=im.getchannel('A').resize(size,Image.Resampling.LANCZOS)
    image=Image.new('RGBA',size,'white')
    image.putalpha(mask)
    image.save(draw/(name+'.png'),optimize=True)
def branch(parent):
    c=sub(parent,'Condition')
    return c,sub(c,'Expressions')
def case(c,exp,name,test):
    sub(exp,'Expression',name=name).text=test
    return sub(c,'Compare',expression=name)
def group(parent,name):
    return sub(parent,'Group',name=name,**rect(0,0,480,480))
def mode(g,ambient):
    g.set('alpha','0' if ambient else '255')
    sub(g,'Variant',mode='AMBIENT',target='alpha',value=255 if ambient else 0)

for sec in range(60):
    sources=sorted(catalog.glob(f'*-{sec:02}.pdf*.png'))
    if sec==0:
        # Asset log distinguishes Globe (ambient) and Globe_00 (zero seconds).
        sources=[p for p in sources if 'd08404077ef47409' in p.name]
    mask_asset(sources[0],f'globe_{sec}',(348,348))
mask_asset(next(catalog.glob('*26c772b9900a3072.png')),'globe_ambient',(348,348))
mask_asset(next(catalog.glob('*swoosh*.png')),'swoosh',(74,27))

registry={}
for path in catalog.glob('vivaldi_*.json'):
    values=json.loads(path.read_text('utf8'))['Components']
    if len(values)==2:values=[values[0]]*3+[values[1]]
    registry[path.stem.split('-')[0]]='#'+''.join(f'{min(255,max(0,round(values[k]*255))):02X}' for k in (3,0,1,2))
gallery='#FFE26F73'
styles=[('gallery',[gallery,'#FFFFFFFF','#FF000000','#BAFFFFFF','#FFFFFFFF'],
         ['#FF000000','#55606060','#FF636363','#FFB1B3B3',gallery])]
for key in sorted(k.removesuffix('_primaryComplication') for k in registry if k.endswith('_primaryComplication')):
    def pigment(field,fallback):
        return registry.get(key+'_'+field,registry.get('vivaldi_'+field,fallback))
    primary=pigment('primaryComplication','#FFFFFFFF')
    active=[primary,pigment('secondaryComplication',primary),pigment('background','#FF000000'),
            pigment('globeGrid','#A6FFFFFF'),pigment('numerals','#FFFFFFFF')]
    ambient=[pigment('background.tritium','#FF000000'),pigment('globeGrid_tritium','#55606060'),
             pigment('numerals.tritium','#FFB1B3B3'),pigment('numeralsOutline.tritium','#FFFFFFFF'),
             pigment('primaryComplication.tritium',primary)]
    styles.append((key.replace('_','.'),active,ambient))

face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
color=sub(sub(face,'UserConfigurations'),'ColorConfiguration',id='palette',displayName='color',defaultValue='0')
for idx,(_,active,_) in enumerate(styles):
    sub(color,'ColorOption',id=idx,displayName=f'color_{idx}',colors=' '.join(active))
fonts=sub(face,'BitmapFonts')
blob=(FW/'代码'/bundle/bundle).read_bytes()
offset=32
sections={}
for _ in range(struct.unpack_from('<I',blob,16)[0]):
    cmd,n=struct.unpack_from('<II',blob,offset)
    if cmd==25:
        for i in range(struct.unpack_from('<I',blob,offset+64)[0]):
            name,seg,_,sz,pos=struct.unpack_from('<16s16sQQI',blob,offset+72+i*80)
            if b'__FONT_DATA' in seg:sections[name.rstrip(b'\0').decode()]=blob[pos:pos+sz]
    offset+=n
# The hours and minutes use different two-digit ligatures. Remap each to a
# temporary private glyph so that rasterization also works without HarfBuzz.
sprites={}
for outline,section in [(False,'__Vivaldi-Reg'),(True,'__Vivaldi-Otl')]:
    for row,feature in [('h','ss01'),('m','ss02')]:
        tt=TTFont(BytesIO(sections[section]))
        digits=tt.getBestCmap()
        by_name={digits[ord(str(n))]:str(n) for n in range(10)}
        feature_rec=next(r for r in tt['GSUB'].table.FeatureList.FeatureRecord if r.FeatureTag==feature)
        pairs={}
        for i in feature_rec.Feature.LookupListIndex:
            for st in tt['GSUB'].table.LookupList.Lookup[i].SubTable:
                for first,records in st.ligatures.items():
                    for lig in records:
                        if first in by_name and len(lig.Component)==1 and lig.Component[0] in by_name:
                            pair=by_name[first]+by_name[lig.Component[0]]
                            pairs[pair]=chr(0xe000+int(pair))
                            for cmap in tt['cmap'].tables:
                                if cmap.isUnicode():cmap.cmap[ord(pairs[pair])]=lig.LigGlyph
        buf=BytesIO()
        tt.save(buf)
        font=ImageFont.truetype(BytesIO(buf.getvalue()),400)
        if outline:font.set_variation_by_axes([65])
        family=row+('_outline' if outline else '_filled')
        bf=sub(fonts,'BitmapFont',name=family)
        samples=[str(i) for i in range(10)]+[f'{i:02}' for i in range(24 if row=='h' else 60)]
        for s in samples:
            im=Image.new('L',(1000,450))
            ImageDraw.Draw(im).text((65,24),pairs.get(s,s),font=font,fill=255)
            bbox=im.getbbox()
            crop=im.crop(bbox)
            size=(round(crop.width*100/284),round(crop.height*100/284))
            mask=crop.resize(size,Image.Resampling.LANCZOS)
            tile=Image.new('RGBA',(mask.width+4,110),'white')
            alpha=Image.new('L',tile.size)
            alpha.paste(mask,(2,(110-mask.height)//2))
            tile.putalpha(alpha)
            name=f'{family}_{s}'
            if outline:
                tile=tile.resize((round(tile.width*0.72),79),Image.Resampling.LANCZOS)
            tile.save(draw/(name+'.png'))
            sub(bf,'Character' if len(s)==1 else 'Word',name=s,resource=name,width=tile.width,height=tile.height)
            sprites[(family,s)]=tile

def clock(parent,row,family,color):
    c=sub(parent,'DigitalClock',**rect(105,132 if row=='h' else 242,270,110))
    t=sub(c,'TimeText',**rect(0,0,270,110),format='h' if row=='h' else 'mm',align='CENTER')
    sub(t,'BitmapFont',family=row+'_'+family,size=110,color=color)

scene=sub(face,'Scene',backgroundColor='#000000')
config=lambda i:f'[CONFIGURATION.palette.{i}]'
def background(parent,color):
    p=sub(parent,'PartDraw',**rect(0,0,480,480))
    sub(sub(p,'Rectangle',**rect(0,0,480,480)),'Fill',color=color)
composition=group(scene,'composition')
composition.attrib.update(scaleX='1.2',scaleY='1.2',pivotX='0.5',pivotY='0.5')
active=group(composition,'active')
mode(active,False)
background(active,config(2))
c,e=branch(active)
for sec in range(60):
    picture(case(c,e,f's{sec}',f'[SECOND] == {sec}'),f'globe_{sec}',66,66,348,348,config(3))
for row in ('h','m'):clock(active,row,'filled',config(4))
picture(active,'swoosh',203,359,74,27,config(0))

ambient=group(composition,'always_on')
mode(ambient,True)
def palette_cases(parent,index,draw_item):
    c,e=branch(parent)
    for idx,(_,pal,aod) in enumerate(styles):
        test=' && '.join(f'{config(i)} == {pal[i]}' for i in (0,1,2))
        draw_item(case(c,e,f'p{idx}',test),aod[index])

palette_cases(ambient,0,background)
palette_cases(ambient,1,lambda node,col:picture(node,'globe_ambient',66,66,348,348,col))
for family,index in [('filled',2),('outline',3)]:
    layer=sub(ambient,'Group',name='ambient_'+family,**rect(105,132,270,220))
    def paint(node,col):
        p=sub(node,'PartDraw',**rect(0,0,270,220))
        sub(sub(p,'Rectangle',**rect(0,0,270,220)),'Fill',color=col)
    palette_cases(layer,index,paint)
    mask=sub(layer,'Group',name='digits_'+family,renderMode='MASK',**rect(0,0,270,220))
    for row,y in [('h',0),('m',110)]:
        c=sub(mask,'DigitalClock',**rect(0,y,270,110))
        t=sub(c,'TimeText',**rect(0,0,270,110),format='h' if row=='h' else 'mm',align='CENTER')
        sub(t,'BitmapFont',family=row+'_'+family,size=110,color='#FFFFFFFF')
palette_cases(ambient,4,lambda node,col:picture(node,'swoosh',203,359,74,27,col))
save_xml(ROOT/'res/raw/watchface.xml',face)

def composite(preview,img,x,y,color):
    ink=Image.new('RGBA',img.size,color)
    ink.putalpha(img.getchannel('A'))
    preview.alpha_composite(ink,(x,y))
preview=Image.new('RGBA',(480,480),'black')
composite(preview,Image.open(draw/'globe_9.png'),66,66,'#B7B7B7')
for row,s,y in [('h','10',132),('m','09',242)]:
    im=sprites[(row+'_filled',s)]
    composite(preview,im,(480-im.width)//2,y,'white')
composite(preview,Image.open(draw/'swoosh.png'),203,359,'#E26F73')
preview.crop((40,40,440,440)).resize((480,480),Image.Resampling.LANCZOS).save(draw/'preview.png')
for loc in props.glob('*.lproj'):
    data={}
    for path in loc.glob('*.json'):data.update(json.loads(path.read_text('utf8')))
    core=FW/'属性表/System/Library/PrivateFrameworks/NanoTimeKit.framework'/loc.name/'ClockFaces.strings.json'
    labels=json.loads(core.read_text('utf8')) if core.exists() else {}
    values={'face_name':data['FACE_STYLE_VIVALDI_IN_TITLE_CASE'],'color':labels.get('EDIT_MODE_LABEL_COLOR','Color')}
    for idx,(key,_,_) in enumerate(styles):values[f'color_{idx}']=data.get(key,'10:09' if idx==0 else key.split('.')[-1])
    tree=ET.Element('resources')
    for k,v in values.items():sub(tree,'string',name=k).text=v.replace("'","\\'")
    code=loc.stem
    suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
    for q in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
        save_xml(ROOT/f'res/values{q}/strings.xml',tree)
print(len(styles),'color choices')
