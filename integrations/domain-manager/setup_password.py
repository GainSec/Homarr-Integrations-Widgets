"""Update private config with a salted password hash, never argv/plaintext."""
import getpass,json,os,sys
from pathlib import Path
from server import hash_password
p=Path(sys.argv[1]);config=json.loads(p.read_text());a=getpass.getpass('New edit password: ');b=getpass.getpass('Confirm password: ')
if not a or a!=b:raise SystemExit('Passwords must match and be nonempty')
if len(a)>256:raise SystemExit('Password must contain at most 256 characters')
config['password']=hash_password(a);fd=os.open(p,os.O_WRONLY|os.O_TRUNC)
with os.fdopen(fd,'w') as f:json.dump(config,f,indent=2)
p.chmod(0o600)
