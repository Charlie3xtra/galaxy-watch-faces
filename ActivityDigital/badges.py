"""Activity Digital built-in complications and firmware artwork."""
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from PIL import Image

from categories import EXTRA
MODES=('weather','workout','battery','heart','steps','date',*EXTRA)
SYMBOLS={'clear':'sun.max.fill','night':'moon.stars.fill','cloud':'cloud.fill',
         'partly':'cloud.sun.fill','partly_night':'cloud.moon.fill','fog':'cloud.fog.fill',
         'rain':'cloud.rain.fill','heavy':'cloud.heavyrain.fill','snow':'cloud.snow.fill',
         'sleet':'cloud.sleet.fill','storm':'cloud.bolt.rain.fill','wind':'wind','haze':'sun.haze.fill',
         'battery':'battery.100percent','heart':'heart.fill','steps':'figure.walk','date':'calendar'}
def make_assets(fw, art, ref):
    symbols=next((fw/'解析/图集').rglob('CoreGlyphs.bundle'))/'Assets.car/资源'
    for key,name in SYMBOLS.items():
        a=Image.open(next(symbols.glob(name+'.svg-*.png'))).convert('RGBA').getchannel('A')
        a=a.crop(a.getbbox())
        tint={'clear':'#FFD52D','night':'#BFC8FF','heart':'#FF305A','steps':'#63DE53','battery':'#9BF63A'}.get(key,'white')
        im=Image.new('RGBA',a.size,tint);im.putalpha(a)
        im.save(art/('ad_'+key+'.png'))
    for key,(_,_,symbol) in EXTRA.items():
        if key in ('notes','recognize'):
            pattern='custom.note.text.badge.clock.svg-*.png' if key=='notes' else 'custom.shazam.logo.fill.svg-*.png'
            src=next((fw/'提供程序解析/图集').rglob(pattern))
        else:src=next(symbols.glob(symbol+'.svg-*.png'))
        a=Image.open((chr(92)*2+'?'+chr(92)+str(src.resolve())) if os.name=='nt' else src).convert('RGBA').getchannel('A')
        a=a.crop(a.getbbox())
        im=Image.new('RGBA',a.size,'white');im.putalpha(a);im.thumbnail((96,96));im.save(art/('ad_'+key+'.png'))
    # Default partly-cloudy artwork has two separately colored layers in the reference.
    ref.crop((55,49,123,117)).resize((64,64),Image.Resampling.LANCZOS).save(art/'ad_partly_badge.png')
    src=next((fw/'解析/图集').rglob('WorkoutComplicationBundle.bundle'))/'Assets.car/资源'
    frames=[]
    for path in sorted(src.glob('174_*.png')):
        a=Image.open(path).convert('RGBA').getchannel('A').resize((78,78),Image.Resampling.LANCZOS)
        im=Image.new('RGBA',a.size,'#ADFA00');im.putalpha(a);frames.append(im)
    assert len(frames)==33
    frames[0].save(art/'ad_workout.png')
    frames[0].save(art/'ad_run.webp',save_all=True,append_images=frames[1:],duration=44,loop=0,lossless=True)

def add(p,tag,**attrs):return ET.SubElement(p,tag,{k:str(v) for k,v in attrs.items()})
def box(x,y,w,h):return dict(x=x,y=y,width=w,height=h)
def part(p,name,rect):add(add(p,'PartImage',**rect),'Image',resource=name)
def bg(p,w,h,color,disc=False):
    shape=add(add(p,'PartDraw',**box(0,0,w,h)),'Ellipse' if disc else 'Rectangle',**box(0,0,w,h))
    add(shape,'Fill',color=color)
def text(p,w,h,pattern,args,size=22,y=0):
    t=add(add(p,'PartText',**box(0,y,w,h)),'Text',align='CENTER',ellipsis='TRUE')
    f=add(t,'Font',family='SYNC_TO_DEVICE',size=size,color='#FFFFFFFF')
    if not args:
        f.text=pattern;return
    fmt=add(f,'Template');fmt.text=pattern
    for expr in args:add(fmt,'Parameter',expression=expr)
def branch(p,expr):
    c=add(p,'Condition');add(add(c,'Expressions'),'Expression',name='valid').text=expr
    return add(c,'Compare',expression='valid'),add(c,'Default')
def weather(p,w,h):
    live,missing=branch(p,'[WEATHER.IS_AVAILABLE]')
    if w!=h:
        text(live,w,h,'%s  %s°',['[WEATHER.CONDITION_NAME]','[WEATHER.TEMPERATURE]'])
        text(missing,w,h,'—',[]);return
    by_condition=add(live,'Condition');ex=add(by_condition,'Expressions')
    groups=[('clear',(1,8)),('cloud',(2,)),('partly',(14,)),('fog',(3,)),('rain',(6,12)),('heavy',(4,)),('snow',(5,7,11)),('storm',(9,)),('sleet',(10,)),('haze',(13,)),('wind',(15,))]
    def icon(g,k):
        if k=='partly':part(g,'ad_partly_badge',box(0,0,w,h))
        else:part(g,'ad_'+k,box(10,12,w-20,h-24))
    for key,values in groups:
        add(ex,'Expression',name=key).text=' || '.join('[WEATHER.CONDITION] == '+str(i) for i in values)
        g=add(by_condition,'Compare',expression=key)
        if key in ('clear','partly'):
            day,night=branch(g,'[WEATHER.IS_DAY]');icon(day,key);icon(night,'night' if key=='clear' else 'partly_night')
        else:icon(g,key)
    text(add(by_condition,'Default'),w,h,'—',[]);text(missing,w,h,'—',[])
def builtin(p,key,w,h):
    circle=w==h
    if circle:bg(p,w,h,'#FF191919',True)
    if key=='weather':weather(p,w,h);return
    if key=='workout':
        side=min(h,w);rect=box((w-side)//2,(h-side)//2,side,side)
        anim=add(p,'PartAnimatedImage',**rect)
        add(anim,'Variant',mode='AMBIENT',target='alpha',value='0')
        still=add(p,'PartImage',**rect,alpha=0)
        add(still,'Variant',mode='AMBIENT',target='alpha',value=255);add(still,'Image',resource='ad_workout')
        add(anim,'AnimatedImage',resource='ad_run',format='WEBP',thumbnail='ad_workout')
        add(anim,'AnimationController',play='ON_VISIBLE',repeat='FALSE',beforePlaying='THUMBNAIL',afterPlaying='THUMBNAIL')
        return
    if key in EXTRA:
        dim=min(42,h-4);part(p,'ad_'+key,box((w-dim)//2,(h-dim)//2,dim,dim));return
    expression={'battery':'[BATTERY_PERCENT]','heart':'[HEART_RATE]','steps':'[STEP_COUNT]','date':'[DAY]'}[key]
    part(p,'ad_'+key,box((w-24)//2 if circle else 65,5,24,22))
    text(p,w,h-26 if circle else h,'%s%%' if key=='battery' else '%s',[expression],17 if circle else 22,25 if circle else 0)

def configure(scene,cfg,fw,art,ref):
    make_assets(fw,art,ref)
    defaults=['weather','workout','weather']
    for n,name in enumerate(('top_left','top_right','bottom')):
        slot=next(el for el in scene.findall('ComplicationSlot') if el.get('displayName')==name)
        x,y,w,h=[int(slot.get(k)) for k in ('x','y','width','height')]
        panel=ET.Element('Group',dict(name='base_'+name,**{k:str(v) for k,v in box(x,y,w,h).items()}))
        scene.insert(list(scene).index(slot),panel)
        add(panel,'Variant',mode='AMBIENT',target='alpha',value=135)
        choice=add(cfg,'ListConfiguration',id=name+'_face',displayName=name,defaultValue='auto')
        dynamic=add(panel,'ListConfiguration',id=name+'_face')
        for selection in ('auto',*MODES,'empty'):
            key=defaults[n] if selection=='auto' else selection
            attrs={} if key=='empty' else {'icon':'ad_'+('partly_badge' if key=='weather' else key)}
            add(choice,'ListOption',id=selection,displayName='opt_'+selection,**attrs)
            if key=='empty':continue
            g=add(add(dynamic,'ListOption',id=selection),'Group',name=name+'_'+selection,**box(0,0,w,h))
            builtin(g,key,w,h)
            if key=='workout':
                tap=add(g,'PartDraw',**box(0,0,w,h))
                add(tap,'Launch',target='com.samsung.android.wear.shealth')
                add(add(tap,'Rectangle',**box(0,0,w,h)),'Fill',color='#00000000')
        # New IDs give existing installs the native artwork default; an explicit system selection
        # paints over that artwork and retains the original provider tap action.
        slot.set('slotId',str(30+n))
        policy=slot.find('DefaultProviderPolicy');policy.attrib.clear()
        policy.attrib.update(defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
        slot.set('supportedTypes','SHORT_TEXT LONG_TEXT MONOCHROMATIC_IMAGE SMALL_IMAGE RANGED_VALUE GOAL_PROGRESS EMPTY')
        for comp in slot.findall('Complication'):
            g=comp.find('Group')
            cover=ET.Element('Group',name=name+'_cover_'+comp.get('type'),**{k:str(v) for k,v in box(0,0,w,h).items()})
            comp.insert(0,cover);bg(cover,w,h,'#FF000000',w==h)
            for im in g.findall('PartImage'):im.attrib.pop('tintColor',None)
            if w!=h and comp.get('type') in ('SHORT_TEXT','LONG_TEXT'):
                t=g.find('.//Template');t.text='%s  %s';t.insert(0,ET.Element('Parameter',expression='[COMPLICATION.TITLE]'))
        for typ in ('SMALL_IMAGE','RANGED_VALUE','GOAL_PROGRESS'):
            g=add(add(slot,'Complication',type=typ),'Group',name=name+'_'+typ,**box(0,0,w,h))
            bg(g,w,h,'#FF191919' if w==h else '#FF000000',w==h)
            if typ=='SMALL_IMAGE':part(g,'[COMPLICATION.SMALL_IMAGE]',box((w-h)//2,0,h,h))
            else:
                part(g,'[COMPLICATION.MONOCHROMATIC_IMAGE]',box((w-24)//2,3,24,23))
                text(g,w,h-24,'%s',['[COMPLICATION.TEXT]'],17,24)




# A native provider owns the data and tap intent. A category selected in the editor
# can supply a firmware glyph, while Auto keeps an arbitrary provider's actual icon.
def skin_provider_images(scene):
    for slot in scene.findall('ComplicationSlot'):
        name=slot.get('displayName')
        if name not in ('top_left','top_right','bottom'):continue
        for comp in slot.findall('Complication'):
            for g in comp.findall('Group'):
                for im in list(g.findall('PartImage')):
                    original=im.find('Image').get('resource')
                    if original!='[COMPLICATION.MONOCHROMATIC_IMAGE]':continue
                    pos=list(g).index(im);g.remove(im)
                    config=ET.Element('ListConfiguration',id=name+'_face');g.insert(pos,config)
                    for key in ('auto',*MODES,'empty'):
                        opt=add(config,'ListOption',id=key)
                        pi=add(opt,'PartImage',**im.attrib)
                        glyph=original if key in ('auto','empty','weather') else 'ad_'+key
                        add(pi,'Image',resource=glyph)


