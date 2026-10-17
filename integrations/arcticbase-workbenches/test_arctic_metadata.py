import json,unittest
from arctic_metadata import ArcticClient,workbench_metadata,object_metadata,validate_slug
from collector import make_reader
class MetadataTests(unittest.TestCase):
 def test_workbenches_allowlist(self):
  d=workbench_metadata({'slug':'demo','title':'Example','custom_fields':{'secret':'DO_NOT_EXPORT'},'content':'DO_NOT_EXPORT'})
  self.assertEqual(d['slug'],'demo');self.assertNotIn('DO_NOT_EXPORT',json.dumps(d))
 def test_objects_allowlist(self):
  d=object_metadata({'id':'example','kind':'html','title':'Example','content':'DO_NOT_EXPORT','responses':{'secret':'DO_NOT_EXPORT'},'archived':True})
  self.assertTrue(d['archived']);self.assertNotIn('DO_NOT_EXPORT',json.dumps(d))
 def test_slug_must_be_known(self):
  self.assertEqual(validate_slug('example',{'example'}),'example')
  for slug in ('missing','../example','example/objects'):
   with self.assertRaises(ValueError):validate_slug(slug,{'example'})
 def test_origin_rejects_credentials(self):
  with self.assertRaises(ValueError):ArcticClient('https://user:secret@app.example.net')
 def test_routes_do_not_accept_arbitrary_paths(self):
  read=make_reader(None)
  for path in ('/','/api/workbenches','/arctic/workbenches/../objects','/arctic/workbenches?url=http://example.net'):
   with self.assertRaises(LookupError):read(path)
if __name__=='__main__':unittest.main()
