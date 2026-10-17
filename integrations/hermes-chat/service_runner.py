"""Launch beside the installed Mac Hermes using its managed dependency runtime."""
import os,runpy,sys
from pathlib import Path
ROOT=Path(__file__).parent
repo=Path(os.environ.get('HERMES_REPO',str(Path.home()/'.hermes/hermes-agent'))).expanduser()
sys.path.insert(0,str(repo))
sys._hermes_pin_default_home=True
import hermes_bootstrap  # activates the same managed dependency generation as gateway
# Runtime environment is loaded by the caller, never from a committed secret file.
mode=sys.argv[1] if len(sys.argv)>1 else ''
if mode not in {'api','chat'}:raise SystemExit('Expected api or chat')
sys.path.insert(0,str(ROOT))
sys.argv=[str(ROOT/('adapter_runner.py' if mode=='api' else 'bridge.py'))]
runpy.run_path(sys.argv[0],run_name='__main__')
