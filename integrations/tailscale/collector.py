"""Fixed read-only routes; no arbitrary upstream URLs or actions."""
from collector_http import serve
import os
from tailscale_collector import Collector
def make_reader(client):
 def read(path):
  if path != '/tailscale/devices':raise LookupError('Not found')
  return client.read()
 return read
def main():serve(make_reader(Collector(os.environ.get('TAILSCALE_BINARY','/usr/bin/tailscale'))),18082)

if __name__=='__main__':main()
