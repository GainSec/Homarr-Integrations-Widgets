import json,threading,unittest,urllib.request,urllib.error
from collector_http import make_server
class BoundaryTests(unittest.TestCase):
 def setUp(self):
  def read(path):
   if path=='/ok':return {'ok':True}
   if path=='/fail':raise RuntimeError('private details')
   raise LookupError('Not found')
  self.server=make_server(read,'127.0.0.1',0,'t'*32,{'127.0.0.1'})
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join()
 def get(self,path,token='t'*32,method='GET'):
  req=urllib.request.Request('http://127.0.0.1:'+str(self.server.server_port)+path,headers={'Authorization':'Bearer '+token},method=method)
  try:r=urllib.request.urlopen(req,timeout=2)
  except urllib.error.HTTPError as e:r=e
  with r:return r.status,json.load(r)
 def test_authorization_and_read_only_routes(self):
  self.assertEqual(self.get('/ok'),(200,{'ok':True}))
  self.assertEqual(self.get('/ok','wrong')[0],401)
  self.assertEqual(self.get('/unknown')[0],404)
  self.assertEqual(self.get('/ok',method='POST')[0],405)
  status,body=self.get('/fail');self.assertEqual(status,503);self.assertNotIn('private details',str(body))
 def test_exact_peer_allowlist(self):
  other=make_server(lambda _: {},'127.0.0.1',0,'t'*32,{'192.0.2.10'})
  t=threading.Thread(target=other.serve_forever,daemon=True);t.start()
  try:
   with self.assertRaises(urllib.error.HTTPError) as caught:
    urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(other.server_port),headers={'Authorization':'Bearer '+'t'*32}),timeout=2)
   self.assertEqual(caught.exception.code,403);caught.exception.close()
  finally:other.shutdown();other.server_close();t.join()
