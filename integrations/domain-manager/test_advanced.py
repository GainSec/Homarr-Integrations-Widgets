import unittest,tempfile,pathlib,json
from advanced import Advanced
from engine import Engine,DomainError,render_config
from test_engine import FakeDNS,FakeCaddy
from inventory_health import site_blocks
class Caddy(FakeCaddy):
 def assert_sync(self,text):
  if self.active!=text:raise DomainError('Drift')
class AdvancedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.file=self.root/'Caddyfile';self.original='a.example {\n respond "hi"\n}\nb.example {\n reverse_proxy other:80\n}\n';self.file.write_text(self.original);self.caddy=Caddy(self.original);self.dns=FakeDNS();self.e=Engine(self.root/'state',self.file,self.dns,self.caddy);self.a=Advanced(self.e);self.id=site_blocks(self.original)[0]['id']
 def tearDown(self):self.tmp.cleanup()
 def test_advanced_changes_one_block_and_no_dns(self):
  ino=self.file.stat().st_ino;self.a.apply(self.id,'a.example {\n header X-Probe yes\n respond hi\n}',self.e.revision());self.assertIn('header X-Probe yes',self.file.read_text());self.assertTrue(self.file.read_text().endswith('b.example {\n reverse_proxy other:80\n}\n'));self.assertEqual(self.file.stat().st_ino,ino);self.assertEqual(self.dns.records,{})
 def test_advanced_failure_rolls_back(self):
  self.caddy.fail=True
  with self.assertRaises(DomainError):self.a.apply(self.id,'a.example {\n respond changed\n}',self.e.revision())
  self.assertEqual(self.file.read_text(),self.original);self.assertFalse(self.e.pending.exists())
 def test_advanced_stale_revision_rejected(self):
  with self.assertRaises(DomainError):self.a.apply(self.id,'a.example {\n respond changed\n}','stale')
 def test_existing_managed_raw_block_survives_other_render(self):
  r={'id':'id','hostname':'a.example','siteBlock':'a.example {\n header X-Probe yes\n respond hi\n}\n'};text=render_config(self.original,[r]);self.assertIn('header X-Probe yes',text)
 def test_site_and_advanced_endpoints_locked(self):
  from server import App,hash_password
  app=App({'proxy_token':'test','password':hash_password('password')},self.e);h={'Host':'example.net','X-Domain-Proxy':'test','Origin':'https://example.net','X-Domain-Action':'1'}
  for path in ['/api/site','/api/advanced-preview','/api/advanced-apply']:self.assertEqual(app.dispatch('POST',path,h,{'id':self.id})[0],401)

 def test_public_state_never_exposes_managed_raw_site(self):
  from server import App,hash_password
  self.e.state.write_text(json.dumps({'routes':[{'id':'owned','hostname':'a.example','siteBlock':'a.example { header X-Secret very-private-value }'}]}))
  app=App({'proxy_token':'test','password':hash_password('password')},self.e);h={'Host':'example.net','X-Domain-Proxy':'test'}
  code,_,body=app.dispatch('GET','/api/state',h,{})
  self.assertEqual(code,200);self.assertNotIn('very-private-value',json.dumps(body));self.assertNotIn('siteBlock',body['routes'][0])
