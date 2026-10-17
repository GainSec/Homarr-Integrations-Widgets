"""Fixed read-only routes; no arbitrary upstream URLs or actions."""
from collector_http import serve
import os
from unifi_metadata import UniFiClient
def make_reader(client):
 def read(path):
  if path not in ('/unifi/health','/unifi/clients'):raise LookupError('Not found')
  return client.read(path.rsplit('/',1)[1])
 return read
def main():serve(make_reader(UniFiClient(os.environ['UNIFI_CREDENTIALS_FILE'],os.environ['UNIFI_ORIGIN'],os.environ.get('UNIFI_SITE','default'))),18086)

if __name__=='__main__':main()
