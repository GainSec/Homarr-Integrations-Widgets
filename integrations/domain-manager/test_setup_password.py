import json,runpy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
class PasswordSetupTests(unittest.TestCase):
 def test_oversized_password_leaves_config_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json';before='{"password":{"salt":"original","hash":"original"}}\n';p.write_text(before)
   with patch('sys.argv',['setup_password.py',str(p)]),patch('getpass.getpass',side_effect=['x'*257,'x'*257]):
    with self.assertRaises(SystemExit) as error:runpy.run_path(str(Path(__file__).with_name('setup_password.py')),run_name='__main__')
   self.assertIn('256',str(error.exception));self.assertEqual(p.read_text(),before)
