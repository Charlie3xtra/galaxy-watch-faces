"""Bake the firmware digit meshes into native WFF bitmap fonts (NumPy and Pillow)."""
from PIL import ImageDraw
import argparse
import ast
import colorsys
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
DRAW = ROOT / "res/drawable-nodpi"
BUNDLE = Path("System/Library/NanoTimeKit/FaceBundles/NTKPlumeriaFaceBundle.bundle")
AX = Path("System/Library/PrivateFrameworks/AXNTKUtilities.framework")
W, H, FRAMES = 156, 190, 6
ROWS = ((136,"hh"),(344,"mm"))
ROMAN = ["I", "II", "III", "IV", "V"]
CHILD = ET.SubElement


def store(path, xml):
    ET.indent(xml)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(xml).write(path, encoding="utf-8", xml_declaration=True)


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def mesh_uv(path, enlargement=0):
    """Rasterize the Apple triangles and their face-varying texture coordinates."""
    source = path.read_text()
    def field(key):
        match = re.search(re.escape(key) + r"\.timeSamples = \{\s*\d+: (\[.*?\]),", source)
        return np.array(ast.literal_eval(match[1]))
    positions = field("points")[:, :2]
    if enlargement:
        positions = positions + enlargement * field("normals")[:, :2]
    pos = positions * [210, -210] + [W / 2, H / 2]
    triangles = field("faceVertexIndices").reshape(-1, 3)
    uv = field("primvars:st")[field("primvars:st:indices")].reshape(-1, 3, 2)
    atlas = np.full((H,W,2), -1, np.float32)
    for xyz, tex in zip(pos[triangles], uv):
        x0,y0 = np.maximum(np.floor(xyz.min(axis=0)).astype(int),0)
        x1,y1 = np.minimum(np.ceil(xyz.max(axis=0)).astype(int)+1,[W,H])
        a,b,c = xyz
        basis = np.stack([b-a,c-a],axis=1)
        if abs(np.linalg.det(basis)) < 1e-10:
            continue
        yy,xx = np.mgrid[y0:y1,x0:x1]
        ab = (np.stack([xx+.5,yy+.5],axis=-1)-a) @ np.linalg.inv(basis).T
        inside = (ab.min(axis=-1)>=0) & (ab.sum(axis=-1)<=1)
        atlas[y0:y1,x0:x1][inside] = tex[0] + ab[inside] @ (tex[1:]-tex[0])
    return atlas


def colors(table):
    return np.array([list(map(int,re.findall(r"\d+",table[f"color{i}"]))) for i in range(1,21)])


def ambient_digit(uv, settings, style, digit):
    cfg = settings["base"] | settings[f"colorway{style}"] | settings["tritiumBase"] | settings[f"tritium{style}"]
    u,v = uv.transpose(2,0,1)
    du = np.minimum(np.abs(np.gradient(u,axis=0))+np.abs(np.gradient(u,axis=1)),.45)/3
    coverage = sum(np.clip(2-4*np.abs(.5-(u+d-.15)/.7),0,1) for d in (-du,0,du))/3
    rng = np.random.default_rng(settings["global"]["randomSeed"] + digit)
    out = np.zeros((H,W,3))
    for index,color in enumerate(colors(cfg)/255,1):
        phase=rng.random()
        length=(.30+.25*rng.random())*cfg["segmentGlobalLengthMultiplier"]
        if index==cfg["tritiumSolidLayerIdx"]:
            length*=cfg["tritiumSolidLayerLengthMultiplier"]
        ramp=cfg["segmentRampLength"]
        t=np.clip((np.abs((v+phase)%1-.5)-length/2+ramp)/ramp,0,1)
        alpha=(coverage*(1-t*t*(3-2*t)))[:,:,None]
        out=color*alpha**2+(1-alpha)*out
    light=(out*cfg["bloomTextLayerInputMult"])**cfg["bloomTextContrast"]
    z=light**cfg["bloomCombinedContrast"]*cfg["bloomFinalMult"]
    mapped=z*(1+z/cfg["bloomWhitePoint"])/(1+z)
    display=mapped/(1+mapped.max(axis=2,keepdims=True))
    return Image.fromarray(np.uint8(np.clip(display,0,1)**(1/1.85)*255))


def render(uv, settings, style, phase, digit, ambient):
    base = settings["base"]
    active = settings[f"colorway{style}"]
    table = dict(active)
    if ambient:
        table.update(settings[f"tritium{style}"])
    palette = colors(table) / 255
    rng = np.random.default_rng(settings["global"]["randomSeed"] + digit)
    output = np.zeros((H,W,3), np.float32)
    u,v = uv.transpose(2,0,1)
    for k in range(base["numLayers"]):
        angle, offset, shift = rng.random(3)
        t = phase / FRAMES
        band = np.maximum(0, 1 - abs(u - (.12+.76*offset)) / (.24 if ambient else .36))
        hue, saturation, value = colorsys.rgb_to_hsv(*palette[k])
        center = (hue + .18*angle + .11*digit + t + .03*np.sin(2*np.pi*(shift+t))) % 1
        distance = abs((v-center+.5)%1-.5)
        envelope = np.maximum(0,1-distance/base["segmentRampLength"])**1.7
        stroke = band * (.012 + 1.9*envelope)
        if ambient:
            stroke *= .43 if k < 9 else 0
        else:
            dx = round(2.7*np.cos(2*np.pi*(shift+t)) * base["jitterAspectRatio"])
            dy = round(2.7*np.sin(2*np.pi*(shift+t)))
            stroke = np.roll(stroke,(dy,dx),(0,1))
        output += stroke[:,:,None]*palette[k]
    if ambient:
        output += ((u>=0)*np.maximum(0,1-abs(u-.5)/.33))[:,:,None]*palette[0]*.55
    direct = np.clip(output*1.35,0,1)
    im = Image.fromarray((direct*255).astype("uint8"))
    if not ambient:
        bloom = np.array(im.filter(ImageFilter.GaussianBlur(4)),float)/255
        halo = np.array(im.filter(ImageFilter.GaussianBlur(10)),float)/255
        direct = 1-np.exp(-(output*1.8 + bloom*active["bloomFinalMult"] + halo*2.2))
        peak = direct.max(axis=2,keepdims=True)
        direct = peak * np.power(direct / np.maximum(peak,1e-8), 2.2)
        yy,xx=np.mgrid[:H,:W]
        margin=np.minimum(np.minimum(xx,W-1-xx),np.minimum(yy,H-1-yy))
        direct *= np.clip(margin/11,0,1)[:,:,None]
    return Image.fromarray((np.clip(direct,0,1)*255).astype("uint8"))


def localized(properties):
    for loc in (properties/BUNDLE).glob("*.lproj"):
        locale = loc.stem
        data = read(loc/"Localizable.strings.json")
        labels = read(loc/"FaceColors.strings.json")
        axfile = properties/AX/loc.name/"Accessibility.strings.json"
        ax = read(axfile) if axfile.exists() else {}
        xml = ET.Element("resources")
        CHILD(xml,"string",name="face_name").text = data["FACE_PLUMERIA_IN_TITLE_CASE"]
        for i in range(5):
            CHILD(xml,"string",name=f"palette_{i}").text = labels[f"colorway{i}"]
            CHILD(xml,"string",name=f"desc_{i}").text = ax.get(f"color.plumeria.colorway{i}.label",ROMAN[i]).replace("'","\\'")
        category = {"zh":"配色","ja":"カラー","ko":"색상","fr":"Couleur","de":"Farbe","es":"Color","pt":"Cor","it":"Colore","ru":"Цвет","ar":"اللون","nl":"Kleur","sv":"Färg","no":"Farge","da":"Farve","fi":"Väri","ca":"Color","cs":"Barva","el":"Χρώμα","he":"צבע","hi":"रंग","hr":"Boja","hu":"Szín","id":"Warna","ms":"Warna","pl":"Kolor","ro":"Culoare","sk":"Farba","sl":"Barva","th":"สี","tr":"Renk","uk":"Колір","vi":"Màu"}.get(locale.split("_")[0],"Color")
        CHILD(xml,"string",name="color_label").text=category
        suffix={"en":"","es_419":"-b+es+419","he":"-iw","id":"-in"}.get(locale,"-"+locale.replace("_","-r"))
        suffixes=[suffix]+{"zh_CN":["-zh","-b+zh+Hans"],"zh_TW":["-b+zh+Hant"],"no":["-nb"],"pt_PT":["-pt"]}.get(locale,[])
        for q in suffixes:
            store(ROOT/f"res/values{q}/strings.xml",xml)


def trim_fonts(mesh_dir):
    """Use proportional advances while fading only the outside of the glow."""
    for digit in range(10):
        atlas=mesh_uv(mesh_dir/f"{digit}.usda")
        xs=np.where(atlas[:,:,0]>=0)[1]
        box=(max(0,int(xs.min())-9),0,min(W,int(xs.max())+11),H)
        for path in DRAW.glob(f"p*f*d{digit}.png"):
            style,phase=map(int,re.match(r"p(\d+)f(\d+)",path.stem).groups())
            if style==1 and phase!=FRAMES:
                continue
            pix=np.asarray(Image.open(path).convert("RGB").crop(box),dtype=float)/255
            yy,xx=np.mgrid[:H,:pix.shape[1]]
            edge=np.minimum.reduce((xx,pix.shape[1]-1-xx,yy,H-1-yy))
            alpha=np.clip(pix.max(2)*12,0,1)
            rgb=pix/np.maximum(alpha[:,:,None],1e-7)
            alpha*=np.clip(edge/4,0,1)
            Image.fromarray(np.uint8(255*np.clip(np.dstack([rgb,alpha]),0,1))).save(path)

def scene(settings):
    root=ET.Element("WatchFace",width="480",height="480",clipShape="CIRCLE")
    fonts=CHILD(root,"BitmapFonts")
    config=CHILD(CHILD(root,"UserConfigurations"),"ListConfiguration",id="palette",displayName="color_label",defaultValue="0")
    group=CHILD(CHILD(root,"Scene",backgroundColor="#000000"),"ListConfiguration",id="palette")
    for style in range(1,6):
        swatch=[tuple(c) for c in colors(settings[f"colorway{style}"])]
        visible=list(dict.fromkeys(swatch))
        if style==1:
            visible=[swatch[i-1] for i in [3,7,9,2,4]]
        badge=Image.new("RGBA",(144,144))
        pen=ImageDraw.Draw(badge)
        for i,c in enumerate(visible):
            pen.pieslice((3,3,140,140),-90+360*i/len(visible),-90+360*(i+1)/len(visible),fill=c+(255,))
        badge.resize((72,72),Image.Resampling.LANCZOS).save(DRAW/f"swatch_{style}.png")
        CHILD(config,"ListOption",id=str(style-1),displayName=f"palette_{style-1}",screenReaderText=f"desc_{style-1}",icon=f"swatch_{style}")
        variant=CHILD(group,"ListOption",id=str(style-1))
        field=CHILD(variant,"Group",name=f"palette{style}",x="0",y="0",width="480",height="480")
        if style==1:
            from flow import scene as flow_scene
            live=CHILD(field,"Group",name="flow",x="0",y="0",width="480",height="480")
            CHILD(live,"Variant",mode="AMBIENT",target="alpha",value="0")
            flow_scene(live)
        for frame in ((FRAMES,) if style==1 else (0,1,FRAMES)):
            name=f"p{style}f{frame}"
            for family in ([name,f"m1f{frame}"] if style==1 and frame<FRAMES else [name]):
                font=CHILD(fonts,"BitmapFont",name=family)
                for digit in range(10):
                    for zero in (48,0x660,0x6f0,0x966,0xe50):
                        CHILD(font,"Character",name=chr(zero+digit),resource=f"{family}d{digit}",width=str(Image.open(DRAW/f"{family}d{digit}.png").width),height=str(H))
            ambient = frame==FRAMES
            layer=CHILD(field,"Group",name=f"layer{name}",x="0",y="0",width="480",height="480",alpha="0" if ambient else "255")
            CHILD(layer,"Variant",mode="AMBIENT",target="alpha",value="255" if ambient else "0")
            fade=layer
            if frame==1:
                # The opaque base is already visible on wake. Only the second texture blends.
                fade=CHILD(layer,"Group",name=f"sheen{name}",x="0",y="0",width="480",height="480")
                opacity=CHILD(fade,"Transform",target="alpha",value="([SECOND] % 8) < 4 ? 255 : 0")
                CHILD(opacity,"Animation",duration="3.8",fps="30",interpolation="LINEAR")
            scale=1.02 if ambient else 1.04
            for y,fmt in ROWS:
                height=round(H*scale)
                clock=CHILD(fade,"DigitalClock",x="0",y=str(round(240+(y-240)*.95-height/2)),width="480",height=str(height))
                text=CHILD(clock,"TimeText",x="0",y="0",width="480",height=str(height),align="CENTER",format=fmt,hourFormat="SYNC_TO_DEVICE")
                family=f"m1f{frame}" if style==1 and not ambient and fmt=="mm" else name
                CHILD(text,"BitmapFont",family=family,size=str(height),color="#FFFFFF")
    store(ROOT/"res/raw/watchface.xml",root)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("model",type=Path,help="Extracted Watch8_5_24S132 directory")
    args=parser.parse_args()
    props=args.model/"解析/属性表"
    settings=read(props/BUNDLE/"PlumeriaSettings.plist.json")
    localized(props)
    for digit in range(10):
        uv=mesh_uv(args.model/"解析/媒体"/BUNDLE/f"{digit}.usda")
        ambient_uv=mesh_uv(args.model/"解析/媒体"/BUNDLE/f"{digit}.usda",settings["tritiumBase"]["fontEnlargement"])
        for style in range(1,6):
            for phase in (0,1,5,FRAMES):
                if style==1 and phase!=FRAMES:
                    continue
                im=ambient_digit(ambient_uv,settings,style,digit) if phase==FRAMES else render(uv,settings,style,phase,digit,False)
                im.save(DRAW/f"p{style}f{phase}d{digit}.png",compress_level=5)
    # Match both opaque endpoints to one exposure. A moving highlight changes only part
    # of each digit, so the time remains readable even on the first interactive frame.
    for prefix in ("p2","p3","p4","p5"):
        for digit in range(10):
            files=[DRAW/f"{prefix}f{phase}d{digit}.png" for phase in (0,1,5)]
            anchor,positive,negative=[np.asarray(Image.open(f).convert("RGB"),dtype=float) for f in files]
            for dest,endpoint in zip(files, (negative,positive)):
                exposure=anchor.mean()/max(endpoint.mean(),1e-6)
                rgb=.65*anchor+.35*endpoint*exposure
                Image.fromarray(np.clip(np.rint(rgb),0,255).astype("uint8")).save(dest)
            files[2].unlink()
    trim_fonts(args.model/"解析/媒体"/BUNDLE)
    scene(settings)
    from flow import generate
    cfg=dict(settings["base"],**settings["colorway1"])
    generate(args.model/"解析/媒体"/BUNDLE,ROOT/"reference.png",DRAW,mesh_uv,cfg,colors(cfg)/255)
