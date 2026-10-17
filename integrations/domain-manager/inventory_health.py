"""Secret-free Caddy inventory and bounded read-only checks of a fixed catalog."""
import hashlib,http.client,json,socket,ssl,threading,time,os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin

def inventory(config):
 rows={}
 def visit(value,hosts,server):
  if isinstance(value,dict):
   matches=value.get('match',[])
   found=[h for m in matches if isinstance(m,dict) for h in m.get('host',[]) if isinstance(h,str)] if isinstance(matches,list) else []
   if found:hosts=found
   for host in hosts:
    key=(server,host);rows.setdefault(key,{'id':hashlib.sha256((server+'|'+host).encode()).hexdigest()[:20],'hostname':host,'server':server,'upstreams':[],'handlers':[]})
    handler=value.get('handler')
    if handler and handler not in rows[key]['handlers']:rows[key]['handlers'].append(handler)
    if handler=='reverse_proxy':
     for u in value.get('upstreams',[]):
      dial=u.get('dial') if isinstance(u,dict) else None
      if isinstance(dial,str) and dial not in rows[key]['upstreams']:rows[key]['upstreams'].append(dial)
     if value.get('dynamic_upstreams') and 'dynamic upstream' not in rows[key]['upstreams']:rows[key]['upstreams'].append('dynamic upstream')
   for key,child in value.items():
    if key not in {'match','headers','transport','upstreams','logs'}:visit(child,hosts,server)
  elif isinstance(value,list):
   for child in value:visit(child,hosts,server)
 for server,cfg in config.get('apps',{}).get('http',{}).get('servers',{}).items():visit(cfg.get('routes',[]),[],server)
 return sorted(rows.values(),key=lambda r:(r['hostname'],r['server']))

class FrontdoorHTTPS(http.client.HTTPSConnection):
 def __init__(self,host,port,frontdoor,timeout):super().__init__(host,port,timeout=timeout,context=ssl.create_default_context());self.frontdoor=frontdoor
 def connect(self):self.sock=self._context.wrap_socket(socket.create_connection((self.frontdoor,self.port),self.timeout),server_hostname=self.host)

def probe(url,frontdoor=None,timeout=4):
 started=time.monotonic();current=url
 try:
  for step in range(5):
   u=urlsplit(current)
   if u.scheme not in {'http','https'} or not u.hostname or u.username is not None or u.password is not None:raise ValueError('Invalid URL')
   port=u.port or (443 if u.scheme=='https' else 80);mapped=frontdoor and any(u.hostname==z or u.hostname.endswith('.'+z) for z in os.environ.get('HEALTH_FRONTDOOR_DOMAINS','example.net').split(','))
   if mapped and u.scheme=='https':c=FrontdoorHTTPS(u.hostname,port,frontdoor,timeout)
   elif mapped:c=http.client.HTTPConnection(frontdoor,port,timeout=timeout)
   else:c=(http.client.HTTPSConnection if u.scheme=='https' else http.client.HTTPConnection)(u.hostname,port,timeout=timeout)
   try:
    path=(u.path or '/')+('?' +u.query if u.query else '');c.request('GET',path,headers={'Host':u.netloc,'User-Agent':'Homarr-Service-Status/1.0','Accept':'text/html,application/json;q=0.9,*/*;q=0.5','Connection':'close'});response=c.getresponse();code=response.status;location=response.getheader('Location');response.read(1024)
   finally:c.close()
   if code in {301,302,303,307,308} and location:
    current=urljoin(current,location);continue
   state='responding' if 200<=code<400 else 'auth' if code in {401,403} else 'unavailable'
   return {'state':state,'status':code,'latencyMs':round((time.monotonic()-started)*1000),'checkedAt':time.time()}
  raise ValueError('Redirect limit')
 except Exception as e:
  reason='TLS verification failed' if isinstance(e,ssl.SSLError) else 'Timed out' if isinstance(e,(TimeoutError,socket.timeout)) else 'Connection or redirect failed'
  return {'state':'unavailable','status':None,'reason':reason,'checkedAt':time.time()}

class HealthCache:
 def __init__(self,catalog,interval=60,frontdoor=None):
  self.urls=list(dict.fromkeys(x['url'] for x in catalog));self.checks={x['url']:x.get('checkUrl',x['url']) for x in catalog};self.interval=interval;self.frontdoor=frontdoor;self.lock=threading.Lock();self.results={};self.checked=0;self.polling=False
 def refresh(self):
  with self.lock:
   if self.polling:return
   self.polling=True
  try:
   with ThreadPoolExecutor(max_workers=6) as pool:values=list(pool.map(lambda u:probe(self.checks[u],self.frontdoor),self.urls))
   with self.lock:self.results=dict(zip(self.urls,values));self.checked=time.time()
  finally:
   with self.lock:self.polling=False
 def snapshot(self):
  with self.lock:return {'services':dict(self.results),'checkedAt':self.checked or None,'stale':not self.checked or time.time()-self.checked>self.interval*3,'refreshing':self.polling,'intervalSeconds':self.interval}
 def start(self):
  def run():
   while True:
    try:self.refresh()
    except Exception:pass
    time.sleep(self.interval)
  threading.Thread(target=run,daemon=True,name='service-health').start()

# Locate only literal top-level site blocks. Caddy performs final syntax validation.
# Placeholder braces are part of tokens; quoted/backtick strings/comments are opaque.
def _tokens(text):
 i=0
 while i<len(text):
  if text[i].isspace():i+=1;continue
  if text[i]=='#':
   i=text.find('\n',i)
   if i<0:return
   continue
  start=i
  if text[i] in {'"','`'}:
   quote=text[i];i+=1
   while i<len(text):
    if text[i]=='\\' and quote=='"':i+=2;continue
    if text[i]==quote:i+=1;break
    i+=1
   else:raise ValueError('Unclosed quoted value')
   yield text[start:i],start,i;continue
  while i<len(text) and not text[i].isspace():i+=1
  yield text[start:i],start,i

def site_blocks(text):
 tokens=list(_tokens(text));depth=0;header=[];result=[];start=None;opening=None
 for token,a,b in tokens:
  if depth==0 and header and header[0][0]=='import' and '\n' in text[header[-1][2]:a]:header=[]
  if token=='{':
   if depth==0:start=header[0][1] if header else a;opening=a;names=[x[0] for x in header]
   depth+=1
  elif token=='}':
   depth-=1
   if depth<0:raise ValueError('Unbalanced block')
   if depth==0:
    if names and names[0]!='import' and not names[0].startswith('('):
     hosts=[]
     for address in names:
      for part in address.split(','):
       part=part.strip('"')
       if not part:continue
       parsed=urlsplit(part if '://' in part else '//'+part)
       if parsed.hostname:hosts.append(parsed.hostname.lower())
     if hosts:
      raw=text[start:b];result.append({'id':hashlib.sha256((' '.join(names)).encode()).hexdigest()[:20],'hosts':sorted(set(hosts)),'start':start,'end':b,'text':raw,'header':text[start:opening].strip()})
    header=[]
  elif depth==0:header.append((token,a,b))
 if depth:raise ValueError('Unbalanced block')
 return result

def validate_site_block(text,hosts):
 if not isinstance(text,str) or len(text)>12000:raise ValueError('Site block is too large')
 from engine import BEGIN,END
 if BEGIN.strip() in text or END.strip() in text:raise ValueError('Manager boundary comments are reserved; paste only the site block')
 text=text.strip();sites=site_blocks(text)
 if len(sites)!=1 or sorted(sites[0]['hosts'])!=sorted(hosts) or text[:sites[0]['start']].strip() or text[sites[0]['end']:].strip():raise ValueError('Paste one complete site block and preserve its hostname(s)')
 return text+'\n'
