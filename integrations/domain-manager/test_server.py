import unittest,tempfile,pathlib,threading,http.client,json,time
from server import App,Server,hash_password
class FakeEngine:
 def zones(self):return []
 def routes(self):return []
 def revision(self):return 'revision'
class ServerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=App({'proxy_token':'private-proxy-key','password':hash_password('short-test-pass')},None);self.server=Server(('127.0.0.1',0),self.app);threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def request(self,path,body=None,**extra):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1]);h={'Host':'example.net','X-Domain-Proxy':'private-proxy-key','Origin':'https://example.net','X-Domain-Action':'1','Content-Type':'application/json',**extra};c.request('POST' if body is not None else 'GET',path,None if body is None else json.dumps(body),h);r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read().decode());c.close();return out
 def test_proxy_token_required(self):self.assertEqual(self.request('/',**{'X-Domain-Proxy':'bad'})[0],403)
 def test_apply_requires_session(self):self.assertEqual(self.request('/api/apply',{})[0],401)
 def test_origin_required(self):self.assertEqual(self.request('/api/login',{'password':'short-test-pass'},Origin='https://evil.example')[0],403)
 def test_password_and_cookie(self):
  status,headers,text=self.request('/api/login',{'password':'short-test-pass'},**{'X-Forwarded-Proto':'https'});self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('Secure',headers['Set-Cookie']);self.assertNotIn('short-test-pass',text)
 def test_rate_limit(self):
  statuses=[self.request('/api/login',{'password':'wrong'})[0] for _ in range(7)];self.assertEqual(statuses[-1],429)
 def test_bad_password_never_authenticates(self):self.assertEqual(self.request('/api/login',{'password':'wrong'})[0],401)
 def test_expired_session_cannot_apply(self):
  status,headers,_=self.request('/api/login',{'password':'short-test-pass'});cookie=headers['Set-Cookie'].split(';')[0];key=cookie.split('=',1)[1];self.app.sessions[key]=time.time()-1
  self.assertEqual(self.request('/api/apply',{},Cookie=cookie)[0],401)
if __name__=='__main__':unittest.main()
