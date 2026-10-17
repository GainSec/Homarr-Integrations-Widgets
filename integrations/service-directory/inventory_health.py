"""Secret-free Caddy inventory and bounded read-only checks of a fixed catalog."""
import hashlib,http.client,json,socket,ssl,threading,time,os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin

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
