import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from usage_collector import codex_read,collect

class CollectorTests(unittest.TestCase):
 def test_coalesced_notification_and_response_are_read_without_timeout(self):
  with tempfile.TemporaryDirectory() as d:
   binary=Path(d)/'fake-codex'
   binary.write_text('''#!/usr/bin/env python3
import sys,json,time
sys.stdin.readline();print(json.dumps({'id':0,'result':{}}),flush=True)
sys.stdin.readline();sys.stdin.readline()
response={'id':1,'result':{'rateLimits':{'primary':{'usedPercent':10,'windowDurationMins':300,'resetsAt':int(time.time())+1000}}}}
sys.stdout.write(json.dumps({'method':'notice','params':{}})+'\\n'+json.dumps(response)+'\\n');sys.stdout.flush();time.sleep(35)
''');binary.chmod(0o700)
   started=time.monotonic();x=codex_read(str(binary));self.assertEqual(x['windows'][0]['usedPercent'],10);self.assertLess(time.monotonic()-started,4)
 def test_failed_poll_keeps_capture_time_and_cannot_leak_error(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);stamp=int(time.time())-600
   (root/'snapshot.json').write_text(json.dumps({'codex':{'capturedAt':stamp,'windows':[{'usedPercent':15,'resetsAt':int(time.time())+1000,'windowMinutes':300}]}}))
   with patch('usage_collector.codex_read',side_effect=RuntimeError('SECRET')):x=collect(root)
   self.assertEqual(x['codex']['capturedAt'],stamp);self.assertTrue(x['codex']['stale']);self.assertNotIn('SECRET',json.dumps(x))
