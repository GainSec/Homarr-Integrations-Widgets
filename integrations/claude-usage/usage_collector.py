"""Local quota-only collector; signed-in client credentials never leave this host."""
import json,os,selectors,subprocess,sys,time,threading,shutil
from pathlib import Path
from usage_metadata import normalize_codex,normalize_claude,snapshot,atomic_json
from collector_http import serve
ROOT=Path(os.environ.get('USAGE_CACHE_DIR',str(Path.home()/'.local/share/homarr-claude-usage'))).expanduser()

def read_json(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}

def hook(root=ROOT):
 try:
  raw=json.loads(sys.stdin.buffer.read(1048577));value=normalize_claude(raw)
  if value['windows']:atomic_json(root/'claude.json',value)
  else:value=read_json(root/'claude.json')
  clean=snapshot({'claude':value})['claude']
  print(' · '.join(w['label']+' '+str(round(w['usedPercent']))+'%' for w in clean['windows']) or 'Claude usage: awaiting limits')
 except Exception:print('Claude usage: unavailable')

def read(path):
 if path!='/usage/status':raise LookupError(path)
 return {'claude':snapshot({'claude':read_json(ROOT/'claude.json')})['claude']}

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='hook':hook()
 else:serve(read,default_port=18089)
