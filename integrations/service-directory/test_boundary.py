import http.client,threading,unittest
from collector_http import make_server
class BoundaryTests(unittest.TestCase):
 def test_peer_bearer_path_and_methods(self):
  def read(path):
   if path!='/services/status':raise LookupError()
   return {'services':{}}
  server=make_server(read,'127.0.0.1',0,'x'*32,{'127.0.0.1'});t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  try:
   for method,path,token,expected in [('GET','/services/status','',401),('GET','/services/status','bad',401),('GET','/services/status','x'*32,200),('GET','/no','x'*32,404),('POST','/services/status','x'*32,405)]:
    c=http.client.HTTPConnection(*server.server_address);c.request(method,path,headers={'Authorization':'Bearer '+token});r=c.getresponse();r.read();self.assertEqual(r.status,expected);c.close()
  finally:server.shutdown();server.server_close();t.join()
