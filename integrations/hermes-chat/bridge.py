"""Narrow Homarr chat bridge. Credentials never enter the served client."""
import asyncio,hmac,json,os,uuid
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import ClientSession,ClientTimeout,web
ROOT=Path(__file__).parent
HTTP=web.AppKey('http',ClientSession)


def validate_body(body):
 if not isinstance(body,dict):raise ValueError()
 conversation=str(uuid.UUID(body.get('conversation','')))
 messages=body.get('messages')
 if not isinstance(messages,list) or not 1<=len(messages)<=40:raise ValueError()
 clean=[]
 for m in messages:
  if not isinstance(m,dict) or m.get('role') not in {'user','assistant'}:raise ValueError()
  text=m.get('content')
  if not isinstance(text,str) or not text.strip() or len(text)>32000:raise ValueError()
  clean.append({'role':m['role'],'content':text})
 if clean[-1]['role']!='user' or sum(len(m['content']) for m in clean)>96000:raise ValueError()
 return conversation,clean

def create_app(token,upstream='http://127.0.0.1:18642',allowed_ips=None,upstream_token=None,allowed_origins=None):
 if any(not isinstance(value,str) or len(value)<24 or value.startswith('<') for value in (token,upstream_token)):raise ValueError('Independent private API and bridge tokens required')
 if hmac.compare_digest(token,upstream_token):raise ValueError('Bridge and API tokens must be different')
 allowed_ips=set(allowed_ips or {'127.0.0.1','::1'})
 origins=set(allowed_origins or ())
 if not origins:raise ValueError('Configure exact dashboard origins')
 for origin in origins:
  parsed=urlsplit(origin)
  if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or '*' in origin:raise ValueError('Origin must be an exact HTTP(S) origin, without a path')
 target=urlsplit(upstream)
 if target.scheme!='http' or target.hostname not in {'127.0.0.1','::1'} or target.username or target.password or target.path or target.query or target.fragment:raise ValueError('Hermes API must be a loopback HTTP origin')
 active=set()
 @web.middleware
 async def guard(request,handler):
  if not hmac.compare_digest(request.headers.get('Authorization','').encode(),('Bearer '+token).encode()):return web.json_response({'error':'Unauthorized'},status=401)
  peer=request.transport.get_extra_info('peername') if request.transport else None
  if not peer or peer[0] not in allowed_ips:return web.json_response({'error':'Forbidden'},status=403)
  if request.method=='POST' and (request.headers.get('Origin') not in origins or request.headers.get('X-Homarr-Chat')!='1'):return web.json_response({'error':'Forbidden'},status=403)
  result=await handler(request)
  result.headers['Cache-Control']='no-store'
  result.headers['X-Content-Type-Options']='nosniff'
  result.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'"
  return result
 app=web.Application(middlewares=[guard],client_max_size=131072)
 async def lifecycle(app):
  app[HTTP]=ClientSession(timeout=ClientTimeout(total=None,connect=10,sock_read=180))
  yield
  await app[HTTP].close()
 app.cleanup_ctx.append(lifecycle)
 async def health(r):
  try:
   async with app[HTTP].get(upstream+'/v1/models',headers={'Authorization':'Bearer '+upstream_token}) as resp:
    if resp.status!=200:raise RuntimeError()
   return web.json_response({'available':True,'instance':os.environ.get('HOMARR_CHAT_INSTANCE','Hermes'),'profile':'default'})
  except Exception:return web.json_response({'available':False},status=503)
 async def asset(r):
  name=r.match_info.get('file','index.html')
  return web.FileResponse(ROOT/name)
 async def chat(r):
  try:conversation,messages=validate_body(await r.json())
  except (ValueError,TypeError,AttributeError):return web.json_response({'error':'Invalid conversation or messages'},status=400)
  if conversation in active or len(active)>=3:return web.json_response({'error':'A reply is already running. Try again shortly.'},status=429)
  active.add(conversation)
  response=None
  try:
   async with app[HTTP].post(upstream+'/v1/chat/completions',json={'model':'hermes','stream':True,'messages':messages},headers={'Authorization':'Bearer '+upstream_token,'X-Hermes-Session-Key':'homarr:'+conversation,'X-Hermes-Session-Id':'api-homarr-'+conversation}) as resp:
    if resp.status!=200:return web.json_response({'error':'Hermes could not start a reply. Try again.'},status=502)
    response=web.StreamResponse(headers={'X-Hermes-Session-Id':resp.headers.get('X-Hermes-Session-Id','api-homarr-'+conversation),'Content-Type':'text/event-stream','Cache-Control':'no-store','X-Accel-Buffering':'no'})
    await response.prepare(r)
    async for chunk in resp.content.iter_any():await response.write(chunk)
    await response.write_eof()
    return response
  except (ConnectionResetError,asyncio.CancelledError):raise
  except Exception:
   if response is not None:
    try:await response.write(b'data: {"error":{"message":"Hermes connection interrupted. Please retry."}}\n\ndata: [DONE]\n\n');await response.write_eof()
    except ConnectionResetError:pass
    return response
   return web.json_response({'error':'Hermes is unavailable. Try again shortly.'},status=502)
  finally:active.discard(conversation)
 app.router.add_get('/',asset)
 for name in ['chat.js','chat.css']:app.router.add_get('/{file:'+name.replace('.','\\.')+'}',asset)
 app.router.add_get('/health',health);app.router.add_post('/chat',chat)
 return app
if __name__=='__main__':
 web.run_app(create_app(os.environ['HOMARR_CHAT_TOKEN'],upstream='http://127.0.0.1:'+os.environ.get('HERMES_API_PORT','18642'),upstream_token=os.environ['API_SERVER_KEY'],allowed_ips={x.strip() for x in os.environ.get('HOMARR_CHAT_ALLOWED_IPS','127.0.0.1,::1').split(',') if x.strip()},allowed_origins={x.strip() for x in os.environ.get('HOMARR_CHAT_ORIGINS','').split(',') if x.strip()}),host=os.environ.get('HOMARR_CHAT_HOST','127.0.0.1'),port=int(os.environ.get('HOMARR_CHAT_PORT','18084')),access_log=None,handler_cancellation=True)
