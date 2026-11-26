"""Decode 24S132 Dolomite's minute tables and normalized Core Graphics paths.

Each hourly font maps private-use glyphs to a minute and a sampled morph phase.
Curves remain cubic at every phase; WFF selects a glyph from local clock time.
"""
from pathlib import Path
import struct
from functools import lru_cache
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString, encodeIntT2

ROOT=Path(__file__).resolve().parent
binary=(ROOT.parent/'Watch8_5_24S132/解析/代码/NTKDolomiteFaceBundle/NTKDolomiteFaceBundle').read_bytes()
segments=[]
pos=32
for _ in range(struct.unpack_from('<I',binary,16)[0]):
    cmd,size=struct.unpack_from('<II',binary,pos)
    if cmd==25:
        vm,_,offset,length=struct.unpack_from('<QQQQ',binary,pos+24)
        segments.append((vm,vm+length,offset))
    pos+=size
def offset(address):
    for start,end,base in segments:
        if start<=address<end: return base+address-start
    raise ValueError(hex(address))
def dynamic_colors():
    return [np.rint(255*np.clip(np.frombuffer(binary,'<f8',42,offset(a)).reshape(14,3),0,1)).astype(int) for a in (0x2117f7ba0,0x2117f7cf0)]
tables={'western':(0x210aad5c0,0x210abe3c0),'eastern':(0x210ac6ac0,0x210ad78c0),'deva':(0x210adffc0,0x210af0dc0)}
words=np.frombuffer(binary,'<u4',3407000,offset(0x210af94c0))
# Type 2 relative move, line and cubic operators, indexed by their operand counts.
ops={2:bytes([21]),-2:bytes([5]),6:bytes([8])}
@lru_cache(maxsize=4096)
def path(key):
    if key==0:return (),np.empty((0,2))
    i=key+1
    move=True
    pts=[]
    commands=[]
    for _ in range(words[key]):
        if move:
            pts.append(words[i]);commands.append(2);i+=1;move=False
        op=int(words[i]);i+=1
        if op==0xffffffff:move=True
        elif op==0xfffffffe:
            pts.append(words[i]);commands.append(-2);i+=1
        elif op==0xfffffffd:
            pts.extend((words[i+1],words[i+2],words[i]));commands.append(6);i+=3
        else:raise ValueError((key,hex(op)))
    p=np.array(pts,dtype='uint32')
    return tuple(commands),np.column_stack(((p>>16)*(1000/32767),1000-(p&65535)*(1000/65535)))
def ease(x):
    lo,hi=0.,1.
    for _ in range(32):
        t=(lo+hi)/2
        if 3*(1-t)**2*t*.42+3*(1-t)*t*t*.58+t**3<x:lo=t
        else:hi=t
    return t*t*(3-2*t)
# KeyTimes 0, .4999, .5, 1; duration .250s; kCAMediaTimingFunctionEaseInEaseOut.
weights=[0]+[min(1,ease(i/16)/.4999) for i in range(1,9)]+[(1-ease(i/16))*2 for i in range(8,16)]
enc={i:encodeIntT2(i) for i in range(-3000,3001)}
def scene(row,frame):
    segments=[];ops_all=[]
    for k,target in zip(row[0],row[1 if frame<=8 else 2]):
        cmds,points=path(int(k))
        if frame:
            target_cmds,other=path(int(target))
            if cmds==target_cmds: points=points+(other-points)*weights[frame]
            elif weights[frame]>=.5:cmds,points=target_cmds,other
        segments.append(points);ops_all.extend(cmds)
    p=np.rint(np.concatenate(segments)).astype(int)
    if not len(p):return b'\x0e'
    p[1:]-=p[:-1].copy()
    numbers=[enc[x] for x in p.ravel().tolist()]
    # Operands interleaved with the Type 2 drawing operators.
    out=[];i=0
    for op in ops_all:
        n=abs(op);out.extend(numbers[i:i+n]);out.append(ops[op]);i+=n
    return b''.join(out)+b'\x0e'
def build_fonts():
    dest=ROOT/'res/font';dest.mkdir(exist_ok=True)
    for script,addresses in tables.items():
        for mode,(hours,addr) in enumerate(zip((24,12),addresses)):
            data=np.frombuffer(binary,'<u4',hours*60*12,offset(addr)).reshape(hours,60,3,4)
            for h,minutes in enumerate(data):
                name=f'flux_{script}_{mode}_{h}'
                fb=FontBuilder(1000,isTTF=False)
                notdef=T2CharString(bytecode=b'\x0e')
                chars={'.notdef':notdef};cmap={};metrics={'.notdef':(1000,0)}
                for m,row in enumerate(minutes):
                    for phase in range(17):
                        ix=m*17+phase;g=f'g{ix}'
                        chars[g]=T2CharString(bytecode=scene(row,phase))
                        cmap[0xe000+ix]=g;metrics[g]=(1000,0)
                fb.setupGlyphOrder(list(chars));fb.setupCharacterMap(cmap)
                fb.setupCFF(name,{'FullName':name,'FamilyName':name,'Weight':'Regular'},chars,{'defaultWidthX':1000})
                fb.setupHorizontalMetrics(metrics);fb.setupHorizontalHeader(ascent=1000,descent=0)
                fb.setupNameTable({'familyName':name,'styleName':'Regular','psName':name})
                fb.setupOS2(sTypoAscender=1000,sTypoDescender=0,usWinAscent=1000,usWinDescent=0)
                fb.setupPost()
                fb.font.recalcBBoxes=False
                fb.font['CFF '].cff.topDictIndex[0].FontBBox=[-100,-100,1100,1100]
                fb.save(dest/(name+'.otf'))
                # Ambient uses only 60 resting outlines, with no transition resources.
                static={k:v for k,v in chars.items() if not k.startswith('g') or int(k[1:])%17==0}
                ab=FontBuilder(1000,isTTF=False)
                ab.setupGlyphOrder(list(static));ab.setupCharacterMap({c:g for c,g in cmap.items() if g in static})
                ab.setupCFF(name+'a',{'FullName':name+'a','FamilyName':name+'a','Weight':'Regular'},static,{'defaultWidthX':1000})
                ab.setupHorizontalMetrics({g:metrics[g] for g in static});ab.setupHorizontalHeader(ascent=1000,descent=0)
                ab.setupNameTable({'familyName':name+'a','styleName':'Regular','psName':name+'a'})
                ab.setupOS2(sTypoAscender=1000,sTypoDescender=0,usWinAscent=1000,usWinDescent=0)
                ab.setupPost();ab.font.recalcBBoxes=False
                ab.font['CFF '].cff.topDictIndex[0].FontBBox=[-100,-100,1100,1100]
                ab.save(dest/(name+'a.otf'))
if __name__=='__main__':build_fonts()
