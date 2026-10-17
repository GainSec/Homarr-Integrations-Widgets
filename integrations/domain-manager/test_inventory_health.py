import unittest,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import inventory_health as subject
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path=='/slow':time.sleep(.2)
  status={'/ok':200,'/bad':502,'/auth':401,'/forbidden':403,'/missing':404,'/redirect':302,'/loop':302}.get(self.path,200)
  self.send_response(status)
  if self.path=='/redirect':self.send_header('Location','/bad')
  if self.path=='/loop':self.send_header('Location','/loop')
  self.end_headers()
  try:self.wfile.write(b'fixture')
  except BrokenPipeError:pass
class HealthTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def test_502_is_unavailable(self):self.assertEqual(subject.probe(self.base+'/bad')['state'],'unavailable')
 def test_redirect_to_502_is_unavailable(self):self.assertEqual(subject.probe(self.base+'/redirect')['state'],'unavailable')
 def test_200_is_responding(self):self.assertEqual(subject.probe(self.base+'/ok')['state'],'responding')
 def test_auth_is_distinct(self):
  for path in ['/auth','/forbidden']:self.assertEqual(subject.probe(self.base+path)['state'],'auth')
 def test_404_is_not_healthy(self):self.assertEqual(subject.probe(self.base+'/missing')['state'],'unavailable')
 def test_redirect_loop_is_unavailable(self):self.assertEqual(subject.probe(self.base+'/loop')['state'],'unavailable')
 def test_slow_service_times_out(self):
  result=subject.probe(self.base+'/slow',timeout=.03);self.assertEqual(result['state'],'unavailable');self.assertEqual(result['reason'],'Timed out')
 def test_bad_scheme_not_fetched(self):self.assertEqual(subject.probe('file:///etc/passwd')['state'],'unavailable')
 def test_configured_frontdoor_preserves_url_host(self):
  r=subject.probe('http://example.example.net:'+str(self.server.server_address[1])+'/bad',frontdoor='127.0.0.1');self.assertEqual(r['status'],502)
 def test_cache_never_accepts_arbitrary_browser_url(self):
  cache=subject.HealthCache([{'url':self.base+'/ok'}],interval=60);cache.refresh();result=cache.snapshot();self.assertEqual(result['services'][self.base+'/ok']['state'],'responding');self.assertIn('checkedAt',result);self.assertFalse(result['stale'])
 def test_explicit_health_path_is_keyed_by_original_service_url(self):
  cache=subject.HealthCache([{'url':self.base+'/missing','checkUrl':self.base+'/ok'}]);cache.refresh();self.assertEqual(cache.snapshot()['services'][self.base+'/missing']['state'],'responding')
class InventoryTests(unittest.TestCase):
 def test_nested_host_upstreams_and_no_secrets(self):
  config={'apps':{'http':{'servers':{'srv0':{'routes':[
   {'match':[{'host':['a.example','alias.example']}],'handle':[{'handler':'subroute','routes':[{'match':[{'path':['/api/*']}],'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'192.0.2.30:8000'}],'headers':{'request':{'set':{'Authorization':['secret-credential']}}}}]}]}]},
   {'match':[{'host':['b.example']}],'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'service:8080'}]}]}
  ]}}}}}
  rows=subject.inventory(config);by={r['hostname']:r for r in rows};self.assertEqual(by['a.example']['upstreams'],['192.0.2.30:8000']);self.assertEqual(by['alias.example']['upstreams'],['192.0.2.30:8000']);self.assertEqual(by['b.example']['upstreams'],['service:8080']);self.assertNotIn('secret-credential',str(rows))
 def test_nested_hosts_do_not_leak_sibling_upstream(self):
  c={'apps':{'http':{'servers':{'srv0':{'routes':[{'handle':[{'handler':'subroute','routes':[{'match':[{'host':['a.example']}],'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'a:80'}]}]},{'match':[{'host':['b.example']}],'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'b:80'}]}]}]}]}]}}}}}
  self.assertEqual({r['hostname']:r['upstreams'] for r in subject.inventory(c)},{'a.example':['a:80'],'b.example':['b:80']})
if __name__=='__main__':unittest.main()

class AdvancedTests(unittest.TestCase):
 def test_site_spans_preserve_comments_quotes_and_placeholders(self):
  text='# pre\n(homarr_tls) {\n tls internal\n}\n# comment\na.example, alias.example {\n header X-Test "quoted } {"\n reverse_proxy backend:80 {\n header_up Host {http.request.host}\n }\n}\nb.example {\n respond `literal } text`\n}\n'
  sites=subject.site_blocks(text);self.assertEqual(len(sites),2);self.assertEqual(sites[0]['hosts'],['a.example','alias.example']);self.assertTrue(sites[0]['text'].startswith('a.example,'));self.assertIn('b.example',sites[1]['text'])
 def test_full_block_rejects_extra_site_and_changed_hosts(self):
  for text in ['a.example {\n respond ok\n}\nb.example {\n respond no\n}','evil.example {\n respond no\n}','{\n admin off\n}']:
   with self.assertRaises(ValueError):subject.validate_site_block(text,['a.example'])
 def test_full_block_allows_headers_for_same_site(self):
  source='a.example {\n header X-Test yes\n reverse_proxy app:80\n}'
  self.assertEqual(subject.validate_site_block(source,['a.example']),source+'\n')

 def test_top_level_import_is_not_in_next_site_editable_span(self):
  text='import /etc/caddy/*.caddy\na.example {\n respond hi\n}\n';sites=subject.site_blocks(text);self.assertEqual(sites[0]['hosts'],['a.example']);self.assertTrue(sites[0]['text'].startswith('a.example'));self.assertEqual(text[:sites[0]['start']],'import /etc/caddy/*.caddy\n')
 def test_reserved_marker_comments_cannot_disable_managed_operations(self):
  for marker in ['# BEGIN HOMARR MANAGED DOMAINS','# END HOMARR MANAGED DOMAINS']:
   with self.assertRaises(ValueError):subject.validate_site_block('a.example {\n '+marker+'\n respond hi\n}', ['a.example'])
