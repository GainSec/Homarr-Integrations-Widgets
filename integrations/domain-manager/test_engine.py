import unittest,tempfile,pathlib,json
from engine import Engine,DomainError,render_config,validate_route
class FakeDNS:
 def __init__(self):self.records={};self.fail_add=False;self.fail_remove=False
 def zones(self):return [{'name':'example.net','type':'Primary','disabled':False}]
 def get(self,zone,domain):return self.records.get(domain,[])
 def add(self,route):
  if self.fail_add:raise DomainError('DNS rejected change')
  self.records[route['hostname']]=[{'name':route['hostname'],'type':'A','ttl':60,'rData':{'ipAddress':'192.0.2.10'},'comments':'Homarr Domains '+route['id']}]
 def remove(self,route):
  if self.fail_remove:raise DomainError('DNS delete rejected')
  self.records.pop(route['hostname'],None)
class FakeCaddy:
 def __init__(self,text):self.active=text;self.fail=False
 def validate(self,text):
  if 'INVALID' in text:raise DomainError('Invalid config')
 def reload(self,text):
  if self.fail:self.fail=False;raise DomainError('Reload rejected')
  self.active=text
 def export(self):return {'fixture':self.active}
 def hosts(self,text):return {'example.net','dns.example.net','*.example.net'}
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.file=self.root/'Caddyfile';self.base='(homarr_tls) {\n tls internal\n}\nexample.net {\n respond "ok"\n}\n';self.file.write_text(self.base);self.dns=FakeDNS();self.caddy=FakeCaddy(self.base);self.engine=Engine(self.root,self.file,self.dns,self.caddy)
  self.input={'zone':'example.net','label':'test','upstream':'http://192.0.2.20:8088','tls':'existing','skipVerify':False}
 def tearDown(self):self.tmp.cleanup()
 def apply(self,kind='create',**extra):return self.engine.apply(kind,self.input,self.engine.revision(),**extra)
 def test_rejects_injection_and_zone_escape(self):
  for key,value in [('label','x\n} admin off'),('zone','evil.com'),('upstream','http://user:pass@host'),('upstream','http://127.0.0.1:2019'),('upstream','http://host/path'),('label','@')]:
   with self.subTest(key=key,value=value),self.assertRaises(DomainError):validate_route({**self.input,key:value},self.dns.zones())
 def test_create_preserves_unrelated_file_and_dns_points_to_proxy(self):
  self.apply();self.assertTrue(self.file.read_text().startswith(self.base));self.assertEqual(self.dns.get('', 'test.example.net')[0]['rData']['ipAddress'],'192.0.2.10');self.assertEqual(self.caddy.active,self.file.read_text());self.assertEqual(len(self.engine.routes()),1)
 def test_remove_only_owned_records(self):
  r=self.apply();self.engine.apply('remove',{'id':r['id']},self.engine.revision());self.assertFalse(self.dns.records);self.assertEqual(self.file.read_text(),self.base)
 def test_existing_dns_never_overwritten(self):
  self.dns.records['test.example.net']=[{'type':'A','name':'test.example.net','rData':{'ipAddress':'192.0.2.99'}}]
  with self.assertRaises(DomainError):self.apply()
  self.assertEqual(self.file.read_text(),self.base)
 def test_caddy_failure_compensates_created_dns(self):
  self.caddy.fail=True
  with self.assertRaises(DomainError):self.apply()
  self.assertFalse(self.dns.records);self.assertEqual(self.file.read_text(),self.base);self.assertFalse(self.engine.routes())
 def test_dns_failure_never_changes_caddy(self):
  self.dns.fail_add=True
  with self.assertRaises(DomainError):self.apply()
  self.assertEqual(self.caddy.active,self.base);self.assertEqual(self.file.read_text(),self.base)
 def test_delete_failure_restores_route(self):
  r=self.apply();before=self.file.read_text();self.dns.fail_remove=True
  with self.assertRaises(DomainError):self.engine.apply('remove',{'id':r['id']},self.engine.revision())
  self.assertEqual(self.caddy.active,before);self.assertEqual(self.file.read_text(),before);self.assertEqual(len(self.engine.routes()),1)
 def test_foreign_edit_protected(self):
  r=self.apply();self.dns.records[r['hostname']][0]['rData']['ipAddress']='192.0.2.99'
  with self.assertRaises(DomainError):self.engine.apply('remove',{'id':r['id']},self.engine.revision())
 def test_stale_revision_rejected(self):
  rev=self.engine.revision();self.file.write_text(self.base+'# manual edit\n')
  with self.assertRaises(DomainError):self.engine.apply('create',self.input,rev)
 def test_update_changes_only_target(self):
  r=self.apply();self.engine.apply('update',{**self.input,'id':r['id'],'upstream':'https://192.0.2.20:8443'},self.engine.revision());self.assertIn('https://192.0.2.20:8443',self.file.read_text());self.assertEqual(len(self.dns.records),1)
 def test_bind_mount_inode_preserved(self):
  ino=self.file.stat().st_ino;self.apply();self.assertEqual(self.file.stat().st_ino,ino)
 def test_pending_recovery_restores_caddy_when_dns_is_unavailable(self):
  r=self.apply();before=self.base;candidate=self.file.read_text()
  j={'kind':'create','route':r,'old_routes':[],'before':before,'candidate':candidate}
  self.dns.fail_remove=True
  with self.assertRaises(DomainError):self.engine.rollback(j)
  self.assertEqual(self.caddy.active,before);self.assertEqual(self.file.read_text(),before)
 def test_interrupted_transaction_recovers_on_restart(self):
  r=self.apply();candidate=self.file.read_text();self.engine.pending.write_text(json.dumps({'kind':'create','route':r,'old_routes':[],'before':self.base,'candidate':candidate}))
  e=Engine(self.root,self.file,self.dns,self.caddy);e.recover();self.assertEqual(self.file.read_text(),self.base);self.assertFalse(e.routes());self.assertFalse(self.dns.records);self.assertFalse(e.pending.exists())
 def test_external_ttl_change_is_not_removed(self):
  r=self.apply();self.dns.records[r['hostname']][0]['ttl']=300
  with self.assertRaises(DomainError):self.engine.apply('remove',{'id':r['id']},self.engine.revision())
if __name__=='__main__':unittest.main()
