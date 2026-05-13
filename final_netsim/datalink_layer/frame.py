import random, time

BROADCAST_MAC  = 'FF:FF:FF:FF:FF:FF'
MULTICAST_MAC  = '01:00:5E:00:00:01'

def crc(data):
    v = 0
    for c in data:
        v ^= ord(c)
    return format(v, '02X')

class Frame:
    _counter = 1000

    def __init__(self, src_mac, dst_mac, data, ftype='UNICAST'):
        Frame._counter += 1
        self.frame_id  = Frame._counter
        self.src_mac   = src_mac
        self.dst_mac   = dst_mac
        self.data      = data
        self.ftype     = ftype          # UNICAST / BROADCAST / MULTICAST
        self.crc       = crc(data)
        self.corrupted = False

    def corrupt(self):
        self.corrupted = True
        lst = list(self.data)
        lst[0] = chr(ord(lst[0]) ^ 0xFF)
        self.data = ''.join(lst)

    def valid(self):
        return (not self.corrupted) and (crc(self.data) == self.crc)

    def to_dict(self):
        return {
            'frame_id': self.frame_id,
            'src_mac':  self.src_mac,
            'dst_mac':  self.dst_mac,
            'data':     self.data,
            'crc':      self.crc,
            'valid':    self.valid(),
            'ftype':    self.ftype
        }
