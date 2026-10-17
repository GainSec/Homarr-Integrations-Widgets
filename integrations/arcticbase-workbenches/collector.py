"""Fixed read-only routes; no arbitrary upstream URLs or actions."""
from collector_http import serve
import os,re,urllib.parse
from arctic_metadata import ArcticClient
def make_reader(client):
 def read(path):
  if path == '/arctic/workbenches':return client.workbenches()
  m=re.fullmatch(r'/arctic/workbenches/([A-Za-z0-9_-]{1,128})/objects',path)
  if m:return client.objects(m.group(1))
  raise LookupError('Not found')
 return read
def main():serve(make_reader(ArcticClient(os.environ['ARCTICBASE_ORIGIN'])),18085)

if __name__=='__main__':main()
