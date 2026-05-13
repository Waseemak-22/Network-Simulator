import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from datalink_layer.frame import BROADCAST_MAC, MULTICAST_MAC

class Bridge:
    """
    Bridge connects exactly 2 network segments.
    It LEARNS which MAC is on which segment, then:
      FILTER  → same segment, no need to cross
      FORWARD → destination is on the other segment
      FLOOD   → destination unknown, send everywhere
    """
    def __init__(self, name):
        self.name        = name
        self.type        = 'bridge'
        self.ports       = {}       # port_num -> hub or device
        self.mac_table   = {}       # mac -> port_num
        self.frame_count = 0
        self._seen       = set()

    def connect_segment(self, segment, port=None):
        if port is None:
            port = len(self.ports) + 1
        self.ports[port] = segment
        # tell segment about bridge
        if hasattr(segment, 'connect_uplink'):
            segment.connect_uplink(self, port=98)
        elif hasattr(segment, 'connect'):
            segment.connect(self, port)
        logger.log('CONNECT',
            f'🌉 {segment.name} ──bridge── {self.name}  [port {port}]',
            {'bridge': self.name, 'segment': segment.name, 'port': port})
        return port

    def _learn(self, mac, port):
        if mac not in self.mac_table:
            self.mac_table[mac] = port
            logger.log('MAC_LEARN',
                f'🌉 Bridge {self.name} learned  {mac}  →  port {port}',
                {'bridge': self.name, 'mac': mac, 'port': port})

    def receive_frame(self, frame, incoming_port=None):
        if frame.frame_id in self._seen:
            return
        self._seen.add(frame.frame_id)
        if len(self._seen) > 5000:
            self._seen.clear()

        self.frame_count += 1
        self._learn(frame.src_mac, incoming_port)
        dst = frame.dst_mac

        if dst == BROADCAST_MAC or dst == MULTICAST_MAC:
            logger.log('BRIDGE',
                f'🌉 Bridge {self.name} FLOODS {frame.ftype} to all segments',
                {'bridge': self.name, 'action': 'FLOOD'})
            self._flood(frame, incoming_port)
            return

        if dst in self.mac_table:
            out = self.mac_table[dst]
            if out == incoming_port:
                logger.log('BRIDGE',
                    f'🌉 Bridge {self.name} FILTERS frame — same segment, no crossing needed',
                    {'bridge': self.name, 'action': 'FILTER', 'port': out})
                # still deliver within same segment
                self.ports[out].receive_frame(frame, incoming_port=out)
            else:
                logger.log('BRIDGE',
                    f'🌉 Bridge {self.name} FORWARDS frame to port {out} (cross-segment ✅)',
                    {'bridge': self.name, 'action': 'FORWARD', 'out_port': out})
                self.ports[out].receive_frame(frame, incoming_port=out)
        else:
            logger.log('BRIDGE',
                f'🌉 Bridge {self.name} FLOODS (MAC unknown)',
                {'bridge': self.name, 'action': 'FLOOD'})
            self._flood(frame, incoming_port)

    def _flood(self, frame, incoming_port):
        for pnum, seg in self.ports.items():
            if pnum != incoming_port:
                seg.receive_frame(frame, incoming_port=pnum)

    def to_dict(self):
        return {'name': self.name, 'type': 'bridge',
                'segments': list(self.ports.keys()),
                'mac_table': [{'mac': m, 'port': p} for m, p in self.mac_table.items()],
                'frame_count': self.frame_count}
