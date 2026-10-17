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
