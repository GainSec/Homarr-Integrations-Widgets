"""Allowlisted quota snapshots; never expose client credentials or session data."""
import json,math,os,time,tempfile
from pathlib import Path

def number(x):
 return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def window(label,used,reset,minutes,now):
 if not all(number(v) for v in (used,reset,minutes)) or not 0<=used<=100 or not now<reset<now+366*86400 or not 0<minutes<=527040:return None
 return {'label':label,'usedPercent':float(used),'resetsAt':int(reset),'windowMinutes':int(minutes)}

def normalize_codex(raw,now=None):
 now=time.time() if now is None else now;windows=[]
 limits=raw.get('rateLimits') or {}
 for key in ('primary','secondary'):
  w=limits.get(key) or {};mins=w.get('windowDurationMins')
  label='5-hour' if mins==300 else 'Weekly' if mins==10080 else str(mins)+' min'
  value=window(label,w.get('usedPercent'),w.get('resetsAt'),mins,now)
  if value:windows.append(value)
 return {'capturedAt':int(now),'windows':windows}

def normalize_claude(raw,now=None):
 now=time.time() if now is None else now;windows=[]
 for key,label,minutes in [('five_hour','5-hour',300),('seven_day','Weekly',10080)]:
  w=(raw.get('rate_limits') or {}).get(key) or {}
  value=window(label,w.get('used_percentage'),w.get('resets_at'),minutes,now)
  if value:windows.append(value)
 return {'capturedAt':int(now),'windows':windows}

def snapshot(raw,now=None):
 now=time.time() if now is None else now;result={}
 if not isinstance(raw,dict):raw={}
 for provider in ('codex','claude'):
  x=raw.get(provider);x=x if isinstance(x,dict) else {};stamp=x.get('capturedAt')
  valid=number(stamp) and 0<stamp<=now+60;windows=[]
  values=x.get('windows') if isinstance(x.get('windows'),list) else []
  for w in values[:4]:
   if not isinstance(w,dict):continue
   mins=w.get('windowMinutes');label='5-hour' if mins==300 else 'Weekly' if mins==10080 else (str(int(mins))+' min' if number(mins) else '')
   v=window(label,w.get('usedPercent'),w.get('resetsAt'),mins,now)
   if valid and v:
    left=int(v['resetsAt']-now)
    days,left=divmod(left,86400);hours,seconds=divmod(left,3600);minutes=max(1,seconds//60)
    v['resetText']=str(days)+'d '+str(hours)+'h' if days else str(hours)+'h '+str(minutes)+'m' if hours else str(minutes)+'m'
    v['resetAtUtc']=time.strftime('%Y-%m-%d %H:%M UTC',time.gmtime(v['resetsAt']))
    windows.append(v)
  stale=valid and now-stamp>300
  result[provider]={'capturedAt':int(stamp) if valid else None,'windows':windows,'stale':bool(stale),'state':'stale' if windows and stale else 'ready' if windows else 'unavailable','ageText':('just now' if now-stamp<60 else str(max(1,int((now-stamp)//60)))+'m ago') if valid else ''}
 result['servedAt']=int(now)
 return result

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f)
  os.chmod(name,0o600);os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def ingest(body,path,now=None):
 if len(body)>16384:raise ValueError('Too large')
 value=json.loads(body)
 if not isinstance(value,dict):raise ValueError('Expected object')
 value=snapshot(value,now);atomic_json(path,value)
 return value

class UsageClient:
 def __init__(self,path=None):self.path=Path(path) if path else Path(__file__).parent/'usage.json'
 def read(self):
  try:raw=json.loads(self.path.read_text())
  except (OSError,ValueError):raw={}
  return snapshot(raw)

if __name__=='__main__':
 import sys
 # Forced-command receiver: original SSH command is deliberately ignored.
 ingest(sys.stdin.buffer.read(16385),Path(__file__).parent/'usage.json')
 print('Usage snapshot received')
