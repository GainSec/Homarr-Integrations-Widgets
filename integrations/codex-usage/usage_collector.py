"""Local quota-only collector; signed-in client credentials never leave this host."""
import json,os,selectors,subprocess,sys,time,threading,shutil
from pathlib import Path
from usage_metadata import normalize_codex,normalize_claude,snapshot,atomic_json
from collector_http import serve
ROOT=Path(os.environ.get('USAGE_CACHE_DIR',str(Path.home()/'.local/share/homarr-codex-usage'))).expanduser()

def read_json(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}

def codex_read(binary=None):
 binary=binary or os.environ.get('CODEX_BINARY') or shutil.which('codex')
 if not binary:raise RuntimeError('Codex CLI not found')
 p=subprocess.Popen([binary,'app-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
 selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
 def send(value):p.stdin.write((json.dumps(value)+'\n').encode());p.stdin.flush()
 try:
  send({'id':0,'method':'initialize','params':{'clientInfo':{'name':'homarr_usage','title':'Homarr quota collector','version':'1.0.0'}}})
  deadline=time.monotonic()+25;buffer=b''
  while time.monotonic()<deadline:
   if not selector.select(1):continue
   chunk=os.read(p.stdout.fileno(),65536)
   if not chunk:raise RuntimeError('Client closed')
   buffer+=chunk
   if len(buffer)>1048576:raise RuntimeError('Client response too large')
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1)
    if not line.strip():continue
    value=json.loads(line)
    if 'error' in value:raise RuntimeError('Client could not read limits')
    if value.get('id')==0:
     send({'method':'initialized','params':{}});send({'id':1,'method':'account/rateLimits/read'})
    elif value.get('id')==1:return normalize_codex(value.get('result') or {})
  raise TimeoutError('Client timeout')
 finally:
  selector.close();p.terminate()
  try:p.wait(3)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  p.stdin.close();p.stdout.close()

def collect(root=ROOT):
 last=read_json(root/'snapshot.json')
 try:
  value=codex_read()
  if value['windows']:last['codex']=value
 except Exception:pass  # A failed poll cannot renew the last successful timestamp.
 clean={'codex':snapshot(last)['codex']};atomic_json(root/'snapshot.json',clean)
 return clean

def poll():
 while True:
  try:collect()
  except Exception:pass
  time.sleep(60)

def read(path):
 if path!='/usage/status':raise LookupError(path)
 return {'codex':snapshot(read_json(ROOT/'snapshot.json'))['codex']}

if __name__=='__main__':
 threading.Thread(target=poll,daemon=True).start()
 serve(read,default_port=18088)
