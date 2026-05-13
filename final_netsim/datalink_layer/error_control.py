import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from datalink_layer.frame import Frame, crc

class ErrorControl:

    @staticmethod
    def check(frame):
        expected = crc(frame.data)
        ok = (expected == frame.crc) and not frame.corrupted
        result = {'frame_id': frame.frame_id, 'data': frame.data,
                  'sent_crc': frame.crc, 'expected_crc': expected, 'valid': ok}
        if ok:
            logger.log('CRC_OK',
                f'✅ CRC valid — frame {frame.frame_id}  [{frame.crc}]', result)
        else:
            logger.log('CRC_FAIL',
                f'❌ CRC MISMATCH — frame {frame.frame_id}  sent={frame.crc} expected={expected}', result)
        return result

    @staticmethod
    def corrupt_and_check(frame):
        orig = frame.data
        frame.corrupt()
        logger.log('CORRUPT',
            f'⚡ Frame {frame.frame_id} deliberately corrupted  "{orig}" → "{frame.data}"',
            {'original': orig, 'corrupted': frame.data})
        return ErrorControl.check(frame)

    @staticmethod
    def parity(data):
        bits = ''.join(f'{ord(c):08b}' for c in data)
        ones = bits.count('1')
        bit  = ones % 2
        ptype = 'EVEN' if bit == 0 else 'ODD'
        logger.log('PARITY',
            f'🔢 Parity of "{data}":  {ones} ones  →  parity bit = {bit}  ({ptype})',
            {'data': data, 'ones': ones, 'parity_bit': bit, 'parity_type': ptype})
        return {'data': data, 'ones': ones, 'parity_bit': bit, 'parity_type': ptype}
