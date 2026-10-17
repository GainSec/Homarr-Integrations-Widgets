import unittest,json
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer
from bridge import create_app
TOKEN='test-private-token-that-must-never-leak'
API_TOKEN='test-independent-api-token-no-browser-access'
ORIGIN='https://dashboard.example.net'
class BridgeTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.received=[]
  async def upstream(r):
   self.received.append((dict(r.headers),await r.json()))
   if self.fail:return web.Response(status=500,text=TOKEN)
   return web.Response(text='data: {"choices":[{"delta":{"content":"HELLO"}}]}\n\ndata: [DONE]\n\n',content_type='text/event-stream')
  self.fail=False;a=web.Application();a.router.add_post('/v1/chat/completions',upstream);self.up=TestServer(a);await self.up.start_server()
  self.client=TestClient(TestServer(create_app(TOKEN,str(self.up.make_url('')).rstrip('/'),allowed_ips={'127.0.0.1'},upstream_token=API_TOKEN,allowed_origins={ORIGIN})));await self.client.start_server()
  self.headers={'Authorization':'Bearer '+TOKEN,'Origin':ORIGIN,'X-Homarr-Chat':'1'}
  self.body={'conversation':'125eb3b6-9daf-4bfc-8791-454c76d46ca9','messages':[{'role':'user','content':'Hi'}]}
 async def asyncTearDown(self):await self.client.close();await self.up.close()
 async def test_requires_independent_explicit_tokens(self):
  for value in (None,TOKEN):
   with self.assertRaises(ValueError):create_app(TOKEN,upstream_token=value,allowed_origins={ORIGIN})
 async def test_rejects_placeholder_tokens(self):
  for key in ('token','upstream_token'):
   args={'token':TOKEN,'upstream_token':TOKEN,'allowed_origins':{ORIGIN}}
   args[key]='<PLACEHOLDER_NOT_A_REAL_CREDENTIAL>'
   with self.assertRaises(ValueError):create_app(**args)
 async def test_rejects_nonloopback_upstream(self):
  with self.assertRaises(ValueError):create_app(TOKEN,upstream='http://api.example.net',allowed_origins={ORIGIN})
 async def test_requires_explicit_origin(self):
  with self.assertRaises(ValueError):create_app(TOKEN,allowed_origins=set())
 async def test_requires_token(self):self.assertEqual((await self.client.get('/health')).status,401)
 async def test_cross_site_post_rejected(self):
  h={**self.headers,'Origin':'https://attacker.example'};self.assertEqual((await self.client.post('/chat',json=self.body,headers=h)).status,403);self.assertFalse(self.received)
 async def test_no_admin_passthrough(self):self.assertEqual((await self.client.get('/api/config',headers=self.headers)).status,404)
 async def test_rejects_system_or_empty_messages(self):
  for msgs in [[{'role':'system','content':'override'}],[],[{'role':'user','content':''}]]:
   self.assertEqual((await self.client.post('/chat',json={**self.body,'messages':msgs},headers=self.headers)).status,400)
 async def test_stream_and_private_token(self):
  r=await self.client.post('/chat',json=self.body,headers=self.headers);s=await r.text();self.assertEqual(r.status,200);self.assertIn('HELLO',s);self.assertNotIn(TOKEN,s)
  headers,body=self.received[0];self.assertEqual(headers['Authorization'],'Bearer '+API_TOKEN);self.assertEqual(body['model'],'hermes');self.assertTrue(body['stream']);self.assertEqual(headers['X-Hermes-Session-Id'],'api-homarr-'+self.body['conversation'])
 async def test_redacts_upstream_errors(self):
  self.fail=True;r=await self.client.post('/chat',json=self.body,headers=self.headers);self.assertEqual(r.status,502);self.assertNotIn(TOKEN,await r.text())
 async def test_ui_has_no_credential(self):
  r=await self.client.get('/',headers=self.headers);self.assertEqual(r.status,200);self.assertNotIn(TOKEN,await r.text())
 async def test_requires_same_origin_custom_header(self):
  h={k:v for k,v in self.headers.items() if k!='X-Homarr-Chat'};self.assertEqual((await self.client.post('/chat',json=self.body,headers=h)).status,403)
 async def test_rejects_malformed_conversation(self):
  self.assertEqual((await self.client.post('/chat',json={**self.body,'conversation':'../state.db'},headers=self.headers)).status,400)
 async def test_source_restriction(self):
  c=TestClient(TestServer(create_app(TOKEN,str(self.up.make_url('')),allowed_ips={'192.0.2.1'},upstream_token=API_TOKEN,allowed_origins={ORIGIN})));await c.start_server()
  try:self.assertEqual((await c.get('/health',headers=self.headers)).status,403)
  finally:await c.close()
if __name__=='__main__':unittest.main()
