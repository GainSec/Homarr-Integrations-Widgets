import unittest,tempfile,json,time
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from server import Connection,verify_grant,clean_visits

class WordpressTests(unittest.TestCase):
 def connection(self,d,**kwargs):return Connection(Path(d),{'client_id':'123','client_secret':'SECRET'},**kwargs)
 def test_authorization_requests_only_stats_and_site(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d);url,cookie=c.begin(c.setup_key);q=parse_qs(urlparse(url).query)
   self.assertEqual(q['scope'],['stats']);self.assertEqual(q['blog'],['123456789']);self.assertEqual(q['redirect_uri'],['https://example.net/wordpress/oauth/callback']);self.assertNotIn('SECRET',url)
   self.assertEqual(c.take_state(q['state'][0],cookie),True)
   with self.assertRaises(ValueError):c.take_state(q['state'][0],cookie)
 def test_wrong_cookie_and_expired_state_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d);url,cookie=c.begin(c.setup_key);state=parse_qs(urlparse(url).query)['state'][0]
   with self.assertRaises(ValueError):c.take_state(state,'bad-cookie')
   c.pending[state]['expires']=time.time()-1
   with self.assertRaises(ValueError):c.take_state(state,cookie)
 def test_wrong_setup_key_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d)
   with self.assertRaises(ValueError):c.begin('wrong')
 def test_only_explicit_stats_single_site_grant_accepted(self):
  for bad in [{},{'scope':'global','blog_id':123456789},{'scope':'stats posts','blog_id':123456789},{'scope':'stats','blog_id':99}]:
   with self.assertRaises(ValueError):verify_grant(bad)
  self.assertTrue(verify_grant({'scope':'stats','blog_id':'123456789'}))
 def test_public_status_never_contains_credentials(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d);c.save_token({'access_token':'SECRET','scope':'stats','blog_id':123456789})
   self.assertNotIn('SECRET',json.dumps(c.status()));self.assertEqual((Path(d)/'token.json').stat().st_mode & 0o777,0o600)
 def test_visits_allowlists_fields_and_rejects_bad_counts(self):
  raw={'fields':['period','views','visitors'],'data':[['2026-10-15',10,7],['2026-10-16',-1,True]],'token':'SECRET','private':'SECRET'}
  x=clean_visits(raw);self.assertEqual(x,[{'date':'2026-10-15','views':10,'visitors':7}]);self.assertNotIn('SECRET',json.dumps(x))
 def test_callback_verifies_actual_grant_before_saving_token(self):
  with tempfile.TemporaryDirectory() as d:
   calls=[]
   def transport(path,**kwargs):
    calls.append(path)
    return {'access_token':'SECRET','blog_id':123456789} if path=='/oauth2/token' else {'scope':'global','blog_id':123456789}
   c=self.connection(d,transport=transport);url,cookie=c.begin(c.setup_key);state=parse_qs(urlparse(url).query)['state'][0]
   with self.assertRaises(ValueError):c.callback(state,cookie,'CODE')
   self.assertFalse((Path(d)/'token.json').exists());self.assertFalse(c.status()['connected'])
   self.assertEqual(len(calls),2)
 def test_success_locks_setup_link_and_discards_extra_response_fields(self):
  with tempfile.TemporaryDirectory() as d:
   def transport(path,**kwargs):return {'access_token':'TOKEN','blog_id':123456789,'private':'NOT_FOR_DISK'} if path=='/oauth2/token' else {'scope':'stats','blog_id':123456789}
   c=self.connection(d,transport=transport);url,cookie=c.begin(c.setup_key);state=parse_qs(urlparse(url).query)['state'][0]
   result=c.callback(state,cookie,'CODE');self.assertTrue(result['connected']);self.assertNotIn('TOKEN',json.dumps(result));self.assertNotIn('NOT_FOR_DISK',(Path(d)/'token.json').read_text())
   with self.assertRaises(ValueError):c.begin(c.setup_key)
   reloaded=self.connection(d,transport=transport)
   self.assertFalse(reloaded.valid_key(c.setup_key));self.assertTrue(reloaded.status()['connected'])
 def test_invalid_state_never_contacts_wordpress(self):
  with tempfile.TemporaryDirectory() as d:
   def transport(*args,**kwargs):self.fail('Must reject before any remote request')
   c=self.connection(d,transport=transport)
   with self.assertRaises(ValueError):c.callback('wrong','wrong','CODE')
 def test_stats_transport_only_reads_fixed_site_path(self):
  with tempfile.TemporaryDirectory() as d:
   paths=[]
   def transport(path,**kwargs):
    paths.append(path);return {'fields':['period','views','visitors'],'data':[['2026-10-16',10,7]],'secret':'SECRET'}
   c=self.connection(d,transport=transport);self.assertEqual(c.stats()['state'],'not_connected');self.assertEqual(paths,[])
   c.save_token({'access_token':'TOKEN','scope':'stats','blog_id':123456789});x=c.stats();self.assertEqual(x['days'][0]['views'],10);self.assertNotIn('SECRET',json.dumps(x));self.assertNotIn('TOKEN',json.dumps(x));c.stats();self.assertEqual(len(paths),1);self.assertEqual(paths[0],'/rest/v1/sites/123456789/stats/visits?unit=day&quantity=7')
 def test_expired_pending_states_do_not_block_setup(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d)
   for _ in range(16):c.begin(c.setup_key)
   for state in c.pending.values():state['expires']=time.time()-1
   url,cookie=c.begin(c.setup_key);self.assertIn('scope=stats',url);self.assertEqual(len(c.pending),1)
 def test_browser_form_headers_preserve_origin_without_leaking_url(self):
  import threading,http.client
  from http.server import ThreadingHTTPServer
  from server import Handler
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d);srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);srv.connection=c;srv.proxy_token='PROXY'
   thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
   try:
    h=http.client.HTTPConnection(*srv.server_address);h.request('GET','/connect?key='+c.setup_key,headers={'Host':'example.net','X-WordPress-Proxy':'PROXY'});r=h.getresponse();r.read()
    self.assertEqual(r.getheader('Referrer-Policy'),'strict-origin')
    self.assertIn("form-action 'self' https://public-api.wordpress.com https://wordpress.com;",r.getheader('Content-Security-Policy'))
    h.request('POST','/start',body='key='+c.setup_key,headers={'Host':'example.net','X-WordPress-Proxy':'PROXY','Origin':'null'});r=h.getresponse();r.read();self.assertEqual(r.status,403)
    h.close()
   finally:srv.shutdown();srv.server_close();thread.join()

 def test_stats_api_requires_distinct_private_widget_credential(self):
  import threading,http.client
  from http.server import ThreadingHTTPServer
  from server import Handler
  with tempfile.TemporaryDirectory() as d:
   c=self.connection(d);srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);srv.connection=c;srv.proxy_token='PROXY';srv.read_token='READ'
   thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
   try:
    for credential,expected in [('',401),('Bearer wrong',401),('Bearer READ',200)]:
     h=http.client.HTTPConnection(*srv.server_address);h.request('GET','/api/stats',headers={'Host':'example.net','X-WordPress-Proxy':'PROXY','Authorization':credential});r=h.getresponse();body=r.read();self.assertEqual(r.status,expected);self.assertNotIn(b'READ',body);h.close()
   finally:srv.shutdown();srv.server_close();thread.join()
 def test_summary_reports_latest_day_and_sums_only_views(self):
  with tempfile.TemporaryDirectory() as d:
   def transport(path,**kwargs):return {'fields':['period','views','visitors'],'data':[['2026-10-15',10,7],['2026-10-16',3,2]]}
   c=self.connection(d,transport=transport);c.save_token({'access_token':'TOKEN','scope':'stats','blog_id':123456789});x=c.stats()
   self.assertEqual(x['summary'],{'date':'2026-10-16','views':3,'visitors':2,'totalViews':13,'maxViews':10,'days':2})
