import random, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger

class Channel:
    def __init__(self):
        self.busy       = False
        self.collisions = 0
        self.successes  = 0

class CSMACD:
    def __init__(self, channel, max_retries=6):
        self.channel     = channel
        self.max_retries = max_retries

    def transmit(self, sender_name, frame):
        steps = []
        for attempt in range(1, self.max_retries + 1):

            # sense channel
            if self.channel.busy:
                logger.log('CSMA',
                    f'⏳ {sender_name}: channel BUSY — waiting  (attempt {attempt})',
                    {'sender': sender_name, 'attempt': attempt, 'state': 'BUSY'})
                steps.append({'attempt': attempt, 'state': 'BUSY'})
                time.sleep(0.01 * attempt)
                continue

            # channel free — transmit
            self.channel.busy = True
            steps.append({'attempt': attempt, 'state': 'SENSING_FREE'})

            # simulate collision (30% chance on first attempt)
            collision = (attempt == 1 and random.random() < 0.30)
            if collision:
                self.channel.collisions += 1
                self.channel.busy = False
                backoff = random.randint(0, 2 ** min(attempt, 10) - 1)
                logger.log('COLLISION',
                    f'💥 {sender_name}: COLLISION detected!  Jam signal sent.  Backoff = {backoff} slots',
                    {'sender': sender_name, 'attempt': attempt, 'backoff': backoff,
                     'total_collisions': self.channel.collisions})
                steps.append({'attempt': attempt, 'state': 'COLLISION', 'backoff': backoff})
                time.sleep(backoff * 0.005)
                continue

            # success
            self.channel.successes += 1
            self.channel.busy = False
            logger.log('CSMA_OK',
                f'✅ {sender_name}: frame {frame.frame_id} transmitted successfully  (attempt {attempt})',
                {'sender': sender_name, 'attempt': attempt, 'frame_id': frame.frame_id})
            steps.append({'attempt': attempt, 'state': 'SUCCESS'})
            return {'success': True, 'attempts': attempt, 'steps': steps,
                    'collisions': self.channel.collisions}

        logger.log('CSMA_FAIL',
            f'❌ {sender_name}: max retries reached — frame DROPPED',
            {'sender': sender_name, 'max_retries': self.max_retries})
        return {'success': False, 'attempts': self.max_retries, 'steps': steps,
                'collisions': self.channel.collisions}
