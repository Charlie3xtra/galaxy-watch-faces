"""Offline WFF animation of Plumeria's mesh-space segment shader."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from xml.etree.ElementTree import SubElement as child

COUNT=32
FRAME_MS=500
SIZE=(174,196)
ROWS=(140,340)
PINK_PAD=24

def tile_size(style):
    return (228,265) if style==2 else SIZE

def key_name(style, asset, frame):
    prefix="key" if style==1 else f"key{style}"
    return f"{prefix}_{asset}_{frame:02}"

def scene(parent, style):
    for odd in (False, True):
        layer=child(parent,"Group",name=f"buffer{int(odd)}",x="0",y="0",width="480",height="480")
        if odd:
            opacity=child(layer,"Transform",target="alpha",value="[MILLISECOND] < 500 ? 255 : 0")
            child(opacity,"Animation",duration="0.5",fps="30",interpolation="LINEAR")
        phase=child(layer,"Condition")
        tests=child(phase,"Expressions")
        for sec in range(16):
            phase_expr="([SECONDS_IN_DAY] % 16)" if odd else "(([SECONDS_IN_DAY] + ([MILLISECOND] >= 500 ? 1 : 0)) % 16)"
            child(tests,"Expression",name=f"s{sec}").text=f"{phase_expr} == {sec}"
            face=child(phase,"Compare",expression=f"s{sec}")
            digit_scene(face,2*sec+int(odd),style)

def digit_scene(parent,frame,style):
    size=tile_size(style)
    hour="([IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12])"
    for row,(prefix,number) in enumerate((("h",hour),("m","[MINUTE]"))):
        digits=(f"floor({number} / 10)",f"({number} % 10)")
        for col,source in enumerate(digits):
            name=f"{prefix}{col}"
            x=240-size[0]//2
            node=child(parent,"Group",name=name,x=str(x),y=str(ROWS[row]-size[1]//2),width=str(size[0]),height=str(size[1]))
            # The narrower 1 needs less horizontal advance than a round digit.
            sign=(-1,1)[col]
            child(node,"Transform",target="x",value=f"{x} + {sign} * (({digits[1-col]} == 1) ? 48 : 72)")
            cond=child(node,"Condition")
            expressions=child(cond,"Expressions")
            limit=3 if (col==0 and row==0) else 6 if col==0 else 10
            for d in range(limit):
                child(expressions,"Expression",name=f"d{d}").text=f"{source} == {d}"
                choice=child(cond,"Compare",expression=f"d{d}")
                part=child(choice,"PartImage",x="0",y="0",width=str(size[0]),height=str(size[1]))
                if style==2:
                    part.set("blendMode","SCREEN")
                asset=f"{prefix if d==0 else 'n'}{d}"
                child(part,"Image",resource=key_name(style,asset,frame))


def bake_digit(uv,source,reference_center,colors,settings,seed,padded=False):
    h,w=uv.shape[:2]
    y,x=np.nonzero(uv[:,:,0]>=0)
    u,v=uv[y,x].T
    rng=np.random.default_rng(seed)
    # block006.ll, lines 9-42: transverse coverage with three derivative samples.
    width=np.maximum(np.abs(np.gradient(uv[:,:,0],axis=0))+np.abs(np.gradient(uv[:,:,0],axis=1)),.01)
    du=np.minimum(width[y,x],.45)/3
    coverage=sum(np.clip(2-4*np.abs(.5-(u+offset-.15)/.70),0,1) for offset in (-du,0,du))/3
    if source is not None:
        X=np.clip((reference_center[0]+x-w/2).astype(int),0,source.shape[1]-1)
        Y=np.clip((reference_center[1]+y-h/2).astype(int),0,source.shape[0]-1)
        light=source[Y,X].astype(float)/255
    layers=[]
    for k,color in enumerate(colors):
        if source is None:
            anchor=rng.random()
        else:
            weight=np.maximum(0,light@(color/(np.linalg.norm(color)+1e-5))-.65*light.max(1))**3
            anchor=np.angle(np.sum(weight*np.exp(2j*np.pi*v)))/(2*np.pi)
        depth=k/(len(colors)-1)
        spread=(settings["jitterScaleNear"]*(1-depth)+settings["jitterScaleFar"]*depth)*8
        dx,dy=np.rint((rng.random(2)-.5)*2*spread*[settings["jitterAspectRatio"],1]).astype(int)
        layers.append((np.clip(y+dy,0,h-1),np.clip(x+dx,0,w-1),color,.5-anchor+rng.uniform(-.06,.06),(.30+.25*rng.random()),(-1 if rng.random()>.66 else 1),rng.uniform(.045,.072)))
    frames=[]
    for n in range(COUNT):
        out=np.zeros((h,w,3),np.float32)
        for yy,xx,color,offset,length,direction,speed in layers:
            # block006.ll, lines 52-105: periodic position, eased ramp and framebuffer blend.
            cycle=n/COUNT
            # Close the portable loop while retaining the measured local velocity at its midpoint.
            travel=cycle+(speed*COUNT*FRAME_MS/1000-1)*np.sin(2*np.pi*cycle)/(2*np.pi)
            pos=(v+offset+travel*direction)%1
            ramp=settings["segmentRampLength"]
            t=np.clip((np.abs(pos-.5)-length*.5+ramp)/ramp,0,1)
            a=(coverage*(1-t*t*(3-2*t)))[:,None]
            out[yy,xx]=color*a*a+(1-a+settings["additiveBlend"])*out[yy,xx]
        core=Image.fromarray(np.uint8(np.clip(out,0,1)*255))
        near=np.asarray(core.filter(ImageFilter.GaussianBlur(2.4)),float)/255
        far=np.asarray(core.filter(ImageFilter.GaussianBlur(8)),float)/255
        # block001.ll: independently shape the light field and type, combine, then tone-map.
        light=((out*settings["bloomTextLayerInputMult"])**settings["bloomTextContrast"]+
               ((near*.52+far*1.25)*settings["bloomLayerInputMult"])**settings["bloomContrast"])
        z=light**settings["bloomCombinedContrast"]*settings["bloomFinalMult"]
        rgb=z*(1+z/settings["bloomWhitePoint"])/(1+z)
        peak=rgb.max(axis=2,keepdims=True)
        display=rgb/(1+peak)
        frames.append(np.power(np.clip(display,0,1), 1/1.85))
    target=np.median([f.mean() for f in frames])
    result=[]
    frames=[np.clip(f*(target/max(f.mean(),1e-8)),0,1) for f in frames]
    peak=np.maximum.reduce([f.max(2) for f in frames])
    if padded:
        # Bloom decays on a padded mesh. Dim transparent halos allow neighbouring glyphs to overlap.
        feather=1
        alpha=np.clip(peak,0,1)
    else:
        yy,xx=np.mgrid[:h,:w]
        edge=np.minimum.reduce((yy-7,h-8-yy,xx,w-1-xx))
        t=np.clip(edge/8,0,1)
        feather=t*t*(3-2*t)
        alpha=np.clip(peak*16,0,1)
    for f in frames:
        res=np.dstack([f/np.maximum(alpha[:,:,None],1e-7),alpha*feather])
        result.append(Image.fromarray(np.uint8(np.clip(res,0,1)*255)))
    return result

def generate(model,art,draw,mesh_uv,settings,palette,style):
    source=np.asarray(Image.open(art).convert("RGB")) if style==1 else None
    frames={}
    size=tile_size(style)
    for d in range(10):
        uv=mesh_uv(model/f"{d}.usda")
        if style==2:
            uv=np.pad(uv,((PINK_PAD,PINK_PAD),(PINK_PAD,PINK_PAD),(0,0)),constant_values=-1)
        for row in (("h","m") if d==0 else ("n",)):
            center=((134,155) if d==1 else (250,155)) if (row=="h" or (row=="n" and d!=9)) else ((142,330) if d==0 else (276,331))
            imgs=bake_digit(uv,source,center,palette,settings,5371+d+(30 if row=="m" else 0),padded=style==2)
            if style!=2:
                imgs=[im.crop((0,7,im.width,im.height-7)) for im in imgs]
            for idx,im in enumerate(imgs):
                im.save(draw/(key_name(style,f"{row}{d}",idx)+".png"))
            if d in (1,0,9):
                frames[row,d]=imgs
    previews=[]
    for n in range(COUNT):
        canvas=Image.new("RGBA",(480,480),"black")
        for row,(prefix,pair) in enumerate((("h",(1,0)),("m",(0,9)))):
            for col,d in enumerate(pair):
                dx=(48 if pair[1-col]==1 else 72)*(-1,1)[col]
                im=frames[prefix if d==0 else "n",d][n].resize(size,Image.Resampling.LANCZOS)
                canvas.alpha_composite(im,(240+dx-size[0]//2,ROWS[row]-size[1]//2))
        previews.append(canvas.convert("RGB"))
    if style==1:
        previews[0].save(draw/"preview.png")
    import os, shutil, subprocess
    ffmpeg=os.environ.get("FFMPEG") or shutil.which("ffmpeg") or next(draw.parents[2].glob("work/decoders/imageio_ffmpeg/binaries/ffmpeg*.exe"))
    with subprocess.Popen([str(ffmpeg),"-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","480x480","-r","30","-i","-","-c:v","libx264","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",str(draw.parents[1]/f"flow-preview-1.6-{style}.mp4")],stdin=subprocess.PIPE) as proc:
        for idx,current in enumerate(previews):
            following=previews[(idx+1)%COUNT]
            for step in range(15):
                proc.stdin.write(Image.blend(current,following,step/15).tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("Preview encoding failed")
