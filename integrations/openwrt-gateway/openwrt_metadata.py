"""Sanitized read-only OpenWrt snapshot feed, collected with a forced-command key."""
import datetime,ipaddress,json,math,pathlib,re,subprocess,threading,time

def number(value):return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None

def text(value):return value[:128] if isinstance(value,str) else ''

def mac(value):
 value=text(value).lower();return value if re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',value) else None

def sanitize(raw,previous=None):
 board=raw.get('board') or {};info=raw.get('info') or {};wan=raw.get('wan') or {};lab=raw.get('lab') or {};device=raw.get('wan_device') or {};extras=raw.get('extras') or {}
 if number(info.get('uptime')) is None:raise ValueError('Router snapshot unavailable')
 oldinfo=(previous or {}).get('info') or {};elapsed=info['uptime']-oldinfo.get('uptime',info['uptime'])
 def rate(key,current=None,old=None):
  if not previous or wan.get('l3_device')!=((previous.get('wan') or {}).get('l3_device')):return None
  current=(device.get('statistics') or {}) if current is None else current;old=(((previous or {}).get('wan_device') or {}).get('statistics') or {}) if old is None else old
  a=number(current.get(key));b=number(old.get(key));return round((a-b)/elapsed,2) if elapsed>0 and a is not None and b is not None and a>=b else None
 cpu=None
 try:
  now=[int(x) for x in extras['cpu'].split()[1:9]];old=[int(x) for x in previous['extras']['cpu'].split()[1:9]];total=sum(now)-sum(old);idle=now[3]+now[4]-old[3]-old[4]
  if elapsed>0 and total>0 and 0<=idle<=total:cpu=round(100*(total-idle)/total,1)
 except (TypeError,KeyError,ValueError,IndexError):pass
 memory=info.get('memory') or {};total=number(memory.get('total'));available=number(memory.get('available'));mem=round(100*(1-available/total),1) if total and available is not None and 0<=available<=total else None
 ping=(extras.get('ping') or '')[:2048];match=re.search(r'(?:round-trip|rtt)[^=]*=\s*[\d.]+/([\d.]+)/',ping);loss=re.search(r'([\d.]+)% packet loss',ping)
 networks=[]
 for addr in lab.get('ipv4-address',[]):
  try:networks.append(ipaddress.ip_network(str(addr['address'])+'/'+str(addr['mask']),strict=False))
  except (KeyError,ValueError):pass
 def local_ip(ip):
  try:a=ipaddress.ip_address(ip);return a.version==4 and any(a in n for n in networks)
  except (ValueError,TypeError):return False
 leases={}
 for lease in (raw.get('leases') or {}).get('dhcp_leases',[]):
  key=mac(lease.get('macaddr'))
  if key and local_ip(lease.get('ipaddr')):leases[key]=lease
 hints={str(k).lower():v for k,v in (raw.get('hints') or {}).items() if isinstance(v,dict)}
 def base(key):
  lease=leases.get(key,{});hint=hints.get(key,{});ips=[x for x in hint.get('ipaddrs',[]) if local_ip(x)];ip=lease.get('ipaddr') or (ips[0] if ips else '')
  return {'mac':key,'name':text(lease.get('hostname') or hint.get('name') or ip or key),'ip':text(ip),'connected':None,'state':'lease','wireless':None,'interface':None,'signal':None,'ssid':None,'band':None}
 clients={};radios=[];wifi_available=True;associated=0
 for index,radio in enumerate(raw.get('radios') or []):
  status=radio.get('status') or {};stations=radio.get('stations');freq=number(status.get('freq'));band='2.4 GHz' if freq and freq<3000 else '5 GHz' if freq and freq<5925 else '6 GHz' if freq else None
  valid=isinstance(stations,dict) and isinstance(stations.get('results'),list);wifi_available=wifi_available and valid
  radios.append({'ssid':text(status.get('ssid')),'band':band,'channel':number(status.get('channel')),'associated':len(stations['results']) if valid else None})
  for station in stations['results'] if valid else []:
   key=mac(station.get('mac'))
   if not key:continue
   associated+=1;c=base(key);c.update({'wireless':True,'connected':True,'state':'associated','signal':number(station.get('signal')),'ssid':text(status.get('ssid')),'band':band});clients[key]=c
 neighbor_text=extras.get('neighbors')
 for line in neighbor_text.splitlines() if isinstance(neighbor_text,str) else []:
  parts=line.split()
  if not parts or not local_ip(parts[0]) or parts[-1] in {'FAILED','INCOMPLETE','NOARP','PERMANENT'} or 'lladdr' not in parts or 'dev' not in parts:continue
  try:key=mac(parts[parts.index('lladdr')+1]);interface=parts[parts.index('dev')+1]
  except IndexError:continue
  if not key or interface==wan.get('l3_device'):continue
  if key in clients:
   if not clients[key]['ip']:clients[key]['ip']=parts[0]
   continue
  c=base(key);c.update({'ip':parts[0],'interface':text(interface),'connected':True if parts[-1]=='REACHABLE' else None,'state':'reachable' if parts[-1]=='REACHABLE' else 'seen'});clients[key]=c
 for key in leases:
  if key not in clients:clients[key]=base(key)
 gateway={'hostname':text(board.get('hostname')),'model':text(board.get('model')),'version':text((board.get('release') or {}).get('version')),'uptimeSeconds':info['uptime'],'wanUp':wan.get('up') if isinstance(wan.get('up'),bool) else None,'wanIp':text(next((a.get('address') for a in wan.get('ipv4-address',[]) if a.get('address')),'')),'downloadBps':rate('rx_bytes'),'uploadBps':rate('tx_bytes'),'cpuPercent':cpu,'memoryPercent':mem,'pingMs':float(match.group(1)) if match else None,'packetLossPercent':float(loss.group(1)) if loss else None,'pingTarget':'1.1.1.1','link':text(device.get('speed')),'wifiAssociated':associated if wifi_available and raw.get('radios') else None,'neighborsAvailable':bool(networks) and isinstance(neighbor_text,str),'leasesAvailable':bool(networks) and isinstance(raw.get('leases'),dict) and isinstance(raw['leases'].get('dhcp_leases'),list)}
 return {'gateway':gateway,'radios':radios,'clients':sorted(clients.values(),key=lambda c:(c['state']=='lease',not c['wireless'],c['name'].lower())),'capturedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'OpenWrt Wi-Fi associations and LAN neighbor observations; DHCP-only entries are unconfirmed.'}

class OpenWrtClient:
 def __init__(self,root='/etc/homarr-openwrt-gateway',runner=None,host='router.example.net'):
  if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]{0,252}',host):raise ValueError('Invalid router host')
  self.host=host;self.root=pathlib.Path(root);self.runner=runner or self.run;self.lock=threading.RLock();self.previous=None;self.cache=None;self.until=0
 def command(self):return ['ssh','-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','UserKnownHostsFile='+str(self.root/'openwrt-known-hosts'),'-i',str(self.root/'openwrt-readonly'),'root@'+self.host,'snapshot']
 def run(self):
  p=subprocess.run(self.command(),capture_output=True,timeout=12)
  if p.returncode or len(p.stdout)>2*1024*1024:raise RuntimeError('OpenWrt snapshot unavailable')
  return json.loads(p.stdout)
 def read(self):
  with self.lock:
   if self.cache is not None and time.monotonic()<self.until:return self.cache
   raw=self.runner();result=sanitize(raw,self.previous);self.previous=raw;self.cache=result;self.until=time.monotonic()+15;return result
