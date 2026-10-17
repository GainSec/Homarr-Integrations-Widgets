"""Fixed read-only routes; no arbitrary upstream URLs or actions."""
from collector_http import serve
import os
from openwrt_metadata import OpenWrtClient
def make_reader(client):
 def read(path):
  if path != '/openwrt/status':raise LookupError('Not found')
  return client.read()
 return read
def main():serve(make_reader(OpenWrtClient(root=os.environ['OPENWRT_SSH_DIR'],host=os.environ['OPENWRT_HOST'])),18087)

if __name__=='__main__':main()
