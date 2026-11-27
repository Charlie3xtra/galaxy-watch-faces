"""Package the extracted provider catalogs and index their original firmware paths."""
import csv,io,json,hashlib,zipfile,os
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parent
fw=root.parent/'Watch8_5_24S132'
if os.name=='nt':fw=Path(chr(92)*2+'?'+chr(92)+str(fw))
labels=json.loads((root.parent/'表盘资料/健身记录数字/官方资料.json').read_text('utf8'))['options'][1].split('：')[-1].split(' • ')
keys=['ActivityMonitor|ActivityComplication','Alarm','NanoUniverse|Astronomy','NanoBooks','Battery','Oxygen','Calculator','Calendar','Camera','Cellular','Compass','Waypoint|Compass','Contacts','Menstrual','Depth','Electrocardiogram','Find','HeartRate','NanoHome','NanoMail','Maps','Dose|Medication','Messages|MobileSMS','Mindfulness|Breathe','NanoMusic','MusicRecognition','Noise','Notes','NanoPhone','Podcast','Reminders','Remote','Shortcuts','NanoSleep','Stock','Stopwatch','Tides','TimeComplication|DateComplications','Timer','Tips','Translate','VoiceMemo','Vitals','PassKit|Wallet','Weather','Workout','WorldClock']
assert len(keys)==len(labels),(len(keys),len(labels))
import re
providers=json.loads((fw/'组件提供程序.json').read_text('utf8'))
files=[]
for base in (fw/'filesystem',fw/'组件提供程序',fw/'解析/图集',fw/'提供程序解析/图集'):
    for p in base.rglob('*') if '图集' in base.parts else base.rglob('*.car'):
        if not p.is_file() or ('FaceBundles' in p.parts and 'NTKActivityFaceBundle.bundle' not in p.parts):continue
        if '图集' in base.parts and ('资源' not in p.parts and p.name not in ('导出记录.json','选定符号导出.json')):continue
        files.append(p)
dest=root/'ActivityDigital-24S132-assets.zip'
def csv_bytes(headers,rows):
    mem=io.StringIO(newline='');w=csv.writer(mem);w.writerow(headers);w.writerows(rows)
    return mem.getvalue().encode('utf-8-sig')
rows=[]; seen={}; tagged=defaultdict(set)
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p in sorted(files):
        f=p.relative_to(fw).as_posix()
        data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest not in seen:
            entry='assets/'+digest[:16]+'/'+p.name
            z.writestr(entry,data);seen[digest]=entry
        matches=[lbl for lbl,pat in zip(labels,keys) if re.search(pat,f,re.I)]
        for lbl in matches:tagged[lbl].add(f)
        rows.append((';'.join(matches),f,seen[digest],digest))
    z.writestr('资源路径.csv',csv_bytes(['类别线索','原始路径','压缩包内文件','SHA256'],rows))
    mapping=[]
    for lbl,pat in zip(labels,keys):
        candidates=sorted({v['id'] for k,v in providers.items() if re.search(pat,k+v['id'],re.I)})
        mapping.append((lbl,';'.join(candidates),len(tagged[lbl]),'按固件路径匹配；设备渲染行为须单独核实'))
    z.writestr('组件对照.csv',csv_bytes(['原版组件','候选提供程序','匹配的资源路径数','对应依据'],mapping))
    z.writestr('提供程序.json',json.dumps(providers,ensure_ascii=False,indent=1))
print(len(labels),len(rows),len(seen),dest.stat().st_size)


