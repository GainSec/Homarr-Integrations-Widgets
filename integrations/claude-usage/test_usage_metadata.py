import unittest,time,json,tempfile
from pathlib import Path
from usage_metadata import normalize_codex,normalize_claude,snapshot,ingest

class UsageTests(unittest.TestCase):
 def test_codex_only_allows_quota_fields(self):
  x=normalize_codex({'rateLimits':{'primary':{'usedPercent':21,'windowDurationMins':10080,'resetsAt':20000},'secondary':None,'credits':{'balance':'SECRET'}},'accountId':'SECRET','token':'SECRET'},10000)
  self.assertEqual(x['windows'][0],{'label':'Weekly','usedPercent':21.0,'resetsAt':20000,'windowMinutes':10080})
  self.assertNotIn('SECRET',json.dumps(x))
 def test_claude_filters_and_names_real_windows(self):
  x=normalize_claude({'rate_limits':{'five_hour':{'used_percentage':42,'resets_at':20000},'seven_day':{'used_percentage':12,'resets_at':90000}},'session_id':'SECRET','transcript_path':'SECRET'},10000)
  self.assertEqual([w['label'] for w in x['windows']],['5-hour','Weekly']);self.assertNotIn('SECRET',json.dumps(x))
 def test_invalid_and_expired_values_are_not_zero(self):
  for value in [None,-1,101,True,float('nan'),'bad']:
   self.assertEqual(normalize_codex({'rateLimits':{'primary':{'usedPercent':value,'resetsAt':20000,'windowDurationMins':300}}},10000)['windows'],[])
  self.assertEqual(normalize_claude({'rate_limits':{'five_hour':{'used_percentage':10,'resets_at':9000}}},10000)['windows'],[])
 def test_snapshot_stale_and_expired_windows(self):
  x={'codex':normalize_codex({'rateLimits':{'primary':{'usedPercent':25,'resetsAt':20000,'windowDurationMins':300}}},10000)}
  self.assertFalse(snapshot(x,10100)['codex']['stale']);self.assertTrue(snapshot(x,11000)['codex']['stale'])
  self.assertEqual(snapshot(x,21000)['codex']['windows'],[])
  self.assertEqual(snapshot({},10000)['claude']['state'],'unavailable')
 def test_ingest_strips_unknown_fields_and_limits_size(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'usage.json';x={'codex':{'capturedAt':10000,'windows':[{'label':'Weekly','usedPercent':25,'resetsAt':20000,'windowMinutes':10080,'token':'SECRET'}],'token':'SECRET'},'token':'SECRET'}
   ingest(json.dumps(x).encode(),p,10000)
   self.assertNotIn('SECRET',p.read_text());self.assertEqual(p.stat().st_mode & 0o777,0o600)
   with self.assertRaises(ValueError):ingest(b'x'*16385,p,10000)
 def test_future_timestamps_are_rejected(self):
  self.assertEqual(snapshot({'codex':{'capturedAt':999999,'windows':[]}},10000)['codex']['state'],'unavailable')
