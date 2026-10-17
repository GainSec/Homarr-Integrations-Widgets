"""Typed, backed-up Caddy + Technitium transactions. No general command API."""
import copy,fcntl,hashlib,ipaddress,json,os,re,subprocess,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.request import Request,urlopen
MANAGER_LABEL=os.environ.get('DOMAIN_MANAGER_LABEL','Homarr Domains')
MARKER=os.environ.get('DOMAIN_MANAGER_MARKER','HOMARR MANAGED DOMAINS')
TLS_SNIPPET=os.environ.get('DOMAIN_MANAGER_TLS_SNIPPET','homarr_tls')
TLS_ZONES=os.environ.get('DOMAIN_MANAGER_TLS_ZONES','example.net').split(',')
PROXY_ADDRESS=os.environ.get('DOMAIN_MANAGER_PROXY_ADDRESS','192.0.2.10')
if not re.fullmatch(r'[A-Z0-9 _-]+',MARKER) or not re.fullmatch(r'[a-zA-Z0-9_-]+',TLS_SNIPPET):raise ValueError('Invalid marker or TLS snippet')
BEGIN='# BEGIN '+MARKER+'\n';END='# END '+MARKER+'\n'
class DomainError(Exception):pass

def atomic(path,value):
 path=Path(path);tmp=path.with_suffix('.tmp');data=json.dumps(value,indent=2).encode();fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(str(tmp),str(path));fd=os.open(str(path.parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def write_in_place(path,text):
 with open(path,'r+',encoding='utf8') as f:f.seek(0);f.write(text);f.truncate();f.flush();os.fsync(f.fileno())
def domain(value):
 if not isinstance(value,str) or len(value)>253 or value!=value.strip():raise DomainError('Invalid DNS name')
 value=value.lower().rstrip('.')
 if not value or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',p) for p in value.split('.')):raise DomainError('Use DNS labels with letters, numbers and hyphens')
 return value

def validate_route(body,zones):
 if not isinstance(body,dict):raise DomainError('Invalid request')
 zone=domain(body.get('zone'));label=domain(body.get('label'));hostname=domain(label+'.'+zone)
 allowed={z['name'].lower().rstrip('.') for z in zones if z.get('type')=='Primary' and not z.get('disabled') and not z.get('internal') and not z['name'].endswith(('.arpa','.localhost'))}
 if zone not in allowed:raise DomainError('Select an authorized primary forward zone')
 raw=body.get('upstream','')
 if not isinstance(raw,str) or any(c.isspace() for c in raw):raise DomainError('Invalid upstream')
 try:
  u=urlsplit(raw);port=u.port;host=u.hostname
  if u.scheme not in {'http','https'} or not host or u.username is not None or u.password is not None or u.path not in {'','/'} or u.query or u.fragment:raise ValueError()
  try:
   addr=ipaddress.ip_address(host)
   if addr.is_loopback or addr.is_unspecified or addr.is_link_local or addr.is_multicast:raise ValueError()
  except ValueError:
   # An IP-shaped or reserved host must not fall back to DNS-name validation.
   if ':' in host or re.fullmatch(r'[0-9.]+',host) or host in {'localhost'}:raise
   domain(host)
  if port is not None and not 1<=port<=65535:raise ValueError()
 except (ValueError,TypeError):raise DomainError('Use an HTTP(S) service host and port, without credentials or paths')
 hostpart='['+host+']' if ':' in host else host
 tls=body.get('tls','existing')
 if tls not in {'existing','internal'}:raise DomainError('Invalid TLS choice')
 if tls=='existing' and not (any(hostname.endswith('.'+z) for z in TLS_ZONES)):raise DomainError('This zone needs Internal CA TLS')
 if not isinstance(body.get('skipVerify',False),bool):raise DomainError('Invalid certificate option')
 return {'zone':zone,'label':label,'hostname':hostname,'upstream':u.scheme+'://'+hostpart+(':'+str(port) if port else ''),'tls':tls,'skipVerify':body.get('skipVerify',False)}

def render_config(text,routes):
 if text.count(BEGIN)!=text.count(END) or text.count(BEGIN)>1:raise DomainError('Managed block markers were changed manually')
 if BEGIN in text:
  before,rest=text.split(BEGIN,1);_,after=rest.split(END,1)
 else:before,after=text,''
 if not routes:return before+after
 if before and not before.endswith('\n'):before+='\n'
 lines=[BEGIN.rstrip('\n')]
 for r in routes:
  if r.get('siteBlock'):
   lines.extend(['# '+r['id'],r['siteBlock'].rstrip('\n')]);continue
  lines.extend(['# '+r['id'],r['hostname']+' {','  import '+TLS_SNIPPET if r['tls']=='existing' else '  tls internal'])
  if r['skipVerify'] and r['upstream'].startswith('https://'):
   lines.extend(['  reverse_proxy '+r['upstream']+' {','    transport http {','      tls_insecure_skip_verify','    }','  }'])
  else:lines.append('  reverse_proxy '+r['upstream'])
  lines.append('}')
 lines.append(END.rstrip('\n'));return before+'\n'.join(lines)+'\n'+after

class DNS:
 def __init__(self,url,token,proxy_address=PROXY_ADDRESS):self.url=url.rstrip('/');self.token=token;self.proxy_address=str(ipaddress.IPv4Address(proxy_address))
 def call(self,path,**params):
  req=Request(self.url+path,data=urlencode(params).encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/x-www-form-urlencoded'})
  try:
   with urlopen(req,timeout=20) as r:j=json.load(r)
  except Exception:raise DomainError('Technitium request failed; check access and connectivity') from None
  if j.get('status')!='ok':raise DomainError('Technitium rejected this operation; check zone permissions')
  return j.get('response',{})
 def zones(self):return self.call('/api/zones/list').get('zones',[])
 def get(self,zone,hostname):return [r for r in self.call('/api/zones/records/get',zone=zone,domain=hostname,listZone='false').get('records',[]) if r.get('name','').lower().rstrip('.')==hostname and r.get('type') not in {'RRSIG','NSEC','NSEC3'}]
 def add(self,r):self.call('/api/zones/records/add',zone=r['zone'],domain=r['hostname'],type='A',ipAddress=self.proxy_address,ttl=60,overwrite='false',comments=MANAGER_LABEL+' '+r['id'])
 def remove(self,r):self.call('/api/zones/records/delete',zone=r['zone'],domain=r['hostname'],type='A',ipAddress=self.proxy_address)

class Caddy:
 def __init__(self,container='caddy'):self.container=container
 def run(self,args,text=None):
  p=subprocess.run(['docker','exec','-i',self.container,'caddy']+args,input=text,capture_output=True,text=True,timeout=45)
  if p.returncode:raise DomainError('Caddy rejected the candidate configuration; previous routes retained')
  return p.stdout
 def adapt(self,text,validate=False):return json.loads(self.run(['adapt','--config','-','--adapter','caddyfile']+(['--validate'] if validate else []),text))
 def validate(self,text):self.adapt(text,True)
 def reload(self,text):self.run(['reload','--config','-','--adapter','caddyfile'],text)
 def export(self):
  p=subprocess.run(['docker','exec',self.container,'wget','-qO-','http://127.0.0.1:2019/config/'],capture_output=True,text=True,timeout=15)
  if p.returncode:raise DomainError('Caddy admin endpoint unavailable')
  return json.loads(p.stdout)
 def assert_sync(self,text):
  if self.adapt(text)!=self.export():raise DomainError('Caddy runtime differs from its file; reconcile before editing')
 def hosts(self,text):
  result=set()
  def walk(v):
   if isinstance(v,dict):
    result.update(v.get('host',[]) if isinstance(v.get('host'),list) else [])
    for child in v.values():walk(child)
   elif isinstance(v,list):
    for child in v:walk(child)
  walk(self.adapt(text));return result

class Engine:
 def __init__(self,root,caddyfile,dns,caddy):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700);self.file=Path(caddyfile);self.dns=dns;self.caddy=caddy;self.state=self.root/'routes.json';self.pending=self.root/'pending.json'
  if not self.state.exists():atomic(self.state,{'routes':[]})
 def routes(self):return json.loads(self.state.read_text())['routes']
 def revision(self):return hashlib.sha256(self.file.read_bytes()+self.state.read_bytes()).hexdigest()
 def owned(self,records,r):return len(records)==1 and records[0].get('type')=='A' and records[0].get('rData',{}).get('ipAddress')==getattr(self.dns,'proxy_address',PROXY_ADDRESS) and records[0].get('comments')==MANAGER_LABEL+' '+r['id'] and records[0].get('ttl')==60 and not records[0].get('disabled',False)
 def check_owned(self,r):
  records=self.dns.get(r['zone'],r['hostname'])
  if not self.owned(records,r):raise DomainError('DNS was changed outside this card; no records were overwritten')
 def preview(self,kind,body,revision):
  if revision!=self.revision():raise DomainError('Configuration changed. Refresh and review again.')
  routes=self.routes();old=None
  if kind not in {'create','update','remove'}:raise DomainError('Invalid operation')
  if kind!='create':
   old=next((r for r in routes if r['id']==body.get('id')),None)
   if not old:raise DomainError('Only domains created by this card can be changed')
   self.check_owned(old)
  if kind=='remove':return old,[r for r in routes if r['id']!=old['id']],old
  r=validate_route(body,self.dns.zones());r['id']=old['id'] if old else uuid.uuid4().hex
  if old and r['hostname']!=old['hostname']:raise DomainError('Create a new domain instead of renaming an existing one')
  if not old:
   if len(routes)>=100:raise DomainError('Managed route limit reached')
   if r['hostname'] in self.caddy.hosts(self.file.read_text()):raise DomainError('This hostname already has a Caddy route')
   if self.dns.get(r['zone'],r['hostname']):raise DomainError('This hostname already has DNS records')
  return r,[x for x in routes if not old or x['id']!=old['id']]+[r],old
 def clear_pending(self):
  self.pending.unlink(missing_ok=True);fd=os.open(str(self.root),os.O_RDONLY)
  try:os.fsync(fd)
  finally:os.close(fd)
 def rollback(self,j):
  text=self.file.read_text()
  if text not in {j['before'],j['candidate']}:raise DomainError('Manual config change detected; recovery needs review')
  dns_error=None
  try:
   if j['kind']=='create':
    records=self.dns.get(j['route']['zone'],j['route']['hostname'])
    if records:
     if not self.owned(records,j['route']):raise DomainError('External DNS edit prevents automatic recovery')
     self.dns.remove(j['route'])
   elif j['kind']=='remove':
    records=self.dns.get(j['route']['zone'],j['route']['hostname'])
    if not records:self.dns.add(j['route'])
    elif not self.owned(records,j['route']):raise DomainError('External DNS edit prevents automatic recovery')
  except Exception as exc:dns_error=exc
  # Restore the previous proxy even when DNS recovery is temporarily unavailable.
  write_in_place(self.file,j['before']);self.caddy.reload(j['before']);atomic(self.state,{'routes':j['old_routes']})
  if dns_error:raise DomainError('DNS recovery needs review; previous Caddy configuration restored')
  self.clear_pending()
 def recover(self):
  if self.pending.exists():
   with open(self.root/'lock','a') as lock:fcntl.flock(lock,fcntl.LOCK_EX);self.rollback(json.loads(self.pending.read_text()))
 def apply(self,kind,body,revision):
  with open(self.root/'lock','a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if self.pending.exists():raise DomainError('An incomplete operation needs recovery before editing')
   route,routes,old=self.preview(kind,body,revision);before=self.file.read_text();old_routes=self.routes()
   if BEGIN in before and render_config(before,old_routes)!=before:raise DomainError('Managed routes changed outside this card')
   if hasattr(self.caddy,'assert_sync'):self.caddy.assert_sync(before)
   candidate=render_config(before,routes);self.caddy.validate(candidate)
   backup=self.root/'backups'/time.strftime('%Y%m%d-%H%M%S')/uuid.uuid4().hex;backup.mkdir(parents=True,mode=0o700)
   for name,text in [('Caddyfile',before),('active.json',json.dumps(self.caddy.export())),('dns.json',json.dumps(self.dns.get(route['zone'],route['hostname'])))]:
    p=backup/name;p.write_text(text);p.chmod(0o600)
   j={'kind':kind,'route':route,'old_routes':old_routes,'before':before,'candidate':candidate};atomic(self.pending,j)
   try:
    if kind=='create':self.dns.add(route);self.check_owned(route)
    write_in_place(self.file,candidate);self.caddy.reload(candidate)
    if hasattr(self.caddy,'assert_sync'):self.caddy.assert_sync(candidate)
    if kind=='remove':
     self.check_owned(route);self.dns.remove(route)
     if self.dns.get(route['zone'],route['hostname']):raise DomainError('DNS removal could not be verified')
    atomic(self.state,{'routes':routes});self.clear_pending();atomic(backup/'result.json',{'status':'success','operation':kind,'hostname':route['hostname'],'at':time.time()});return route
   except Exception as exc:
    try:self.rollback(j)
    except Exception:raise DomainError('Partial change could not be recovered automatically. Editing is locked; private recovery journal retained.') from None
    atomic(backup/'result.json',{'status':'rolled_back','operation':kind,'at':time.time()})
    raise DomainError(str(exc) if isinstance(exc,DomainError) else 'Change failed and was rolled back') from None
