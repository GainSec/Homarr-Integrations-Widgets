"""Standalone fixed-catalog HTTP health collector; no domain editor required."""
import json,os
from pathlib import Path
from collector_http import serve
from inventory_health import HealthCache

def main():
 catalog=json.loads(Path(os.environ.get('SERVICE_CATALOG','/etc/homarr-services/catalog.json')).read_text())
 if not isinstance(catalog,list) or not all(isinstance(x,dict) and isinstance(x.get('url'),str) for x in catalog):raise ValueError('Invalid catalog')
 health=HealthCache(catalog,interval=60,frontdoor=os.environ.get('HEALTH_FRONTDOOR') or None);health.start()
 def read(path):
  if path!='/services/status':raise LookupError()
  return health.snapshot()
 serve(read,18085)
if __name__=='__main__':main()
