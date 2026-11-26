"""Transport the reference photo's radiance along the firmware numeral outlines."""
import ast
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HEIGHT, WIDTH = 190, 156
SAMPLES = 512
# Centers and pixels per model unit, measured on the 440 x 484 Apple reference.
LIGHTS = {"one": (1,134,155,209), "upper_zero": (0,250,155,210),
          "lower_zero": (0,142,330,210), "nine": (9,276,331,210)}


def outlines(path):
    source = path.read_text()
    def field(key):
        match = re.search(re.escape(key) + r"\.timeSamples = \{\s*\d+: (\[.*?\]),", source)
        return np.array(ast.literal_eval(match[1]))
    points = field("points")[:,:2] * [1,-1]
    indices = field("faceVertexIndices").reshape(-1,3)
    uv = field("primvars:st")[field("primvars:st:indices")].reshape(-1,3,2)
    # Each strip follows a separate closed boundary (including each counter of 8).
    graph = {}
    for tri, tex in zip(indices,uv):
        for i,j in ((0,1),(1,2),(2,0)):
            if abs(tex[i,0])>.01 or abs(tex[j,0])>.01:
                continue
            a,b = map(tuple,np.round(points[tri[[i,j]]],5))
            if a != b:
                graph.setdefault(a,set()).add(b)
                graph.setdefault(b,set()).add(a)
    rings=[]
    while graph:
        start=max(graph,key=lambda p:(p[1],p[0]))
        current=start
        ring=[]
        while current in graph:
            ring.append(current)
            neighbors=graph.pop(current)
            current=next((p for p in sorted(neighbors) if p in graph),start)
        if len(ring)<3:
            continue
        p=np.array(ring+[start])
        if np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])<0:
            p=p[::-1]
        dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        s=np.arange(SAMPLES)*dist[-1]/SAMPLES
        rings.append(np.column_stack([np.interp(s,dist,p[:,i]) for i in (0,1)]))
    return sorted(rings,key=lambda r:np.prod(np.ptp(r,axis=0)),reverse=True)


def normal(ring):
    tangent=np.roll(ring,-1,axis=0)-np.roll(ring,1,axis=0)
    tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-9)
    return tangent[:,[1,0]]*[-1,1]


def sample(image,xy):
    x,y=xy.T
    x=np.clip(x,0,image.shape[1]-1.001)
    y=np.clip(y,0,image.shape[0]-1.001)
    i,j=x.astype(int),y.astype(int)
    dx,dy=(x-i)[:,None],(y-j)[:,None]
    return ((1-dy)*((1-dx)*image[j,i]+dx*image[j,i+1])
            +dy*((1-dx)*image[j+1,i]+dx*image[j+1,i+1]))


def illuminate(paths, refpaths, image, center, scale, frame, frames):
    # Project each strand separately, keeping the sharp bends and holes of the target.
    factor=2
    canvas=Image.new("RGB",(WIDTH*factor,HEIGHT*factor))
    pen=ImageDraw.Draw(canvas)
    for k,path in enumerate(paths):
        rp=refpaths[min(k,len(refpaths)-1)]
        phase=round(SAMPLES*.085*np.sin(2*np.pi*frame/frames))
        rp=np.roll(rp,-phase,axis=0)
        target=path*196+[WIDTH/2,HEIGHT/2]
        for strand in (-3.4,-1.6,0,1.8,3.3):
            offset=strand+1.3*np.sin(np.arange(SAMPLES)*2*np.pi/SAMPLES+strand)
            pos=(target+normal(path)*offset[:,None])*factor
            light=sample(image,rp*scale+center+normal(rp)*offset[:,None])
            for i,c in enumerate(light):
                j=(i+1)%SAMPLES
                pen.line([tuple(pos[i]),tuple(pos[j])],fill=tuple(c.astype(int)),width=3 if strand==0 else 2)
    core=canvas.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    thin=np.asarray(core,dtype=float)
    local=np.asarray(core.filter(ImageFilter.GaussianBlur(2.3)),dtype=float)
    halo=np.asarray(core.filter(ImageFilter.GaussianBlur(7)),dtype=float)
    return Image.fromarray(np.clip(thin+local*.80+halo*1.45,0,255).astype("uint8"))

def bake(model,reference,draw,frames):
    image=np.asarray(Image.open(reference).convert("RGB"),dtype=float)
    rings=[outlines(model/f"{d}.usda") for d in range(10)]
    for digit,paths in enumerate(rings):
        for row in ("hour","minute"):
            key=("one" if digit==1 else "upper_zero") if row=="hour" else ("lower_zero" if digit==0 else "nine")
            ref,cx,cy,scale=LIGHTS[key]
            prefix="p" if row=="hour" else "m"
            for phase in (0,1,5):
                light=illuminate(paths,rings[ref],image,[cx,cy],scale,phase,frames)
                light.save(draw/f"{prefix}1f{phase}d{digit}.png")
