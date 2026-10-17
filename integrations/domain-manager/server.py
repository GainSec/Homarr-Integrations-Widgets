"""Password-gated narrow UI/API, served over a private Unix socket to Homarr."""
import hashlib,hmac,json,os,secrets,socketserver,threading,time
from pathlib import Path
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,HTTPServer
from engine import DNS,Caddy,Engine,DomainError,atomic
from inventory_health import inventory,site_blocks,HealthCache
from advanced import Advanced
ROOT=Path(__file__).parent
ORIGINS={'https://example.net','http://192.0.2.10:8080'}
def hash_password(password):
 salt=secrets.token_hex(16);return {'salt':salt,'hash':hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()}
def validate_secrets(config):
 for key in ('proxy_token','dns_token'):
  value=config.get(key)
  if not isinstance(value,str) or len(value)<24 or '<' in value:raise ValueError('Replace credential placeholders with private tokens')
class App:
 def __init__(self,config,engine,health=None):self.config=config;self.engine=engine;self.health=health;self.sessions={};self.failures=[];self.mutex=threading.Lock()
 def unlocked(self,cookie):
  try:c=SimpleCookie();c.load(cookie);key=c['dm_session'].value
  except Exception:return False
  return self.sessions.get(key,0)>time.time()
 def dispatch(self,method,path,headers,body):
  if not hmac.compare_digest(headers.get('X-Domain-Proxy','').encode(),self.config['proxy_token'].encode()) or headers.get('Host') not in self.config.get('allowed_hosts',['example.net','192.0.2.10:8080']):return 403,{}, {'error':'Forbidden'}
  if method=='POST' and (headers.get('Origin') not in self.config.get('allowed_origins',ORIGINS) or headers.get('X-Domain-Action')!='1'):return 403,{}, {'error':'Origin rejected'}
  unlocked=self.unlocked(headers.get('Cookie',''))
  if method=='GET' and path in {'/','/app.js','/app.css'}:
   p=ROOT/({'/':'index.html'}.get(path,path[1:]));return 200,{'Content-Type':{'html':'text/html; charset=utf-8','js':'application/javascript','css':'text/css'}[p.suffix[1:]]},p.read_bytes()
  if path=='/api/login' and method=='POST':
   with self.mutex:
    self.failures=[t for t in self.failures if t>time.time()-300]
    if len(self.failures)>=5:return 429,{}, {'error':'Too many attempts. Wait five minutes.'}
    password=body.get('password','')
    if not isinstance(password,str) or len(password)>256:return 400,{}, {'error':'Invalid password'}
    d=self.config['password'];candidate=hashlib.scrypt(password.encode(),salt=bytes.fromhex(d['salt']),n=16384,r=8,p=1).hex()
    if not hmac.compare_digest(candidate,d['hash']):self.failures.append(time.time());return 401,{}, {'error':'Incorrect edit password'}
    self.failures=[];key=secrets.token_urlsafe(32);self.sessions={k:v for k,v in self.sessions.items() if v>time.time()};self.sessions[key]=time.time()+300
   secure='; Secure' if headers.get('X-Forwarded-Proto')=='https' else ''
   return 200,{'Set-Cookie':'dm_session='+key+'; Path=/domain-manager; HttpOnly; SameSite=Strict; Max-Age=300'+secure},{'unlocked':True}
  if path=='/api/logout' and method=='POST':
   try:c=SimpleCookie();c.load(headers.get('Cookie',''));self.sessions.pop(c['dm_session'].value,None)
   except Exception:pass
   return 200,{'Set-Cookie':'dm_session=; Path=/domain-manager; Max-Age=0; HttpOnly; SameSite=Strict'},{'unlocked':False}
  if path=='/api/services' and method=='GET':return 200,{}, self.health.snapshot() if self.health else {'services':{},'checkedAt':None,'stale':True}
  if path in {'/api/site','/api/advanced-preview','/api/advanced-apply'} and method=='POST':
   if not unlocked:return 401,{}, {'error':'Unlock editing first'}
   try:
    advanced=Advanced(self.engine)
    if path=='/api/site':
     site=advanced.site(body.get('id'));return 200,{}, {'id':site['id'],'hosts':site['hosts'],'text':site['text'],'revision':self.engine.revision()}
    if path=='/api/advanced-preview':
     site,_,_=advanced.preview(body.get('id'),body.get('text'),body.get('revision'));return 200,{}, {'hosts':site['hosts'],'revision':body.get('revision')}
    return 200,{}, advanced.apply(body.get('id'),body.get('text'),body.get('revision'))
   except DomainError as e:return 409,{}, {'error':str(e)}
  if path=='/api/state' and method=='GET':
   try:zones=self.engine.dns.zones();error=None
   except DomainError:zones=[];error='Technitium is unavailable or its zone permissions need attention.'
   zones=[{'name':z['name'],'type':z['type']} for z in zones if z.get('type')=='Primary' and not z.get('disabled') and not z.get('internal') and z.get('name') and not z['name'].endswith('.arpa')]
   inventory_error=None
   try:
    rows=inventory(self.engine.caddy.export());sites=site_blocks(self.engine.file.read_text());managed={r['hostname']:r for r in self.engine.routes()}
    for row in rows:
     site=next((s for s in sites if row['hostname'] in s['hosts']),None);row['siteId']=site['id'] if site else None;row['managedId']=managed.get(row['hostname'],{}).get('id')
   except Exception:rows=[];inventory_error='Caddy inventory is unavailable.'
   return 200,{}, {'inventory':rows,'inventoryError':inventory_error,'zones':zones,'routes':[{k:v for k,v in r.items() if k in {'id','hostname','zone','label','upstream','tls','skipVerify'}} for r in self.engine.routes()],'revision':self.engine.revision(),'unlocked':unlocked,'dnsError':error,'recoveryRequired':self.engine.pending.exists(),'proxyAddress':getattr(self.engine.dns,'proxy_address','192.0.2.10'),'tlsZones':__import__('engine').TLS_ZONES}
  if path in {'/api/preview','/api/apply'} and method=='POST':
   if not unlocked:return 401,{}, {'error':'Unlock editing first'}
   try:
    kind=body.get('operation');fields=body.get('route',{});revision=body.get('revision','')
    if path=='/api/preview':
     route,_,_=self.engine.preview(kind,fields,revision);return 200,{}, {'route':route,'revision':revision,'operation':kind}
    route=self.engine.apply(kind,fields,revision);return 200,{}, {'route':route,'operation':kind}
   except DomainError as e:return 409,{}, {'error':str(e)}
  return 404,{}, {'error':'Not found'}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):self.handle_request()
 def do_POST(self):self.handle_request()
 def handle_request(self):
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length<0 or length>16384:raise ValueError()
   body=json.loads(self.rfile.read(length)) if length else {}
   if not isinstance(body,dict):raise ValueError()
   status,headers,data=self.server.app.dispatch(self.command,self.path.split('?',1)[0],self.headers,body)
  except (ValueError,json.JSONDecodeError):status,headers,data=400,{}, {'error':'Invalid request'}
  except Exception:status,headers,data=500,{}, {'error':'Operation failed. Private backups and recovery details were retained.'}
  raw=data if isinstance(data,bytes) else json.dumps(data).encode();self.send_response(status)
  defaults={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'",'Content-Length':str(len(raw))}
  for k,v in {**defaults,**headers}.items():self.send_header(k,v)
  self.end_headers()
  try:self.wfile.write(raw)
  except (BrokenPipeError,ConnectionResetError):pass
class Server(socketserver.ThreadingMixIn,HTTPServer):
 daemon_threads=True
 def __init__(self,address,app):self.app=app;super().__init__(address,Handler)
class UnixServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
 daemon_threads=True
 def __init__(self,path,app):self.app=app;super().__init__(path,Handler)
if __name__=='__main__':
 config=json.loads(Path(os.environ.get('DOMAIN_MANAGER_CONFIG','/etc/homarr-domain-manager/config.json')).read_text())
 validate_secrets(config)
 engine=Engine(config['state_dir'],Path(config['caddyfile']),DNS(config['dns_url'],config['dns_token'],config['proxy_address']),Caddy(config['caddy_container']))
 try:engine.recover()
 except Exception:pass # Remain read-only with a visible recovery-required state.
 sock=Path(config['socket_path']);sock.unlink(missing_ok=True)
 server=UnixServer(str(sock),App(config,engine));os.chown(str(sock),0,int(config['socket_gid']));os.chmod(str(sock),0o660)
 server.serve_forever()
