from .config import ROOT,cfg
from .analyzer import probe,scenes,thumbnail,sha
from . import db
from pathlib import Path
import json,uuid
def category(meta): return 'autre'
def create(p):
 digest=sha(p)
 if db.known(digest): return None
 pid=str(uuid.uuid4()); work=ROOT/'workspace'/pid; cuts=scenes(p,work); dur=float(probe(p)['format']['duration']); items=[]
 for i,start in enumerate(cuts):
  end=cuts[i+1] if i+1<len(cuts) else dur; thumb=work/f'scene-{i+1:03}.jpg'; thumbnail(p,start,thumb); items.append({'id':f'scene-{i+1:03}','start_seconds':start,'end_seconds':end,'thumbnail':str(thumb.relative_to(ROOT)),'selected':True})
 plan={'schema_version':1,'plan_id':pid,'source':{'path':str(p),'sha256':digest},'category':category({}),'status':'pending_human_review','scenes':items,'exports':[{'profile':k,'output':str((ROOT/'output'/f'{pid}-{k}.mp4').relative_to(ROOT)),'status':'pending'} for k in cfg()['profiles']],'human_validation':{'approved':False,'approved_at':None}}
 out=ROOT/'projects'/f'{pid}.json'; out.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n'); db.add(digest,str(p),pid); return out
