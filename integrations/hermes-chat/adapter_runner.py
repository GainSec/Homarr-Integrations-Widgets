"""Run only Hermes's installed gateway API adapter; leave messaging runner alone."""
import asyncio,os,signal,sys
from pathlib import Path
repo=Path(os.environ.get('HERMES_REPO',str(Path.home()/'.hermes/hermes-agent'))).expanduser()
sys.path.insert(0,str(repo))
from dotenv import load_dotenv
load_dotenv(Path(os.environ.get('HERMES_HOME',str(Path.home()/'.hermes'))).expanduser()/'.env',override=False)
from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter
async def main():
 stop=asyncio.Event()
 for sig in (signal.SIGTERM,signal.SIGINT):asyncio.get_running_loop().add_signal_handler(sig,stop.set)
 adapter=APIServerAdapter(PlatformConfig(enabled=True,extra={'host':'127.0.0.1','port':int(os.environ.get('HERMES_API_PORT','18642')),'key':os.environ['API_SERVER_KEY']}))
 try:
  if not await adapter.connect():raise RuntimeError('Hermes API adapter failed to start')
  await stop.wait()
 finally:await adapter.disconnect()
if __name__=='__main__':asyncio.run(main())
