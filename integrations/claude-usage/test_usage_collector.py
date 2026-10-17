import io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from usage_collector import hook,read

class HookTests(unittest.TestCase):
 def feed(self,root,value):
  stream=io.TextIOWrapper(io.BytesIO(json.dumps(value).encode()))
  with patch('sys.stdin',stream),patch('sys.stdout',new_callable=io.StringIO) as out:
   hook(root)
   return out.getvalue()
 def test_hook_persists_only_quota_not_session_or_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   result=self.feed(root,{'session_id':'PRIVATE','rate_limits':{'five_hour':{'used_percentage':23,'resets_at':int(time.time())+3600}},'api_key':'PRIVATE'})
   self.assertIn('23%',result)
   self.assertNotIn('PRIVATE',(root/'claude.json').read_text())
   self.assertEqual((root/'claude.json').stat().st_mode&0o777,0o600)
 def test_missing_hook_limits_preserve_old_capture(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);stamp=int(time.time())-600
   (root/'claude.json').write_text(json.dumps({'capturedAt':stamp,'windows':[{'usedPercent':18,'resetsAt':int(time.time())+1000,'windowMinutes':300}]}))
   self.feed(root,{})
   self.assertEqual(json.loads((root/'claude.json').read_text())['capturedAt'],stamp)
   with patch('usage_collector.ROOT',root):self.assertTrue(read('/usage/status')['claude']['stale'])
 def test_unknown_route_is_not_a_file_reader(self):
  with self.assertRaises(LookupError):read('/../../config.env')
