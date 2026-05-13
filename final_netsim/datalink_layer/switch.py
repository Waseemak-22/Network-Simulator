import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from datalink_layer.frame import BROADCAST_MAC, MULTICAST_MAC

class Switch:
    def __init__(self, name, num_ports=8):
        self.name        = name
        self.num_ports   = num_ports
        self.ports       = {}
        self.mac_table   = {}
        self.type        = 'switch'
        self.frame_count = 0

    def connect_device(self, device, port=None):
        if port is None:
            port = len(self.ports) + 1
        self.ports[port] = device
        device.connect(self, port)
        logger.log('CONNECT',
            f'🔌 {device.name} ──wire── {self.name}  [port {port}]',
            {'switch': self.name, 'device': device.name, 'port': port})

    def connect_hub(self, hub, port=None):
        if port is None:
            port = len(self.ports) + 1
        self.ports[port] = hub
        hub.connect_uplink(self, port=99)
        logger.log('CONNECT',
            f'🔗 {hub.name} ──trunk── {self.name}  [sw port {port}]',
            {'switch': self.name, 'hub': hub.name, 'port': port})

    def _learn(self, mac, port):
        if mac not in self.mac_table:
            self.mac_table[mac] = port
            logger.log('MAC_LEARN',
                f'📋 {self.name} learned  {mac}  →  port {port}',
                {'switch': self.name, 'mac': mac, 'port': port})

    def receive_frame(self, frame, incoming_port=None):
        self.frame_count += 1
        self._learn(frame.src_mac, incoming_port)
        dst = frame.dst_mac

        if dst == BROADCAST_MAC or dst == MULTICAST_MAC:
            logger.log('SWITCH',
                f'🔲 {self.name} FLOODS {frame.ftype} frame to all ports except {incoming_port}',
                {'switch': self.name, 'action': 'FLOOD', 'frame_id': frame.frame_id})
            self._flood(frame, incoming_port)
            return

        if dst in self.mac_table:
            out = self.mac_table[dst]
            if out == incoming_port:
                return
            logger.log('SWITCH',
                f'🔲 {self.name} FORWARDS frame → port {out}  (MAC known ✅)',
                {'switch': self.name, 'action': 'FORWARD',
                 'dst_mac': dst, 'out_port': out})
            self.ports[out].receive_frame(frame, incoming_port=out)
        else:
            logger.log('SWITCH',
                f'🔲 {self.name} FLOODS frame (MAC {dst[:11]}… unknown)',
                {'switch': self.name, 'action': 'FLOOD'})
            self._flood(frame, incoming_port)

    def _flood(self, frame, incoming_port):
        for pnum, dev in self.ports.items():
            if pnum != incoming_port:
                dev.receive_frame(frame, incoming_port=pnum)

    def to_dict(self):
        devs = []
        for p, d in self.ports.items():
            devs.append({'port': p, 'device': d.name,
                         'mac': getattr(d, 'mac', 'N/A'),
                         'type': getattr(d, 'type', 'enddevice')})
        return {'name': self.name, 'type': 'switch',
                'num_ports': self.num_ports,
                'connected_devices': devs,
                'mac_table': [{'mac': m, 'port': p} for m, p in self.mac_table.items()],
                'frame_count': self.frame_count}
