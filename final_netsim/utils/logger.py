import time

class Logger:
    def __init__(self):
        self.entries = []

    def log(self, event_type, message, details=None):
        e = {
            'id': len(self.entries),
            'time_str': time.strftime('%H:%M:%S'),
            'event_type': event_type,
            'message': message,
            'details': details or {}
        }
        self.entries.append(e)
        return e

    def clear(self):
        self.entries = []

    def all(self):
        return self.entries

    def recent(self, n=300):
        return self.entries[-n:]

logger = Logger()
