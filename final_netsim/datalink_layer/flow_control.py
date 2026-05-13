import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger

class SlidingWindow:
    """
    ══════════════════════════════════════════════════════════
    FLOW CONTROL — Sliding Window Protocol
    ══════════════════════════════════════════════════════════

    PROBLEM SOLVED:
      Sender sends too fast → receiver gets overwhelmed → data lost.
      Flow control limits how many unacknowledged frames can be in transit.

    WINDOW SIZE:
      How many frames sender can send WITHOUT waiting for ACK.
      Window = 1 → send 1, wait for ACK, send 1, wait...  (slow)
      Window = 4 → send 4 at once, wait for ACK           (fast)

    ──────────────────────────────────────────────────────────
    Go-Back-N (GBN):
      If frame N is lost → retransmit N and ALL frames after N.
      Simple, but wastes bandwidth.

    Selective Repeat (SR):
      If frame N is lost → retransmit ONLY frame N.
      Efficient, receiver must buffer out-of-order frames.
    ══════════════════════════════════════════════════════════
    """

    def __init__(self, window_size=4, mode='GBN', error_rate=0.2):
        self.window_size = window_size
        self.mode        = mode
        self.error_rate  = error_rate

    def transmit(self, src_name, dst_name, chunks):
        if hasattr(src_name, 'name'):
            src_name = src_name.name
        if hasattr(dst_name, 'name'):
            dst_name = dst_name.name

        total    = len(chunks)
        acked    = [False] * total
        steps    = []
        retrans  = 0
        base     = 0
        next_seq = 0
        iters    = 0

        logger.log('FLOW_START',
            f'🚀 FLOW CONTROL START  |  Mode={self.mode}  |  Window={self.window_size}  |  Frames={total}  |  Error rate={int(self.error_rate*100)}%',
            {'mode': self.mode, 'window': self.window_size, 'total': total})

        if self.mode == 'GBN':
            logger.log('FLOW_INFO',
                '📖 Go-Back-N: if a frame is LOST → retransmit that frame AND all frames after it in the window', {})
        else:
            logger.log('FLOW_INFO',
                '📖 Selective Repeat: if a frame is LOST → retransmit ONLY that specific frame, keep others', {})

        while base < total and iters < total * 20:
            iters += 1

            # send all frames within window
            while next_seq < total and next_seq < base + self.window_size:
                lost = (random.random() < self.error_rate)
                step = {
                    'seq':    next_seq,
                    'data':   chunks[next_seq],
                    'action': 'LOST' if lost else 'SENT',
                    'win_start': base,
                    'win_end': min(base + self.window_size - 1, total - 1)
                }
                if lost:
                    logger.log('FLOW_LOST',
                        f'📦 Frame {next_seq} "{chunks[next_seq]}"  →  LOST in transit ✗  [window {base}..{min(base+self.window_size-1,total-1)}]',
                        step)
                else:
                    acked[next_seq] = True
                    logger.log('FLOW_SEND',
                        f'📦 Frame {next_seq} "{chunks[next_seq]}"  →  sent ✓  [window {base}..{min(base+self.window_size-1,total-1)}]',
                        step)
                steps.append(step)
                next_seq += 1

            # process ACKs
            if acked[base]:
                logger.log('FLOW_ACK',
                    f'✉️  ACK {base} received  →  window slides: {base} → {base+1}',
                    {'acked': base, 'new_base': base + 1})
                steps.append({'seq': base, 'action': 'ACK', 'new_base': base + 1})
                base += 1
            else:
                retrans += 1
                if self.mode == 'GBN':
                    logger.log('FLOW_RETRANS',
                        f'🔁 Go-Back-N: Frame {base} LOST → retransmitting frames {base}..{next_seq-1}  (going back!)',
                        {'mode': 'GBN', 'retransmit_from': base, 'retransmit_to': next_seq - 1})
                    steps.append({'seq': base, 'action': 'GBN_RETRANSMIT',
                                  'retransmit_from': base, 'retransmit_to': next_seq - 1})
                    next_seq = base  # go back
                else:
                    logger.log('FLOW_RETRANS',
                        f'🔁 Selective Repeat: ONLY frame {base} retransmitted (others kept in buffer)',
                        {'mode': 'SR', 'retransmit_seq': base})
                    steps.append({'seq': base, 'action': 'SR_RETRANSMIT', 'retransmit_seq': base})
                    acked[base] = True
                    base += 1

        success = base >= total
        logger.log('FLOW_DONE',
            f'{"✅ ALL" if success else "⚠️ PARTIAL"} {base}/{total} frames delivered  |  Retransmissions: {retrans}  |  Mode: {self.mode}',
            {'success': success, 'delivered': base, 'total': total, 'retransmissions': retrans})

        return {'success': success, 'mode': self.mode,
                'window_size': self.window_size, 'total_frames': total,
                'delivered': base, 'retransmissions': retrans, 'steps': steps}
