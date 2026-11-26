"""Build the 24S132 Lilypad strand field and its native Wear OS scene."""
import argparse
import json
import struct
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
DRAW=ROOT/'res/drawable-nodpi'
BUNDLE='NTKLilypadFaceBundle.bundle'
PITCH=26
HEIGHT=224
ROW_Y=(32,224)
ORIGIN=240-8*PITCH
E=ET.SubElement

def write_xml(path,node):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(node)
    ET.ElementTree(node).write(path,encoding='utf-8',xml_declaration=True)

def strings(props):
    labels={'en':'Light|Dark','zh':'浅色|深色','ja':'ライト|ダーク','ko':'라이트|다크','fr':'Clair|Sombre','de':'Hell|Dunkel','es':'Claro|Oscuro','it':'Chiaro|Scuro','pt':'Claro|Escuro','ru':'Светлый|Тёмный','ar':'فاتح|داكن','nl':'Licht|Donker','sv':'Ljus|Mörk','da':'Lys|Mørk','no':'Lys|Mørk','fi':'Vaalea|Tumma','pl':'Jasne|Ciemne','tr':'Açık|Koyu','cs':'Světlé|Tmavé','el':'Ανοιχτό|Σκούρο','he':'בהיר|כהה','hi':'हल्का|गहरा','hu':'Világos|Sötét','id':'Terang|Gelap','ms':'Cerah|Gelap','ro':'Deschis|Închis','sk':'Svetlé|Tmavé','th':'สว่าง|มืด','uk':'Світлий|Темний','vi':'Sáng|Tối','ca':'Clar|Fosc','hr':'Svijetlo|Tamno','sl':'Svetlo|Temno'}
    for loc in props.glob('*.lproj'):
        code=loc.stem
        data=json.loads((loc/'LocalizableCompanion.strings.json').read_text(encoding='utf8'))
        pair=labels.get(code.split('_')[0],'Light|Dark').split('|')
        if code in ('zh_TW','zh_HK'):pair=['淺色','深色']
        tree=ET.Element('resources')
        for name,value in zip(('face_name','background','light','dark'),(data['LILYPAD_FACE_NAME_IN_TITLE_CASE'],data['EDIT_MODE_LABEL_LILYPAD_STYLE_COMPANION'],*pair)):
            E(tree,'string',name=name).text=value.replace("'","\\'")
        suffix={'en':'','es_419':'-b+es+419','he':'-iw','id':'-in'}.get(code,'-'+code.replace('_','-r'))
        for qualifier in [suffix]+{'zh_CN':['-zh','-b+zh+Hans'],'zh_TW':['-b+zh+Hant'],'no':['-nb']}.get(code,[]):
            write_xml(ROOT/f'res/values{qualifier}/strings.xml',tree)

def alpha_image(a):
    image=Image.new('RGBA',(a.shape[1],a.shape[0]),'white')
    image.putalpha(Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)))
    return image

def make_masks(atlas,curve,origins):
    masks={}
    x=np.arange(PITCH)+.5-PITCH/2
    for digit in range(10):
        glyph=atlas.crop((origins[digit],0,origins[digit+1]-1,156))
        width=round(glyph.width*1.59)
        samples=np.asarray(glyph.resize((width,HEIGHT),Image.Resampling.BICUBIC))/255
        for col in range(6):
            pos=round(width/2+(col-2.5)*PITCH-.5)
            if pos<0 or pos>=width:continue
            u=samples[:,pos]**.45
            v=np.interp(u*u*(3-2*u),np.linspace(0,1,len(curve)),curve)
            if v.max()<.001:continue
            for mode in ('active','ambient'):
                # Black AOD extinguishes the thin ground strands and narrows the digit.
                diameter=3.2+(PITCH-2-3.2)*v if mode=='active' else (PITCH-2)*v*.50
                a=np.clip(diameter[:,None]/2+.5-np.abs(x),0,1)
                if mode=='active':a[v==0]=0
                im=alpha_image(a)
                key=f'{mode}_{digit}_{col}'
                im.save(DRAW/f'{key}.png')
                masks[key]=im
    return masks

def number(node):
    cond=E(node,'Condition')
    return cond,E(cond,'Expressions')

def case(cond,tests,name,expr):
    E(tests,'Expression',name=name).text=expr
    return E(cond,'Compare',expression=name)

def box(tag,parent,x,y,w,h,**attrs):
    return E(parent,tag,x=str(x),y=str(y),width=str(w),height=str(h),**attrs)

def picture(parent,x,y,w,h,res,color):
    im=box('PartImage',parent,x,y,w,h,tintColor=color)
    E(im,'Image',resource=res)

def render_digits(node,mode,palette,masks):
    for row,src in enumerate(('([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])','[MINUTE]')):
        val=(f'floor({src} / 10)',f'({src} % 10)')
        for side in range(2):
            opts,tests=number(node)
            for short in (0,1):
                layout=case(opts,tests,f'width{short}',f'{val[1-side]} {"==" if short else "!="} 1')
                digits,limits=number(layout)
                for d in range((3 if row==0 else 6) if side==0 else 10):
                    first=5+(-1,1)[side]*(2 if short or d==1 else 3)
                    choice=case(digits,limits,f'd{d}',f'{val[side]} == {d}')
                    for col in range(6):
                        key=f'{mode}_{d}_{col}'
                        if key in masks:
                            k=first+col
                            picture(choice,ORIGIN+k*PITCH,ROW_Y[row],PITCH,HEIGHT,key,palette[k])

def pulse_frames():
    yy,xx=np.mgrid[:160,:PITCH]
    frames=[]
    for n in range(40):
        t=n/39
        env=np.sin(np.pi*t)**1.2
        wave=(.5+.5*np.cos(yy*.081-10*t))**2
        width=2+19*env*wave
        a=np.clip(width/2+.5-abs(xx+.5-PITCH/2),0,1)*env
        frames.append(alpha_image(a))
    frames[0].save(DRAW/'pulse.webp',save_all=True,append_images=frames[1:],lossless=True,duration=33,loop=0)
    frames[0].save(DRAW/'idle.png')

def interactive(node,palette):
    for i,color in enumerate(palette):
        x=ORIGIN+i*PITCH
        picture(node,x,0,PITCH,480,'strand',color)
    for trigger in ('ON_VISIBLE','TAP'):
        for i,color in enumerate(palette):
            part=box('PartAnimatedImage',node,ORIGIN+i*PITCH,0,PITCH,480,tintColor=color)
            E(part,'AnimatedImage',resource='pulse',format='WEBP',thumbnail='idle')
            E(part,'AnimationController',play=trigger,delayPlay=str(round(i*.022,3) if trigger=='ON_VISIBLE' else 0),beforePlaying='HIDE',afterPlaying='HIDE',repeat='FALSE')

def generate(fw):
    bundle=next((fw/'解析/图集').rglob(BUNDLE))/'Assets.car/资源'
    atlas=Image.open(next(bundle.glob('*DigitSprites*'))).convert('L')
    curve=np.asarray(Image.open(next(bundle.glob('*CurveFunction*'))).convert('L'))[0]/255
    binary=(fw/'解析/代码/NTKLilypadFaceBundle/NTKLilypadFaceBundle').read_bytes()
    offsets=struct.unpack_from('<11i',binary,0x7f60)
    assert offsets[-1]==atlas.width and atlas.height==156
    palettes=[]
    for base in (0x7c60,0x7d60):
        rgba=np.frombuffer(binary,'<f4',64,base).reshape(16,4)
        assert np.all(rgba[:,3]==255)
        palettes.append(['#%02X%02X%02X'%tuple(c[:3].astype(int)) for c in rgba])
    strings(next((fw/'解析/属性表').rglob(BUNDLE)))
    masks=make_masks(atlas,curve,offsets)
    alpha_image(np.clip(1.6+.5-np.abs(np.arange(PITCH)+.5-PITCH/2),0,1)[None,:]).save(DRAW/'strand.png')
    pulse_frames()
    face=ET.Element('WatchFace',width='480',height='480',clipShape='CIRCLE')
    settings=E(E(face,'UserConfigurations'),'ColorConfiguration',id='background',displayName='background',defaultValue='0')
    for key,color in [('light','#FFFFFFFF'),('dark','#FF000000')]:
        E(settings,'ColorOption',id='0' if key=='light' else '1',displayName=key,colors=color)
    scene=E(face,'Scene',backgroundColor='#000000')
    live=box('Group',scene,0,0,480,480,name='interactive')
    E(live,'Variant',mode='AMBIENT',target='alpha',value='0')
    choice,tests=number(live)
    for i in (1,0):
        pal=palettes[i]
        key=('light','dark')[i]
        branch=case(choice,tests,key,'[CONFIGURATION.background.0] == #FF000000') if i else E(choice,'Default')
        if i==0:
            rect=box('PartDraw',branch,0,0,480,480)
            E(box('Rectangle',rect,0,0,480,480),'Fill',color='#FFFFFF')
        interactive(branch,pal)
        render_digits(branch,'active',pal,masks)
    ambient=box('Group',scene,0,0,480,480,name='ambient',alpha='0')
    E(ambient,'Variant',mode='AMBIENT',target='alpha',value='135')
    render_digits(ambient,'ambient',palettes[1],masks)
    write_xml(ROOT/'res/raw/watchface.xml',face)
    for i,mode in ((0,'active'),(1,'active'),(1,'ambient')):
        canvas=Image.new('RGB',(480,480),'white' if i==0 else 'black')
        def paste(mask,x,y,color):
            canvas.paste(color,(x,y,x+mask.width,y+mask.height),mask)
        if mode=='active':
            line=Image.open(DRAW/'strand.png').getchannel('A').resize((PITCH,480))
            for k,c in enumerate(palettes[i]):paste(line,ORIGIN+k*PITCH,0,c)
        for row,pair in enumerate(((1,0),(0,9))):
            for side,d in enumerate(pair):
                first=5+(-1,1)[side]*(2 if pair[1-side]==1 or d==1 else 3)
                for col in range(6):
                    mask=masks.get(f'{mode}_{d}_{col}')
                    if mask:
                        k=first+col
                        alpha=mask.getchannel('A')
                        if mode=='ambient':alpha=alpha.point(lambda v:round(v*135/255))
                        paste(alpha,ORIGIN+k*PITCH,ROW_Y[row],palettes[i][k])
        circular=Image.new('L',(480,480));from PIL import ImageDraw
        ImageDraw.Draw(circular).ellipse((0,0,479,479),fill=255)
        canvas=Image.composite(canvas,Image.new('RGB',canvas.size),circular)
        canvas.save(ROOT/('light.png' if i==0 else mode+'.png'))
        if i==0:canvas.save(DRAW/'preview.png')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('firmware',type=Path)
    generate(parser.parse_args().firmware)
