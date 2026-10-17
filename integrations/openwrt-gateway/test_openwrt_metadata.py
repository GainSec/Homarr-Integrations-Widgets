import unittest,copy
from openwrt_metadata import sanitize

def sample():
 return {'board':{'hostname':'router-example','model':'GL-MT6000','release':{'version':'24.10.1'},'secret':'private'},'info':{'uptime':100,'memory':{'total':1000,'available':400}},'wan':{'up':True,'l3_device':'eth1','ipv4-address':[{'address':'198.51.100.44','mask':24}]},'lab':{'ipv4-address':[{'address':'192.0.2.1','mask':24}]},'wan_device':{'statistics':{'rx_bytes':10000,'tx_bytes':20000},'speed':'1000F'},'leases':{'dhcp_leases':[{'hostname':'wired','macaddr':'AA:BB:CC:DD:EE:01','ipaddr':'192.0.2.10'},{'hostname':'quiet','macaddr':'AA:BB:CC:DD:EE:03','ipaddr':'192.0.2.12'}]},'hints':{},'radios':[{'status':{'ssid':'Home','freq':5180,'channel':36},'stations':{'results':[{'mac':'AA:BB:CC:DD:EE:02','signal':-60,'rx':{'bytes':111,'rate':1000},'tx':{'bytes':222,'rate':2000}}]}}],'extras':{'neighbors':'192.0.2.10 dev br-lan.30 lladdr aa:bb:cc:dd:ee:01 REACHABLE\n198.51.100.1 dev eth1 lladdr aa:bb:cc:dd:ee:04 REACHABLE\n192.0.2.90 dev br-lan.30 FAILED','cpu':'cpu 100 0 100 800 0 0 0 0 0 0','ping':'1 packets transmitted, 1 packets received, 0% packet loss\nround-trip min/avg/max = 1.2/1.2/1.2 ms'}}
class OpenWrtTests(unittest.TestCase):
 def test_filters_wan_and_failed_neighbors(self):
  d=sanitize(sample());self.assertEqual(len(d['clients']),3);self.assertNotIn('198.51.100.1',str(d['clients']));self.assertNotIn('private',str(d))
 def test_associations_neighbors_and_leases_are_distinct(self):
  d=sanitize(sample());c={x['mac']:x for x in d['clients']};self.assertTrue(c['aa:bb:cc:dd:ee:02']['connected']);self.assertEqual(c['aa:bb:cc:dd:ee:01']['state'],'reachable');self.assertEqual(c['aa:bb:cc:dd:ee:03']['state'],'lease');self.assertIsNone(c['aa:bb:cc:dd:ee:03']['connected'])
 def test_stale_is_seen_not_confirmed_online(self):
  s=sample();s['extras']['neighbors']=s['extras']['neighbors'].replace('REACHABLE','STALE');d=sanitize(s);c=next(x for x in d['clients'] if x['ip']=='192.0.2.10');self.assertEqual(c['state'],'seen');self.assertIsNone(c['connected'])
 def test_first_sample_is_not_fake_zero_traffic(self):
  d=sanitize(sample());self.assertIsNone(d['gateway']['downloadBps']);self.assertIsNone(d['gateway']['cpuPercent']);self.assertEqual(d['gateway']['memoryPercent'],60)
 def test_counter_delta_and_direction(self):
  old=sample();new=copy.deepcopy(old);new['info']['uptime']=110;new['wan_device']['statistics']={'rx_bytes':11000,'tx_bytes':22000};new['extras']['cpu']='cpu 150 0 150 900 0 0 0 0 0 0';d=sanitize(new,old);self.assertEqual(d['gateway']['downloadBps'],100);self.assertEqual(d['gateway']['uploadBps'],200);self.assertEqual(d['gateway']['cpuPercent'],50)
 def test_restart_resets_rates(self):
  s=sample();s['info']['uptime']=1;d=sanitize(s,sample());self.assertIsNone(d['gateway']['downloadBps'])
 def test_empty_wifi_is_zero_but_failed_read_is_unknown(self):
  s=sample();s['radios'][0]['stations']={'results':[]};self.assertEqual(sanitize(s)['gateway']['wifiAssociated'],0);s['radios'][0]['stations']=None;self.assertIsNone(sanitize(s)['gateway']['wifiAssociated'])
 def test_ping_is_actual_probe(self):
  d=sanitize(sample());self.assertEqual(d['gateway']['pingMs'],1.2);self.assertEqual(d['gateway']['packetLossPercent'],0)
 def test_ping_with_realistic_long_header_parses_summary(self):
  s=sample();s['extras']['ping']='PING 1.1.1.1: 56 data bytes\n64 bytes from 1.1.1.1: seq=0 ttl=57 time=1.2 ms\n--- 1.1.1.1 ping statistics ---\n'+s['extras']['ping'];d=sanitize(s);self.assertEqual(d['gateway']['pingMs'],1.2);self.assertEqual(d['gateway']['packetLossPercent'],0)
 def test_missing_system_info_is_unavailable(self):
  s=sample();s['info']=None
  with self.assertRaises(ValueError):sanitize(s)

 def test_lan_neighbor_does_not_claim_known_wired_transport(self):
  d=sanitize(sample());c=next(x for x in d['clients'] if x['ip']=='192.0.2.10');self.assertIsNone(c['wireless'])
 def test_neighbor_failure_is_distinct_from_empty(self):
  s=sample();s['extras']['neighbors']=None;self.assertFalse(sanitize(s)['gateway']['neighborsAvailable']);s['extras']['neighbors']='';self.assertTrue(sanitize(s)['gateway']['neighborsAvailable'])
 def test_lease_failure_is_explicit(self):
  s=sample();s['leases']=None;self.assertFalse(sanitize(s)['gateway']['leasesAvailable'])
 def test_changed_wan_device_resets_traffic_sampling(self):
  old=sample();new=copy.deepcopy(old);new['info']['uptime']=110;new['wan']['l3_device']='eth2';new['wan_device']['statistics']['rx_bytes']=999999;self.assertIsNone(sanitize(new,old)['gateway']['downloadBps'])

 def test_missing_lan_scope_is_not_a_successful_empty_list(self):
  s=sample();s['lab']=None;d=sanitize(s);self.assertFalse(d['gateway']['neighborsAvailable']);self.assertFalse(d['gateway']['leasesAvailable']);self.assertEqual(d['gateway']['wifiAssociated'],1)

class ClientTests(unittest.TestCase):
 def test_collector_does_not_return_cached_success_after_failure(self):
  from openwrt_metadata import OpenWrtClient
  c=OpenWrtClient(runner=lambda:sample());c.read();c.until=0
  def fail():raise RuntimeError('private error')
  c.runner=fail
  with self.assertRaises(RuntimeError):c.read()
 def test_ssh_pins_host_and_uses_only_dedicated_key(self):
  from openwrt_metadata import OpenWrtClient
  args=OpenWrtClient().command();self.assertIn('StrictHostKeyChecking=yes',args);self.assertIn('IdentitiesOnly=yes',args);self.assertEqual(args[-2:],['root@router.example.net','snapshot'])
