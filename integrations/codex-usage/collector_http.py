"""Vendored read-only HTTP boundary for standalone Homarr metadata collectors."""
import hmac,json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

def make_server(read,bind,port,token,allowed_clients):
 if not isinstance(token,str) or len(token)<24 or token.startswith('<'):raise ValueError('Set a random COLLECTOR_TOKEN of at least24 characters')
 peers=set(allowed_clients)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,status,value):
   body=json.dumps(value).encode();self.send_response(status)
   for key,v in {'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Length':str(len(body))}.items():self.send_header(key,v)
   self.end_headers();self.wfile.write(body)
  def do_GET(self):
   if self.client_address[0] not in peers:return self.reply(403,{'error':'Client not allowed'})
   if not hmac.compare_digest(self.headers.get('Authorization','').encode(),('Bearer '+token).encode()):return self.reply(401,{'error':'Authentication required'})
   try:
    value=read(self.path)
    if len(json.dumps(value).encode())>2097152:raise ValueError('Response too large')
    self.reply(200,value)
   except LookupError:self.reply(404,{'error':'Not found'})
   except Exception:self.reply(503,{'error':'Collector unavailable'})
  def do_POST(self):self.reply(405,{'error':'Read only'})
  do_PUT=do_POST;do_PATCH=do_POST;do_DELETE=do_POST
 return ThreadingHTTPServer((bind,int(port)),Handler)

def serve(read,default_port=18083):
 token=os.environ.get('COLLECTOR_TOKEN','');peers={x.strip() for x in os.environ.get('COLLECTOR_ALLOWED_CLIENTS','127.0.0.1').split(',') if x.strip()}
 make_server(read,os.environ.get('COLLECTOR_BIND','127.0.0.1'),int(os.environ.get('COLLECTOR_PORT',str(default_port))),token,peers).serve_forever()
