from .config import ROOT,cfg
import hashlib,json,subprocess
from pathlib import Path
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def probe(p):
 r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(p)],capture_output=True,text=True,check=True); return json.loads(r.stdout)
def scenes(p,work):
 work.mkdir(parents=True,exist_ok=True); threshold=str(cfg()['scene_threshold']); r=subprocess.run(['ffmpeg','-hide_banner','-i',str(p),'-vf',f"select='gt(scene,{threshold})',showinfo",'-an','-f','null','-'],capture_output=True,text=True); times=[]
 for line in r.stderr.splitlines():
  if 'pts_time:' in line:
   try: times.append(float(line.split('pts_time:')[1].split()[0]))
   except ValueError: pass
 return sorted(set([0.0]+times))
def thumbnail(p,t,target): subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',str(p),'-frames:v','1','-q:v','3',str(target)],check=True,capture_output=True)
