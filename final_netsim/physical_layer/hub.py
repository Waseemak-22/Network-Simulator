import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger

class Hub:
    def __init__(self, name, num_ports=8):
        self.name        = name
        self.num_ports   = num_ports
        self.ports       = {}        # port_num -> device/switch/bridge
        self.type        = 'hub'
        self.frame_count = 0
        self._seen       = set()
        self.uplink_port = 99        # reserved for switch/bridge uplink

    def connect_device(self, device, port=None):
        if port is None:
            used = [p for p in self.ports if p != 99]
            port = max(used, default=0) + 1
        self.ports[port] = device
        device.connect(self, port)
        logger.log('CONNECT',
            f'🔌 {device.name} ──wire── {self.name}  [port {port}]',
            {'hub': self.name, 'device': device.name, 'port': port})

    def connect_uplink(self, target, port=99):
        self.ports[port] = target
        logger.log('CONNECT',
            f'🔗 {self.name} uplink ──── {target.name}',
            {'hub': self.name, 'target': target.name})

    def receive_frame(self, frame, incoming_port=None):
        if frame.frame_id in self._seen:
            return
        self._seen.add(frame.frame_id)
        if len(self._seen) > 5000:
            self._seen.clear()

        self.frame_count += 1
        out_ports = [p for p in self.ports if p != incoming_port]

        logger.log('HUB',
            f'🔵 {self.name} BROADCASTS frame to ALL ports {out_ports}  (from port {incoming_port})',
            {'hub': self.name, 'from_port': incoming_port,
             'to_ports': out_ports, 'frame_id': frame.frame_id,
             'src_mac': frame.src_mac, 'dst_mac': frame.dst_mac,
             'ftype': frame.ftype})

        for pnum, dev in self.ports.items():
            if pnum != incoming_port:
                dev.receive_frame(frame, incoming_port=pnum)

    def to_dict(self):
        devs = [{'port': p, 'device': d.name, 'mac': getattr(d, 'mac', 'N/A')}
                for p, d in self.ports.items() if p != 99]
        return {'name': self.name, 'type': 'hub',
                'num_ports': self.num_ports,
                'connected_devices': devs,
                'frame_count': self.frame_count}
