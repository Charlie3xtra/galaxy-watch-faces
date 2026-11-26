"""Olympus corner artwork, launch targets and native Wear OS data slots."""
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET

corners=[('top_left',104,88,'phone'),('top_right',376,88,'workout'),
         ('bottom_left',104,392,'messages'),('bottom_right',376,392,'music')]
targets={'phone':'PHONE','workout':'com.samsung.android.wear.shealth',
         'messages':'MESSAGE','music':'MUSIC_PLAYER','alarm':'ALARM','heartrate':'HEALTH_HEART_RATE','battery':'BATTERY_STATUS','date':'CALENDAR'}
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
def corners_scene(scene):
    ink='[CONFIGURATION.palette.0]'
    for ident,(pos,x,y,default) in enumerate(corners,1):
        cfg=add(scene,'ListConfiguration',id='art_'+pos)
        for name,target in targets.items():
            opt=add(cfg,'ListOption',id=name)
            g=add(opt,'Group',name=pos+'_'+name,**box(x-33,y-33,66,66))
            add(g,'Launch',target=target)
            add(g,'Variant',mode='AMBIENT',target='alpha',value='76')
            if name=='music':
                # The gallery separates the angled label and the note, without a platter.
                text(g,'@string/music_caption',-6,3,67,24,16,ink,-35)
                pic(g,'corner_note',31,32,24,27,ink)
            elif name in ('battery','date'):
                ellipse(g,1,1,64,64,'#FF1B1B1B')
                if name=='date':
                    text(g,'[DAY_OF_WEEK_S]',5,7,56,20,13,ink)
                    text(g,'[DAY_Z]',5,25,56,34,24,ink)
                else:
                    part=add(g,'PartDraw',**box(0,0,66,66))
                    ring=add(part,'Arc',centerX=33,centerY=33,width=56,height=56,startAngle=0,endAngle=360)
                    add(ring,'Transform',target='endAngle',value='[BATTERY_PERCENT]*3.6')
                    add(ring,'Stroke',thickness=3,color=ink)
                    text(g,'[BATTERY_PERCENT]',4,19,58,29,19,ink)
            else:
                ellipse(g,1,1,64,64,'#FF1B1B1B')
                w,h={'phone':(32,32),'workout':(34,38),'messages':(40,33),'alarm':(32,34),'heartrate':(35,32)}[name]
                pic(g,'corner_'+name,(66-w)//2,(66-h)//2,w,h,ink)
        add(add(cfg,'ListOption',id='off'),'Group',name=pos+'_off',**box(0,0,1,1))
        types=['SHORT_TEXT','MONOCHROMATIC_IMAGE','SMALL_IMAGE','RANGED_VALUE','GOAL_PROGRESS']
        slot=add(scene,'ComplicationSlot',**box(x-34,y-34,68,68),slotId=ident,displayName=pos,supportedTypes='EMPTY '+' '.join(types))
        add(slot,'DefaultProviderPolicy',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
        add(slot,'BoundingOval',**box(0,0,68,68))
        add(slot,'Complication',type='EMPTY')
        for kind in types:
            view=add(add(slot,'Complication',type=kind),'Group',name=pos+'_'+kind,**box(0,0,68,68))
            # Opaque disk covers the shortcut beneath when the user supplies data.
            ellipse(view,0,0,68,68,'#FF191919')
            if kind in ('SMALL_IMAGE','MONOCHROMATIC_IMAGE'):
                pic(view,f'[COMPLICATION.{kind}]',14,14,40,40,ink if kind=='MONOCHROMATIC_IMAGE' else None)
            else:
                if kind!='SHORT_TEXT':
                    d=add(view,'PartDraw',**box(0,0,68,68))
                    r=add(d,'Arc',centerX=34,centerY=34,width=61,height=61,startAngle=0,endAngle=360)
                    expr=('clamp(([COMPLICATION.RANGED_VALUE_VALUE]-[COMPLICATION.RANGED_VALUE_MIN])/max(0.0001,[COMPLICATION.RANGED_VALUE_MAX]-[COMPLICATION.RANGED_VALUE_MIN]),0,1)' if kind=='RANGED_VALUE' else 'clamp([COMPLICATION.GOAL_PROGRESS_VALUE]/max(0.0001,[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]),0,1)')
                    add(r,'Transform',target='endAngle',value=expr+'*360')
                    add(r,'Stroke',thickness=3,color=ink)
                pic(view,'[COMPLICATION.MONOCHROMATIC_IMAGE]',24,8,20,20,ink)
                text(view,'[COMPLICATION.TEXT]',4,29,60,30,19,ink)
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

def localization(labels,strings):
    for pos,*_ in corners:
        label=labels['SLOT_LABEL_'+pos.upper()]
        strings[pos]=label
        strings['corner_'+pos]=label
    for key in [*targets,'off']:
        strings['quick_'+key]=labels['COMPLICATION_TYPE_EDIT_LABEL_'+key.upper()]
    strings['bezel']=labels['SLOT_LABEL_BOTTOM_CENTER']
    strings['music_caption']=labels.get('MUSIC_STOPPED_LARGE_UTILITY',strings['quick_music'])

def preview(im,draw,gallery):
    # Match the active default, including the invitation to open Music.
    for pos,x,y,key in corners:
        if key=='music':
            crop=gallery.crop((285,357,346,426)).convert('RGBA')
            crop.putalpha(crop.convert('L').point(lambda v:min(255,v*1.23)))
            im.alpha_composite(crop.resize((62,69)),(x-32,y-36))
        else:
            ImageDraw.Draw(im).ellipse((x-32,y-32,x+32,y+32),fill='#1b1b1b')
            mask=Image.open(draw/f'corner_{key}.png').getchannel('A')
            w,h={'phone':(32,32),'workout':(34,38),'messages':(40,33)}[key]
            im.paste('#cbd0d2',(x-w//2,y-h//2,x-w//2+w,y-h//2+h),mask.resize((w,h),Image.Resampling.LANCZOS))
