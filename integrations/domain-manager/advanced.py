"""Unlocked full site-block edits; preserve Caddyfile startup and DNS ownership."""
import fcntl,json,time,uuid
from inventory_health import site_blocks,validate_site_block
from engine import DomainError,atomic,write_in_place
class Advanced:
 def __init__(self,engine):self.engine=engine
 def site(self,ident):
  try:site=next((s for s in site_blocks(self.engine.file.read_text()) if s['id']==ident),None)
  except ValueError as e:raise DomainError(str(e))
  if site is None:raise DomainError('Site no longer exists. Refresh the inventory.')
  return site
 def preview(self,ident,text,revision):
  e=self.engine
  if e.pending.exists():raise DomainError('An incomplete change needs recovery')
  if e.revision()!=revision:raise DomainError('Configuration changed. Refresh and review again.')
  site=self.site(ident)
  try:raw=validate_site_block(text,site['hosts'])
  except ValueError as ex:raise DomainError(str(ex))
  before=e.file.read_text();candidate=before[:site['start']]+raw.rstrip('\n')+before[site['end']:]
  e.caddy.assert_sync(before);e.caddy.validate(candidate)
  return site,candidate,raw
 def apply(self,ident,text,revision):
  e=self.engine
  with open(e.root/'lock','a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);site,candidate,raw=self.preview(ident,text,revision);before=e.file.read_text();old=e.routes();routes=json.loads(json.dumps(old))
   # Future managed create/remove operations must retain this block verbatim.
   for r in routes:
    if r['hostname'] in site['hosts']:r['siteBlock']=raw
   backup=e.root/'backups'/time.strftime('%Y%m%d-%H%M%S')/uuid.uuid4().hex;backup.mkdir(parents=True,mode=0o700)
   for name,value in [('Caddyfile',before),('active.json',json.dumps(e.caddy.export())),('routes.json',json.dumps(old))]:
    p=backup/name;p.write_text(value);p.chmod(0o600)
   atomic(e.pending,{'kind':'advanced','route':{},'old_routes':old,'before':before,'candidate':candidate})
   try:
    write_in_place(e.file,candidate);e.caddy.reload(candidate);e.caddy.assert_sync(candidate);atomic(e.state,{'routes':routes});e.clear_pending()
   except Exception:
    try:e.rollback(json.loads(e.pending.read_text()))
    except Exception:raise DomainError('Recovery needs review; editing is locked') from None
    raise DomainError('Advanced edit failed and was rolled back') from None
   atomic(backup/'result.json',{'status':'success','operation':'advanced','hostnames':site['hosts'],'at':time.time()});return {'hosts':site['hosts']}
