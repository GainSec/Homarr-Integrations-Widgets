"""Site-scoped WordPress statistics OAuth over Homarr's private Unix socket."""
import hashlib,hmac,html,json,os,re,secrets,socketserver,threading,time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode,urlsplit,parse_qs
from urllib.request import Request,build_opener,HTTPRedirectHandler

SITE='123456789'
CALLBACK='https://example.net/wordpress/oauth/callback'
ROOT=Path(__file__).parent
VISITS='/rest/v1/sites/'+SITE+'/stats/visits?unit=day&quantity=7'

def validate_secrets(config,credentials):
 for key in ('proxy_token','read_token'):
  value=config.get(key)
  if not isinstance(value,str) or len(value)<24 or '<' in value:raise ValueError('Replace credential placeholders with private tokens')
 if config['proxy_token']==config['read_token']:raise ValueError('Use distinct proxy and feed tokens')
 if not str(credentials.get('client_id','')).isdigit() or not credentials.get('client_secret') or '<' in credentials['client_secret']:raise ValueError('Insert WordPress application credentials privately')
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def upstream(path,form=None,token=None):
 # Callers supply only fixed, server-owned paths. Never follow token-bearing redirects.
 if not (path.startswith('/oauth2/') or re.fullmatch(r'/rest/v1/sites/[0-9]+/stats/visits\?unit=day&quantity=7',path)):raise ValueError('Unsupported request')
 data=urlencode(form).encode() if form is not None else None
 headers={'Accept':'application/json','User-Agent':'Homarr-Homarr-Stats/1.0'}
 if token:headers['Authorization']='Bearer '+token
 with build_opener(NoRedirect).open(Request('https://public-api.wordpress.com'+path,data=data,headers=headers),timeout=20) as r:body=r.read(1048577)
 if len(body)>1048576:raise ValueError('Response too large')
 value=json.loads(body)
 if not isinstance(value,dict):raise ValueError('Unexpected response')
 return value

def atomic(path,value):
 path=Path(path);tmp=path.with_name('.'+path.name+'.'+secrets.token_hex(8))
 try:
  fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump(value,f)
  os.replace(tmp,path)
 finally:tmp.unlink(missing_ok=True)

def verify_grant(value,site_id=SITE):
 scopes=value.get('scope')
 scopes=set(re.split(r'[ ,]+',scopes.strip())) if isinstance(scopes,str) else set(scopes) if isinstance(scopes,list) else set()
 if scopes!={'stats'} or str(value.get('blog_id',''))!=str(site_id):raise ValueError('Grant must explicitly allow only stats for the configured site')
 return True

def clean_visits(value):
 fields=value.get('fields');rows=value.get('data')
 if not isinstance(fields,list) or not isinstance(rows,list) or not all(k in fields for k in ('period','views','visitors')):raise ValueError('Unexpected stats format')
 out=[]
 for row in rows[-31:]:
  if not isinstance(row,list) or len(row)<len(fields):continue
  d=dict(zip(fields,row));day=d.get('period');v=d.get('views');u=d.get('visitors')
  if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):continue
  if any(not isinstance(n,int) or isinstance(n,bool) or n<0 for n in (v,u)):continue
  out.append({'date':day,'views':v,'visitors':u})
 return out

class Connection:
 def __init__(self,root,credentials,transport=upstream,site_id=SITE,public_base_url="https://example.net",site_label="blog.example.net"):
  if not str(site_id).isdigit() or not re.fullmatch(r"https://[a-zA-Z0-9.-]+(?::[0-9]+)?",public_base_url):raise ValueError("Set a numeric site_id and HTTPS public_base_url")
  self.site_id=str(site_id);self.public_base_url=public_base_url;self.site_label=site_label;self.callback_url=public_base_url+"/wordpress/oauth/callback";self.visits="/rest/v1/sites/"+self.site_id+"/stats/visits?unit=day&quantity=7"
  self.root=Path(root);self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
  self.credentials=credentials;self.transport=transport;self.pending={};self.lock=threading.RLock();self.cache=None
  setup=self.root/'setup.json'
  if not setup.exists():atomic(setup,{'key':secrets.token_urlsafe(32),'expires':time.time()+86400,'used':False})
  self.setup=json.loads(setup.read_text());self.setup_key=self.setup['key']
 def valid_key(self,key):return isinstance(key,str) and hmac.compare_digest(key,self.setup_key) and not self.setup.get('used') and self.setup['expires']>time.time()
 def begin(self,key):
  with self.lock:
   if not self.valid_key(key):raise ValueError('Setup link is invalid or expired')
   self.pending={k:v for k,v in self.pending.items() if v['expires']>time.time()}
   if len(self.pending)>=16:raise ValueError('Too many connection attempts')
   state=secrets.token_urlsafe(32);cookie=secrets.token_urlsafe(32)
   self.pending[state]={'cookie':hashlib.sha256(cookie.encode()).hexdigest(),'expires':time.time()+600}
   query={'client_id':self.credentials['client_id'],'redirect_uri':self.callback_url,'response_type':'code','scope':'stats','blog':self.site_id,'state':state}
   return 'https://public-api.wordpress.com/oauth2/authorize?'+urlencode(query),cookie
 def take_state(self,state,cookie):
  with self.lock:
   x=self.pending.get(state)
   if not x or x['expires']<=time.time() or not hmac.compare_digest(x['cookie'],hashlib.sha256(cookie.encode()).hexdigest()):raise ValueError('Invalid or expired authorization session')
   del self.pending[state];return True
 def save_token(self,value):
  verify_grant(value,self.site_id)
  token=value.get('access_token')
  if not isinstance(token,str) or not token or len(token)>8192:raise ValueError('Missing token')
  safe={'access_token':token,'scope':'stats','blog_id':self.site_id,'verified_at':int(time.time())}
  if isinstance(value.get('expires_in'),int):safe['expires_at']=int(time.time())+value['expires_in']
  atomic(self.root/'token.json',safe)
 def callback(self,state,cookie,code,error=None):
  self.take_state(state,cookie)
  if error:raise ValueError('Authorization was declined or WordPress rejected the requested scope')
  if not isinstance(code,str) or not 1<=len(code)<=4096:raise ValueError('Missing authorization code')
  token=self.transport('/oauth2/token',form={'client_id':self.credentials['client_id'],'client_secret':self.credentials['client_secret'],'code':code,'grant_type':'authorization_code','redirect_uri':self.callback_url})
  access=token.get('access_token')
  if not isinstance(access,str) or not access:raise ValueError('WordPress did not issue a token')
  info=self.transport('/oauth2/token-info?'+urlencode({'client_id':self.credentials['client_id'],'token':access}))
  verify_grant(info,self.site_id)
  if token.get('blog_id') is not None and str(token['blog_id'])!=self.site_id:raise ValueError('Wrong site')
  self.save_token({**token,'scope':info['scope'],'blog_id':info['blog_id']})
  self.setup['used']=True;atomic(self.root/'setup.json',self.setup)
  return self.status()
 def status(self):
  try:
   token=json.loads((self.root/'token.json').read_text());verify_grant(token,self.site_id)
   connected=not token.get('expires_at') or token['expires_at']>time.time()
  except (OSError,ValueError):connected=False
  return {'site':self.site_label,'connected':bool(connected),'permission':'stats' if connected else None}
 def stats(self):
  with self.lock:
   if not self.status()['connected']:return {**self.status(),'state':'not_connected','days':[]}
   if self.cache and time.time()-self.cache['capturedAt']<300:return self.cache
   token=json.loads((self.root/'token.json').read_text())['access_token']
   try:
    data=self.transport(self.visits,token=token)
    days=sorted(clean_visits(data),key=lambda d:d['date']);latest=days[-1] if days else None
    summary={**latest,'totalViews':sum(d['views'] for d in days),'maxViews':max(d['views'] for d in days),'days':len(days)} if latest else None
    result={**self.status(),'state':'ready','days':days,'summary':summary,'capturedAt':int(time.time())}
    self.cache=result;return result
   except Exception:return {**self.status(),'state':'unavailable','days':[]}

STYLE='body{background:#081b25;color:#d8eef2;font:14px ui-monospace,monospace;line-height:1.6;margin:0;padding:28px}main{max-width:620px;margin:10vh auto;padding:24px;border:1px solid #285564;border-radius:12px;background:#0c2733}h1{font-size:21px}button,a{color:#7ee7d3}button{font:inherit;border:1px solid #3c9c91;border-radius:6px;padding:10px 15px;background:#123d45;cursor:pointer}small{color:#9db6be}'
def page(title,body):return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+STYLE+'</style><main><h1>'+html.escape(title)+'</h1>'+body+'</main></html>').encode()

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass # OAuth codes, state, setup keys and cookies never enter access logs.
 def reply(self,status,data,headers=None):
  raw=data if isinstance(data,bytes) else json.dumps(data).encode();self.send_response(status)
  base={'Content-Type':'text/html; charset=utf-8' if isinstance(data,bytes) else 'application/json','Cache-Control':'no-store','Pragma':'no-cache','Referrer-Policy':'strict-origin','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://public-api.wordpress.com https://wordpress.com; frame-ancestors 'none'; base-uri 'none'",'Content-Length':str(len(raw))}
  for k,v in {**base,**(headers or {})}.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.dispatch()
 def do_POST(self):self.dispatch()
 def dispatch(self):
  c=self.server.connection
  if self.headers.get('Host')!=urlsplit(c.public_base_url).netloc or not hmac.compare_digest(self.headers.get('X-WordPress-Proxy','').encode(),self.server.proxy_token.encode()):return self.reply(403,{'error':'Forbidden'})
  path=urlsplit(self.path);q=parse_qs(path.query);key=q.get('key',[''])[0]
  if self.command=='GET' and path.path=='/api/status':return self.reply(200,c.status())
  if self.command=='GET' and path.path=='/api/stats':
   if not hmac.compare_digest(self.headers.get('Authorization','').encode(),('Bearer '+self.server.read_token).encode()):return self.reply(401,{'error':'Authentication required'})
   return self.reply(200,c.stats())
  if self.command=='GET' and path.path=='/connect':
   if not c.valid_key(key):return self.reply(403,page('Connection link expired','<p>This connection link is invalid, expired or already used.</p>'))
   return self.reply(200,page('Connect site statistics','<p>Continue to WordPress.com, sign in there, and review the requested access for <strong>the configured site</strong>.</p><p>This connection requests <strong>stats</strong> only. If WordPress asks for editing, publishing or all-site access, cancel rather than approve.</p><form method="post" action="/wordpress/start"><input type="hidden" name="key" value="'+html.escape(key,quote=True)+'"><button type="submit">Continue to WordPress</button></form><p><small>Your WordPress password stays with WordPress. Homarr receives only selected statistics after authorization.</small></p>'))
  if self.command=='POST' and path.path=='/start':
   if self.headers.get('Origin')!=c.public_base_url:return self.reply(403,{'error':'Origin rejected'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=4096:raise ValueError()
    form=parse_qs(self.rfile.read(size).decode());url,cookie=c.begin(form.get('key',[''])[0])
    return self.reply(303,b'',{'Location':url,'Set-Cookie':'__Host-wp_link='+cookie+'; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600'})
   except Exception:return self.reply(400,page('Cannot start connection','<p>The setup link is invalid or expired. No access was granted.</p>'))
  if self.command=='GET' and path.path=='/oauth/callback':
   clear={'Set-Cookie':'__Host-wp_link=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0'}
   try:
    cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));cookie=cookies['__Host-wp_link'].value
    c.callback(q.get('state',[''])[0],cookie,q.get('code',[''])[0],q.get('error',[None])[0])
    return self.reply(200,page('WordPress connected','<p>Verified: statistics access for the configured site. The connection is ready for the dashboard widget.</p><p><a href="/">Return to Homarr</a></p>'),clear)
   except Exception:return self.reply(400,page('Connection not accepted','<p>The authorization session expired, WordPress rejected the request, or the token did not explicitly grant only stats access for the configured site. No new token was saved.</p><p>If you approved broader permissions, disconnect Homarr Stats in WordPress.com → Security → Connected applications.</p>'),clear)
  return self.reply(404,{'error':'Not found'})

class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True

if __name__=='__main__':
 config=json.loads(Path(os.environ.get('WORDPRESS_CONFIG','/etc/homarr-wordpress/config.json')).read_text());credentials=json.loads(Path(config['oauth_file']).read_text())
 validate_secrets(config,credentials)
 sock=Path(config['socket_path']);sock.unlink(missing_ok=True)
 server=Server(str(sock),Handler);server.connection=Connection(config['state_dir'],credentials,site_id=config['site_id'],public_base_url=config['public_base_url'],site_label=config['site_label']);server.proxy_token=config['proxy_token'];server.read_token=config['read_token'];os.chown(sock,0,int(config['socket_gid']));os.chmod(sock,0o660)
 server.serve_forever()
