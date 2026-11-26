"""Foghorn bilateral elevation scale, adapted from the 24S132 range table."""
# Meter limit, foot limit, minor meter spacing, minor foot spacing.
SCALES=[(30,100,1,5),(150,500,5,10),(300,1000,10,20),
        (3000,10000,100,200),(6000,20000,100,500),(9000,30000,200,1000),
        (-30,-100,1,5),(-60,-200,1,5),(-90,-300,2,10),(-500,-1600,10,50)]

# Major and intermediate tick periods in minor divisions, feet then metres.
PERIODS=[(2,2,10,5),(10,5,10,5),(5,5,10,5),(5,5,10,5),(20,2,10,5),
         (10,5,5,5),(2,2,10,5),(20,2,10,5),(10,5,5,5),(2,2,10,5)]

def add_bezel(scene,el,box,colored,ink):
    full=box(0,0,480,480)
    source='com.samsung.android.watch.compass/com.samsung.android.watch.samsungcompass.complicationprovider.BarometerComplicationProviderService'
    slot=el(scene,'ComplicationSlot',slotId=8,displayName='elevation',supportedTypes='SHORT_TEXT EMPTY',**full)
    el(slot,'BoundingArc',centerX=240,centerY=240,width=478,height=478,thickness=44,startAngle=0,endAngle=359.99,direction='CLOCKWISE')
    el(slot,'DefaultProviderPolicy',primaryProvider=source,primaryProviderType='SHORT_TEXT',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')

    def mode(p):
        return el(el(el(el(p,'Group',name='provider_'+p.get('type').lower(),**full),'ListConfiguration',id='bezel_mode'),'ListOption',id='elevation'),'Group',name='elevation_'+p.get('type').lower(),**full)
    def curve(parent,angle,radius,span,size,value,params=(),lower=False):
        part=el(parent,'PartText',**full)
        t=el(part,'TextCircular',centerX=240,centerY=240,width=2*radius,height=2*radius,
             startAngle=angle+(span/2 if lower else -span/2),endAngle=angle+(-span/2 if lower else span/2),
             direction='COUNTER_CLOCKWISE' if lower else 'CLOCKWISE',align='CENTER')
        f=el(t,'Font',family='SYNC_TO_DEVICE',size=size,color='#FFFFFFFF')
        if params:
            tpl=el(f,'Template');tpl.text=value
            for expr in params:el(tpl,'Parameter',expression=expr)
        else:f.text=value

    def base(comp):
        g=mode(comp)
        colored(g,'[CONFIGURATION.tone.0]',ink('timeMinutes_night'),'[CONFIGURATION.tone.0]',ink('timeMinutes_night.tritium'))
        curve(g,321,222,22,14,'@string/feet')
        curve(g,39,222,22,14,'@string/meters')
        return g
    empty=base(el(slot,'Complication',type='EMPTY'))
    curve(empty,180,211,42,19,'—',lower=True)
    g=base(el(slot,'Complication',type='SHORT_TEXT'))
    # The Samsung provider sends the numeric value and unit in separate fields.
    txt='[COMPLICATION.TEXT]'
    title='[COMPLICATION.TITLE]'
    pressure=f'(abs({txt})*({title}=="inHg" ? 33.86389 : ({title}=="mmHg" ? 1.333224 : 1)))'
    alt=f'(44330*(1-pow({pressure}/1013.25,0.190295)))'
    cond=el(g,'Condition')
    el(el(cond,'Expressions'),'Expression',name='valid').text=f'({title}=="hPa" || {title}=="inHg" || {title}=="mmHg") && {pressure}>=250 && {pressure}<=1100'
    valid=el(cond,'Compare',expression='valid')
    select=el(valid,'Condition')
    exprs=el(select,'Expressions')
    for idx,(m,ft,dm,df) in enumerate(SCALES):
        k='band'+str(idx)
        test=f'{alt}>=0 && {alt}<={m}' if m>0 else f'{alt}<0 && {alt}>={m}'
        if m==9000:test=f'{alt}>=0'
        if m==-500:test=f'{alt}<0'
        el(exprs,'Expression',name=k).text=test
        band=el(select,'Compare',expression=k)
        for side,limit,spacing in [(-1,ft,df),(1,m,dm)]:
            count=round(abs(limit)/spacing)
            for n in range(count+1):
                # Both scales rise from their lower ends for positive heights.
                frac=n/count
                if m<0:frac=1-frac
                angle=side*(134-88*frac)
                value=f'abs({alt})'+('/0.3048' if side<0 else '')
                part=el(band,'PartDraw',**full,angle=round(angle,3))
                el(part,'Transform',target='alpha',value=f'{value}>={n*spacing} ? 242 : 65')
                major_step,mid_step=PERIODS[idx][:2] if side<0 else PERIODS[idx][2:]
                major=n%major_step==0
                el(el(part,'RoundRectangle',**box(238,7,4 if major else 3,13 if major else (10 if n%mid_step==0 else 6)),cornerRadiusX=1,cornerRadiusY=1),'Fill',color='#FFFFFFFF')
            curve(band,side*139%360,213,29,14,'%s',[f'numberFormat("#",{limit})'],True)
    curve(valid,180,211,45,18,'≈ %s %s',[f'numberFormat("#",round({alt}))','"m"'],True)
    curve(el(cond,'Default'),180,211,45,18,'—',lower=True)
