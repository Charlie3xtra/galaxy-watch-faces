"""Graphic-corner layouts for the Nike Hybrid face, in 66-unit local coordinates."""
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

SCALE=1.17
def add(p,tag,**a):return ET.SubElement(p,tag,{k:str(v) for k,v in a.items()})
def fmt(font,pattern,values):
    t=add(font,'Template');t.text=pattern
    for val in values:add(t,'Parameter',expression=val)
def when(p,key,expr):
    c=add(p,'Condition');add(add(c,'Expressions'),'Expression',name=key).text=expr
    return add(c,'Compare',expression=key),add(c,'Default')
def geometry(x,y,r,span):
    angle=math.degrees(math.atan2(x-240,240-y))%360
    lower=y>240
    # All positions share the screen centre, with upright reading on the lower half.
    return dict(centerX=round(33+(240-x)/SCALE,2),centerY=round(33+(240-y)/SCALE,2),
                width=round(2*r/SCALE,2),height=round(2*r/SCALE,2),
                startAngle=angle+(span if lower else -span)/2,endAngle=angle+(-span if lower else span)/2,
                direction='COUNTER_CLOCKWISE' if lower else 'CLOCKWISE')
def arc_text(g,x,y,r,span,size,ink,label,values=()):
    part=add(g,'PartText',x=0,y=0,width=66,height=66)
    tc=add(part,'TextCircular',**geometry(x,y,r,span),align='CENTER',ellipsis='TRUE')
    f=add(tc,'Font',family='SYNC_TO_DEVICE',size=size,color=ink)
    if values:fmt(f,label,values)
    else:f.text=label
def ordinary(g,cy,size,ink,pattern,values=()):
    p=add(g,'PartText',x=0,y=cy,width=66,height=27)
    f=add(add(p,'Text',align='CENTER'),'Font',family='SYNC_TO_DEVICE',size=size,color=ink)
    if values:fmt(f,pattern,values)
    else:f.text=pattern
def picture(g,name,cx,cy,w,h,ink):
    part=add(g,'PartImage',x=round(cx-w/2),y=round(cy-h/2),width=w,height=h,tintColor=ink)
    add(part,'Image',resource='corner_'+name)
def gauge(g,x,y,r,fraction,color):
    geo=geometry(x,y,r,17);geo.pop('direction')
    start,end=sorted([geo.pop('startAngle'),geo.pop('endAngle')])
    for fg in (False,True):
        part=add(g,'PartDraw',x=0,y=0,width=66,height=66)
        arc=add(part,'Arc',**geo,startAngle=start,endAngle=end)
        if fg:add(arc,'Transform',target='endAngle',value=f'{start} + {end-start} * clamp({fraction},0,1)')
        add(arc,'Stroke',thickness=4,color=color if fg else '#FF383838')
def artwork(draw,catalog):

    weather=catalog.parents[2]/'NanoWeatherComplications.framework/Assets.car/资源'
    for name,src in [('note',next(catalog.glob('rich-corner_music-*'))),('heartrate',next(catalog.glob('RichCornerHeartrate@*'))),('unavailable',next(weather.glob('DGCorner-Weather-emptystate*.png')))]:
        a=Image.open(src).convert('RGBA').getchannel('A');a=a.crop(a.getbbox())
        im=Image.new('RGBA',a.size,'white');im.putalpha(a);im.save(draw/f'corner_{name}.png')
    for key in ('sun','moon','cloud','partly','fog','rain','snow','storm','sleet','wind'):
        im=Image.new('RGBA',(120,120));p=ImageDraw.Draw(im);c='white'
        if key in ('sun','partly'):
            cx,cy=(58,58) if key=='sun' else (83,36)
            p.ellipse((cx-19,cy-19,cx+19,cy+19),fill=c)
            for i in range(8):
                a=i*math.pi/4
                p.line([(cx+math.cos(a)*v,cy+math.sin(a)*v) for v in (25,34)],fill=c,width=5)
        if key=='moon':
            p.ellipse((25,14,99,94),fill=c);p.ellipse((48,1,110,73),fill=(0,0,0,0))
        if key in ('wind','fog'):
            for j,(x1,x2) in enumerate(((12,90),(27,106),(16,82))):
                p.rounded_rectangle((x1,40+14*j,x2,45+14*j),3,fill=c)
        if key in ('cloud','partly','rain','snow','storm','sleet'):
            for b in ((16,42,57,79),(34,27,79,76),(61,41,102,79)):p.ellipse(b,fill=c)
            p.rectangle((36,54,82,79),fill=c)
            if key in ('rain','sleet'):
                for x in (38,60,83):p.line((x,85,x-5,98),fill=c,width=5)
            if key in ('snow','sleet'):
                for x in (34,55,78):p.ellipse((x,99,x+5,104),fill=c)
            if key=='storm':p.polygon([(58,79),(72,79),(62,91),(70,91),(48,109),(55,94),(49,94)],fill=c)
        im.resize((50,50),Image.Resampling.LANCZOS).save(draw/f'corner_{key}.png')
def render(g,name,x,y,ink):
    dx,dy=x-240,y-240
    norm=math.hypot(dx,dy)
    outward=(33+dx/norm*12,33+dy/norm*12)
    if name=='music':
        arc_text(g,x,y,177,23,15,ink,'@string/music_caption')
        picture(g,'note',*outward,25,27,ink)
    elif name=='heartrate':
        picture(g,'heartrate',*outward,31,31,'#FFFF527C')
        valid,empty=when(g,'pulse','[HEART_RATE] > 0')
        arc_text(valid,x,y,177,21,17,ink,'%s',('[HEART_RATE]',))
        arc_text(empty,x,y,177,21,17,ink,'—')
    elif name=='battery':
        # NTKBatteryTimelineEntryModel: gaugeProviderWithStyle + outerTextProvider (with %).
        arc_text(g,x,y,208,22,17,ink,'%s%%',('[BATTERY_PERCENT]',))
        normal,low=when(g,'normal','[BATTERY_PERCENT] > 20')
        for layer,color in ((normal,'#FF53D76A'),(low,'#FFFC5855')):
            gauge(layer,x,y,180,'[BATTERY_PERCENT]/100.0',color)
    elif name=='weather':
        live,empty=when(g,'weather','[WEATHER.IS_AVAILABLE] && ![WEATHER.IS_ERROR]')
        picture(empty,'unavailable',33,32,32,31,ink)
        arc_text(live,x,y,177,22,17,ink,'%s°',('[WEATHER.TEMPERATURE]',))
        c=add(live,'Condition');ex=add(c,'Expressions')
        for key,values in [('cloud',(2,)),('partly',(14,)),('fog',(3,13)),('rain',(4,6,12)),('snow',(5,7,11)),('storm',(9,)),('sleet',(10,)),('wind',(15,))]:
            add(ex,'Expression',name=key).text=' || '.join(f'[WEATHER.CONDITION] == {v}' for v in values)
            picture(add(c,'Compare',expression=key),key,*outward,34,34,ink)
        add(ex,'Expression',name='clear').text='[WEATHER.CONDITION] == 1 || [WEATHER.CONDITION] == 8'
        day,night=when(add(c,'Compare',expression='clear'),'day','[WEATHER.IS_DAY]')
        picture(day,'sun',*outward,33,33,ink);picture(night,'moon',*outward,33,33,ink)
        picture(add(c,'Default'),'unavailable',*outward,28,28,ink)
    elif name in ('weather_rich','weather_uv_index'):
        live,empty=when(g,'live','[WEATHER.IS_AVAILABLE] && ![WEATHER.IS_ERROR]')
        picture(empty,'unavailable',33,32,32,31,ink)
        if name=='weather_rich':
            arc_text(live,x,y,210,23,17,ink,'%s°',('[WEATHER.TEMPERATURE]',))
            frac='([WEATHER.TEMPERATURE] - [WEATHER.DAY_TEMPERATURE_LOW])/max(1,[WEATHER.DAY_TEMPERATURE_HIGH] - [WEATHER.DAY_TEMPERATURE_LOW])'
            gauge(live,x,y,183,frac,'#FFF6A34F')
        else:
            arc_text(live,x,y,210,22,16,ink,'UV %s',('[WEATHER.UV_INDEX]',))
            gauge(live,x,y,183,'[WEATHER.UV_INDEX]/11.0','#FFCD89DE')
