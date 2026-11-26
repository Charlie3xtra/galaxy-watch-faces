"""Olympus corner artwork, launch targets and native Wear OS data slots."""
from PIL import Image, ImageDraw
import rich_corners as rich
import os
import xml.etree.ElementTree as ET

corners=[('top_left',101,101,'phone'),('top_right',379,101,'workout'),
         ('bottom_left',101,379,'messages'),('bottom_right',379,379,'music')]
targets={'phone':'PHONE','workout':'com.samsung.android.wear.shealth',
         'messages':'MESSAGE','music':'MUSIC_PLAYER','alarm':'ALARM','heartrate':'HEALTH_HEART_RATE','battery':'BATTERY_STATUS','date':'CALENDAR','weather':'com.samsung.android.watch.weather','weather_rich':'com.samsung.android.watch.weather','weather_uv_index':'com.samsung.android.watch.weather'}
timing_apps={'timer':'timer','stopwatch':'stopwatch','world_clock':'worldclock'}
targets.update({key:'com.samsung.android.watch.'+app for key,app in timing_apps.items()})
targets.update(astronomy_luna=None, altitude='com.samsung.android.watch.compass')

def artwork(draw,catalog,gallery):
    for name,area,bg in [('phone',(74,65,107,97),26),('workout',(308,63,342,100),26),
                         ('messages',(70,380,115,419),26),('note',(321,396,347,427),0)]:
        mask=gallery.crop(area).convert('L').point(lambda p:max(0,min(255,(p-bg)*255/(205-bg))))
        mask=mask.crop(mask.getbbox())
        im=Image.new('RGBA',mask.size,'white');im.putalpha(mask);im.save(draw/f'corner_{name}.png')
    for key,pattern in [('alarm','circular-md_alarms-foreground@*'),('heartrate','circular-md_heartrate@*')]:
        im=Image.open(next(catalog.glob(pattern))).convert('RGBA')
        mask=im.getchannel('A');mask=mask.crop(mask.getbbox())
        im=Image.new('RGBA',mask.size,'white');im.putalpha(mask);im.save(draw/f'corner_{key}.png')

    rich.artwork(draw,catalog)
    atlas=catalog.parents[5]
    altitude=next(atlas.rglob('*rich_corner*altimeter_white*.png'))
    moon=next(atlas.rglob('VictoryNTKMoon_00-*.png')).parent
    for key,src in [('altitude',altitude),('timer',next(catalog.glob('circular-md_timercolor*.png'))),
                    ('world_clock',next(atlas.rglob('utility-textstring_worldclock*.png')))]+[
        (f'luna_{d}',next(moon.glob(f'VictoryNTKMoon_{(4*d)%112:02}-*.png'))) for d in range(28)]:
        full=str(src.resolve())
        alpha=Image.open(('\\\\?\\'+full) if os.name=='nt' else full).convert('RGBA').getchannel('A')
        asset=Image.new('RGBA',alpha.size,'white')
        asset.putalpha(alpha)
        if key in timing_apps:asset=asset.crop(alpha.getbbox())
        asset.save(draw/f'corner_{key}.png')
    # watchOS uses an SF Symbol for Stopwatch. Draw a scalable equivalent for Wear OS.
    art=Image.new('RGBA',(96,96)); pen=ImageDraw.Draw(art)
    pen.ellipse((12,20,83,91),outline='white',width=7)
    pen.line((48,5,48,21),fill='white',width=7)
    pen.line((35,5,61,5),fill='white',width=7)
    pen.line((74,26,82,17),fill='white',width=6)
    pen.line((48,57,61,39),fill='white',width=6)
    art.save(draw/'corner_stopwatch.png')

def add(p,tag,**attrs):
    return ET.SubElement(p,tag,{k:str(v) for k,v in attrs.items()})
def box(x,y,w,h):return dict(x=x,y=y,width=w,height=h)
def ellipse(g,x,y,w,h,color):
    p=add(g,'PartDraw',**box(x,y,w,h))
    add(add(p,'Ellipse',**box(0,0,w,h)),'Fill',color=color)
def pic(g,key,x,y,w,h,tint=None):
    p=add(g,'PartImage',**box(x,y,w,h),**({'tintColor':tint} if tint else {}))
    add(p,'Image',resource=key)
def text(g,expr,x,y,w,h,size,color,angle=0):
    p=add(g,'PartText',**box(x,y,w,h),angle=angle)
    f=add(add(p,'Text',align='CENTER',ellipsis='TRUE'),'Font',family='SYNC_TO_DEVICE',size=size,color=color)
    if expr.startswith('['):
        t=add(f,'Template');t.text='%s';add(t,'Parameter',expression=expr)
    else:f.text=expr
def configs(c):
    for pos,_,_,default in corners:
        opt=add(c,'ListConfiguration',id='art_'+pos,displayName='corner_'+pos,defaultValue=default)
        for key in [*targets,'off']:add(opt,'ListOption',id=key,displayName='quick_'+key)
    presets=add(c,'Flavors',defaultValue='original')
    original=add(presets,'Flavor',id='original',displayName='face_name')
    for pos,_,_,default in corners:
        add(original,'Configuration',id='art_'+pos,optionId=default)
    timing=add(presets,'Flavor',id='timing',displayName='timing_preset')
    for (pos,*_),art in zip(corners,('timer','stopwatch','world_clock','astronomy_luna')):
        add(timing,'Configuration',id='art_'+pos,optionId=art)
    for slot_id,(app,service) in enumerate((
            ('timer','complications.TimerComplicationProviderService'),
            ('stopwatch','complications.StopwatchComplicationProviderService'),
            ('worldclock','complication.WorldClockComplicationProviderService')),1):
        pkg='com.samsung.android.watch.'+app
        add(add(timing,'ComplicationSlot',slotId=slot_id),'DefaultProviderPolicy',
            primaryProvider=pkg+'/'+pkg+'.'+service,primaryProviderType='LONG_TEXT',
            defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
def corners_scene(scene):
    ink='[CONFIGURATION.palette.0]'
    for ident,(pos,x,y,default) in enumerate(corners,1):
        cfg=add(scene,'ListConfiguration',id='art_'+pos)
        for name,target in targets.items():
            opt=add(cfg,'ListOption',id=name)
            g=add(opt,'Group',name=pos+'_'+name,**box(x-33,y-33,66,66),scaleX=rich.SCALE,scaleY=rich.SCALE)
            if target:add(g,'Launch',target=target)
            add(g,'Variant',mode='AMBIENT',target='alpha',value='76')
            if name in ('music','heartrate','battery','weather','weather_rich','weather_uv_index'):
                rich.render(g,name,x,y,ink)
            elif name in ('astronomy_luna','altitude',*timing_apps):
                dx=(x-240)/((x-240)**2+(y-240)**2)**.5
                dy=(y-240)/((x-240)**2+(y-240)**2)**.5
                if name in timing_apps:
                    rich.picture(g,name,33+dx*13,33+dy*13,25,25,'#FFFF9F0A')
                    rich.arc_text(g,x,y,177,25,12,ink,'@string/quick_'+name)
                elif name=='altitude':
                    rich.picture(g,'altitude',33+dx*11,33+dy*11,29,34,ink)
                    rich.arc_text(g,x,y,177,23,16,ink,'—')
                else:
                    c=add(g,'Condition'); ex=add(c,'Expressions')
                    for day in range(28):
                        key=f'day{day}'
                        add(ex,'Expression',name=key).text=f'floor([MOON_PHASE_POSITION]) % 28 == {day}'
                        rich.picture(add(c,'Compare',expression=key),f'luna_{day}',33+dx*12,33+dy*12,36,36,ink)
                    # Some renderers report a fractional age. Use the coarse phase even when age is unavailable.
                    fallback=add(c,'Default'); phases=add(fallback,'Condition'); names=add(phases,'Expressions')
                    for phase in range(8):
                        key=f'phase{phase}';add(names,'Expression',name=key).text=f'[MOON_PHASE_TYPE] == {phase}'
                        rich.picture(add(phases,'Compare',expression=key),f'luna_{round(3.5*phase)}',33+dx*12,33+dy*12,36,36,ink)
                    rich.arc_text(g,x,y,176,25,8.5,ink,'%s',('[MOON_PHASE_TYPE_STRING]',))
            elif name=='date':
                ellipse(g,1,1,64,64,'#FF1B1B1B')
                text(g,'[DAY_OF_WEEK_S]',5,7,56,20,13,ink)
                text(g,'[DAY_Z]',5,25,56,34,24,ink)
            else:
                ellipse(g,1,1,64,64,'#FF1B1B1B')
                w,h={'phone':(32,32),'workout':(34,38),'messages':(40,33),'alarm':(32,34),'heartrate':(35,32)}[name]
                pic(g,'corner_'+name,(66-w)//2,(66-h)//2,w,h,ink)
        add(add(cfg,'ListOption',id='off'),'Group',name=pos+'_off',**box(0,0,1,1))
        types=['LONG_TEXT','SHORT_TEXT','RANGED_VALUE','GOAL_PROGRESS','MONOCHROMATIC_IMAGE','SMALL_IMAGE']
        slot=add(scene,'ComplicationSlot',**box(x-40,y-40,80,80),slotId=ident,displayName=pos,supportedTypes='EMPTY '+' '.join(types))
        add(slot,'DefaultProviderPolicy',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
        add(slot,'BoundingOval',**box(0,0,80,80))
        add(slot,'Complication',type='EMPTY')
        for kind in types:
            view=add(add(slot,'Complication',type=kind),'Group',name=pos+'_'+kind,**box(6,6,68,68),scaleX=rich.SCALE,scaleY=rich.SCALE)
            # Opaque disk covers the shortcut beneath when the user supplies data.
            ellipse(view,0,0,68,68,'#FF191919')
            if kind in ('SMALL_IMAGE','MONOCHROMATIC_IMAGE'):
                pic(view,f'[COMPLICATION.{kind}]',14,14,40,40,ink if kind=='MONOCHROMATIC_IMAGE' else None)
            elif kind in ('SHORT_TEXT','LONG_TEXT'):
                # Keep data, title and state glyph separate. Samsung Timer only supplies LONG_TEXT or ICON.
                rich.arc_text(view,x,y,191,24,13,ink,'%s',('[COMPLICATION.TEXT]',))
                rich.arc_text(view,x,y,170,21,11,ink,'%s',('[COMPLICATION.TITLE]',))
                dx,dy=x-240,y-240
                radius=(dx*dx+dy*dy)**.5
                style=add(view,'ListConfiguration',id='art_'+pos)
                for choice in [*targets,'off']:
                    branch=add(style,'ListOption',id=choice)
                    glyph='corner_'+choice if choice in timing_apps else '[COMPLICATION.MONOCHROMATIC_IMAGE]'
                    pic(branch,glyph,round(23+dx/radius*21),round(23+dy/radius*21),22,22,
                        '#FFFF9F0A' if choice in timing_apps else ink)
            else:
                if kind=='RANGED_VALUE':
                    frac='([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN])/max(0.0001,[COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])'
                else:
                    frac='[COMPLICATION.GOAL_PROGRESS_VALUE]/max(0.0001,[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE])'
                rich.gauge(view,x,y,180,frac,ink)
                rich.arc_text(view,x,y,209,22,15,ink,'%s',('[COMPLICATION.TEXT]',))
        add(slot,'Variant',mode='AMBIENT',target='alpha',value=76)

    # The fifth slot remains empty until a data source is explicitly selected.
    bezel=add(scene,'ComplicationSlot',**box(0,0,480,480),slotId=5,displayName='bezel',supportedTypes='EMPTY SHORT_TEXT LONG_TEXT')
    add(bezel,'DefaultProviderPolicy',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
    add(bezel,'BoundingArc',centerX=240,centerY=240,width=448,height=448,thickness=34,startAngle=150,endAngle=210,direction='CLOCKWISE')
    add(bezel,'Complication',type='EMPTY')
    for kind in ('SHORT_TEXT','LONG_TEXT'):
        part=add(add(bezel,'Complication',type=kind),'PartText',**box(0,0,480,480))
        circular=add(part,'TextCircular',centerX=240,centerY=240,width=450,height=450,startAngle=210,endAngle=150,direction='COUNTER_CLOCKWISE',align='CENTER',ellipsis='TRUE')
        templ=add(add(circular,'Font',family='SYNC_TO_DEVICE',size=17,color=ink),'Template')
        templ.text='%s'
        add(templ,'Parameter',expression='[COMPLICATION.TEXT]')
    add(bezel,'Variant',mode='AMBIENT',target='alpha',value=76)

def localization(labels,strings,altitude):
    for pos,*_ in corners:
        label=labels['SLOT_LABEL_'+pos.upper()]
        strings[pos]=label
        strings['corner_'+pos]=label
    for key in [*targets,'off']:
        strings['quick_'+key]=altitude if key=='altitude' else labels['COMPLICATION_TYPE_EDIT_LABEL_'+key.upper()]
    strings['bezel']=labels['SLOT_LABEL_BOTTOM_CENTER']
    strings['timing_preset']=' · '.join(labels['COMPLICATION_TYPE_EDIT_LABEL_'+key] for key in ('TIMER','WORLD_CLOCK'))
    strings['music_caption']=labels.get('MUSIC_STOPPED_LARGE_UTILITY',strings['quick_music'])

def preview(im,draw,gallery):
    for pos,x,y,key in corners:
        if key=='music':
            # Apple reference retains the actual curved glyphs in the static picker.
            crop=gallery.crop((285,357,346,426)).convert('RGBA')
            crop.putalpha(crop.convert('L').point(lambda v:min(255,v*1.23)))
            im.alpha_composite(crop.resize((70,78),Image.Resampling.LANCZOS),(x-35,y-39))
        else:
            radius=round(32*rich.SCALE)
            ImageDraw.Draw(im).ellipse((x-radius,y-radius,x+radius,y+radius),fill='#1b1b1b')
            mask=Image.open(draw/f'corner_{key}.png').getchannel('A')
            sw,sh={'phone':(32,32),'workout':(34,38),'messages':(40,33)}[key]
            w,h=round(sw*rich.SCALE),round(sh*rich.SCALE)
            im.paste('#cbd0d2',(x-w//2,y-h//2,x-w//2+w,y-h//2+h),mask.resize((w,h),Image.Resampling.LANCZOS))
