"""Configure credential-free widget URLs without embedding authentication."""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit

def checked_url(value):
 p=urlsplit(value)
 if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.query or p.fragment or any(c in value for c in '\"\'<>\\\r\n'):raise ValueError('Use an HTTP(S) URL with no credentials, query or fragment')
 return value.rstrip('/')

def configure(value,collector_url,app_url=None,network_scope='private'):
 # Replace only documented placeholder origins; never touch arbitrary source code.
 value=json.loads(json.dumps(value));value['sources']['default']['baseUrl']=checked_url(collector_url);value['sources']['default']['networkScope']=network_scope
 if app_url:
  app_url=checked_url(app_url)
  def walk(x):
   if isinstance(x,str):return x.replace('https://app.example.net',app_url)
   if isinstance(x,list):return [walk(v) for v in x]
   if isinstance(x,dict):return {k:walk(v) for k,v in x.items()}
   return x
  value=walk(value)
 return value

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collector-url',required=True);p.add_argument('--app-url');p.add_argument('--network-scope',choices=['private','public','loopback'],default='private');p.add_argument('--input',default='widget.json');p.add_argument('--output',default='widget.configured.json');a=p.parse_args()
 value=configure(json.loads(Path(a.input).read_text()),a.collector_url,a.app_url,a.network_scope);Path(a.output).write_text(json.dumps(value,indent=2)+'\n');print('Wrote credential-free widget configuration to '+a.output)
