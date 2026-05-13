import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physical_layer.device   import EndDevice
from physical_layer.hub      import Hub
from datalink_layer.switch   import Switch
from datalink_layer.bridge   import Bridge
from utils.logger import logger

MULTICAST_MAC = '01:00:5E:00:00:01'

class Topology:
    def __init__(self, name='Network'):
        self.name     = name
        self.devices  = {}
        self.hubs     = {}
        self.switches = {}
        self.bridges  = {}
        self._links   = []   # for canvas rendering

    # ── add nodes ─────────────────────────────────────────
    def add_device(self, name, mac=None, multicast_group=None):
        d = EndDevice(name, mac, multicast_group)
        self.devices[name] = d
        logger.log('TOPOLOGY', f'💻 Device "{name}" added  MAC:{d.mac}  group:{multicast_group}',
                   {'name': name, 'mac': d.mac, 'group': multicast_group})
        return d

    def add_hub(self, name, ports=8):
        h = Hub(name, ports)
        self.hubs[name] = h
        logger.log('TOPOLOGY', f'🔵 Hub "{name}" added ({ports} ports)', {'name': name})
        return h

    def add_switch(self, name, ports=8):
        s = Switch(name, ports)
        self.switches[name] = s
        logger.log('TOPOLOGY', f'🔲 Switch "{name}" added ({ports} ports)', {'name': name})
        return s

    def add_bridge(self, name):
        b = Bridge(name)
        self.bridges[name] = b
        logger.log('TOPOLOGY', f'🌉 Bridge "{name}" added', {'name': name})
        return b

    # ── connect ───────────────────────────────────────────
    def connect_to_hub(self, device_name, hub_name, port=None):
        self.hubs[hub_name].connect_device(self.devices[device_name], port)

    def connect_to_switch(self, device_name, switch_name, port=None):
        self.switches[switch_name].connect_device(self.devices[device_name], port)

    def connect_hub_to_switch(self, hub_name, switch_name, port=None):
        sw  = self.switches[switch_name]
        hub = self.hubs[hub_name]
        if port is None:
            port = len(sw.ports) + 1
        sw.ports[port] = hub
        hub.connect_uplink(sw, port=99)
        self._links.append({'from': hub_name, 'to': switch_name,
                            'ftype': 'hub', 'ttype': 'switch'})
        logger.log('CONNECT',
            f'🔗 {hub_name} ──trunk── {switch_name}  [sw port {port}]',
            {'hub': hub_name, 'switch': switch_name, 'port': port})

    def connect_hub_to_bridge(self, hub_name, bridge_name):
        hub    = self.hubs[hub_name]
        bridge = self.bridges[bridge_name]
        bridge.connect_segment(hub)
        self._links.append({'from': hub_name, 'to': bridge_name,
                            'ftype': 'hub', 'ttype': 'bridge'})

    def connect_device_to_bridge(self, device_name, bridge_name):
        dev    = self.devices[device_name]
        bridge = self.bridges[bridge_name]
        port   = bridge.connect_segment(dev)
        dev.connect(bridge, port)
        self._links.append({'from': device_name, 'to': bridge_name,
                            'ftype': 'device', 'ttype': 'bridge'})

    # ── domain analysis ───────────────────────────────────
    def total_collision_domains(self):
        total, hubs_on_sw = 0, set()
        for sw in self.switches.values():
            for p, d in sw.ports.items():
                t = getattr(d, 'type', '')
                if t == 'hub':
                    hubs_on_sw.add(d.name); total += 1
                elif hasattr(d, 'mac'):
                    total += 1
        for hn in self.hubs:
            if hn not in hubs_on_sw:
                total += 1
        for b in self.bridges.values():
            total += len(b.ports)
        if not self.switches and not self.hubs and not self.bridges:
            total = max(1, len(self.devices))
        return total

    def total_broadcast_domains(self):
        if self.switches: return 1
        if self.hubs:     return 1
        if self.bridges:  return 1
        return max(1, len(self.devices))

    # ── summary for frontend ──────────────────────────────
    def summary(self):
        devs = []
        for d in self.devices.values():
            e = d.to_dict()
            e['connected_to'] = None
            for h in self.hubs.values():
                for p, dev in h.ports.items():
                    if p != 99 and getattr(dev, 'name', '') == d.name:
                        e['connected_to'] = h.name; e['port'] = p
            for sw in self.switches.values():
                for p, dev in sw.ports.items():
                    if getattr(dev, 'name', '') == d.name and hasattr(dev, 'mac'):
                        e['connected_to'] = sw.name; e['port'] = p
            for br in self.bridges.values():
                for p, seg in br.ports.items():
                    if getattr(seg, 'name', '') == d.name:
                        e['connected_to'] = br.name; e['port'] = p
            devs.append(e)

        # detect direct P2P links (device connected directly to another device)
        p2p_links = []
        seen_pairs = set()
        for d in self.devices.values():
            ct = d.connected_to
            if ct and hasattr(ct, 'mac') and ct.name in self.devices:
                pair = tuple(sorted([d.name, ct.name]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    p2p_links.append({'from': d.name, 'to': ct.name})

        return {
            'topology_name':           self.name,
            'devices':                 devs,
            'hubs':                    [h.to_dict() for h in self.hubs.values()],
            'switches':                [s.to_dict() for s in self.switches.values()],
            'bridges':                 [b.to_dict() for b in self.bridges.values()],
            'hub_switch_links':        self._links,
            'p2p_links':               p2p_links,
            'total_collision_domains': self.total_collision_domains(),
            'total_broadcast_domains': self.total_broadcast_domains(),
            'multicast_mac':           MULTICAST_MAC
        }
