import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from datalink_layer.frame import Frame, BROADCAST_MAC, MULTICAST_MAC

def gen_mac():
    p = [random.randint(0, 255) for _ in range(6)]
    p[0] &= 0xFE
    return ':'.join(f'{x:02X}' for x in p)

class EndDevice:
    def __init__(self, name, mac=None, multicast_group=None):
        self.name             = name
        self.mac              = mac or gen_mac()
        self.multicast_group  = multicast_group   # e.g. 'VideoGroup'
        self.connected_to     = None
        self.port_on_device   = None
        self.inbox            = []
        self.sent_count       = 0
        self.recv_count       = 0
        self._seen_frames     = set()

    def connect(self, device, port):
        self.connected_to   = device
        self.port_on_device = port

    # ─── SEND ────────────────────────────────────────────────
    def send_unicast(self, data, dst_mac):
        frame = Frame(self.mac, dst_mac, data, ftype='UNICAST')
        self.sent_count += 1
        logger.log('SEND',
            f'📤 {self.name} → UNICAST "{data}" to {dst_mac}',
            {'src': self.name, 'src_mac': self.mac, 'dst_mac': dst_mac,
             'frame_id': frame.frame_id, 'crc': frame.crc})
        if self.connected_to:
            self.connected_to.receive_frame(frame, incoming_port=self.port_on_device)
        return frame

    def send_broadcast(self, data):
        frame = Frame(self.mac, BROADCAST_MAC, data, ftype='BROADCAST')
        self.sent_count += 1
        logger.log('BROADCAST',
            f'📢 {self.name} → BROADCAST "{data}" to FF:FF:FF:FF:FF:FF (ALL)',
            {'src': self.name, 'frame_id': frame.frame_id})
        if self.connected_to:
            self.connected_to.receive_frame(frame, incoming_port=self.port_on_device)
        return frame

    def send_multicast(self, data, group_mac=MULTICAST_MAC):
        frame = Frame(self.mac, group_mac, data, ftype='MULTICAST')
        self.sent_count += 1
        logger.log('MULTICAST',
            f'📡 {self.name} → MULTICAST "{data}" to group {group_mac}',
            {'src': self.name, 'group_mac': group_mac, 'frame_id': frame.frame_id})
        if self.connected_to:
            self.connected_to.receive_frame(frame, incoming_port=self.port_on_device)
        return frame

    # ─── RECEIVE ─────────────────────────────────────────────
    def receive_frame(self, frame, incoming_port=None):
        # loop prevention
        if frame.frame_id in self._seen_frames:
            return
        self._seen_frames.add(frame.frame_id)
        if len(self._seen_frames) > 5000:
            self._seen_frames.clear()

        dst = frame.dst_mac

        # decide if this frame is for me
        is_unicast_me  = (dst == self.mac)
        is_broadcast   = (dst == BROADCAST_MAC)
        # multicast: only accept if I am in a multicast group
        is_multicast   = (dst == MULTICAST_MAC and self.multicast_group is not None)

        if is_unicast_me or is_broadcast or is_multicast:
            ok = frame.valid()
            self.inbox.append(frame.to_dict())
            self.recv_count += 1
            tag  = '✅' if ok else '❌ CRC ERROR'
            kind = frame.ftype
            logger.log('RECEIVE',
                f'📥 {self.name} received [{kind}] "{frame.data}" from {frame.src_mac} {tag}',
                {'device': self.name, 'src_mac': frame.src_mac,
                 'data': frame.data, 'valid': ok,
                 'frame_id': frame.frame_id, 'ftype': kind})
        else:
            logger.log('DISCARD',
                f'🗑  {self.name} discarded frame — not for me (dst={dst})',
                {'device': self.name, 'my_mac': self.mac, 'dst_mac': dst})

    def to_dict(self):
        return {
            'name':            self.name,
            'mac':             self.mac,
            'multicast_group': self.multicast_group,
            'type':            'enddevice',
            'sent':            self.sent_count,
            'received':        self.recv_count
        }
