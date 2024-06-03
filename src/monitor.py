import threading
import time


class Monitor:
    instance = None
    lock = threading.Lock()

    def __new__(cls):
        with Monitor.lock:
            if Monitor.instance is None:
                Monitor.instance = super(Monitor, cls).__new__(cls)
        return Monitor.instance

    def __init__(self):
        self.topic_callbacks = {}
        self.timeout_thread = threading.Thread(target=self._check_timeouts, daemon=True)
        self.timeout_thread.start()

    def _check_timeouts(self):
        while True:
            time.sleep(5)
            with self.lock:
                current_time = time.time()
                for topic, data in list(self.topic_callbacks.items()):
                    elapsed_time = current_time - data["last_ping_time"]
                    if elapsed_time >= data["timeout"] and not data["timedout"]:
                        self.topic_callbacks[topic]["timedout"] = True
                        try:
                            data["callback"](topic)
                        except Exception as e:
                            raise e

    def register_callback(self, topic, callback, timeout_seconds):
        with self.lock:
            if topic not in self.topic_callbacks:
                self.topic_callbacks[topic] = {
                    "callback": callback,
                    "timeout": timeout_seconds,
                    "last_ping_time": time.time(),
                    "timedout": False,
                }

    def deregister_callback(self, topic):
        with self.lock:
            if topic in self.topic_callbacks:
                del self.topic_callbacks[topic]

    def ping_topic(self, topic):
        with self.lock:
            if topic in self.topic_callbacks:
                self.topic_callbacks[topic]["last_ping_time"] = time.time()
                self.topic_callbacks[topic]["timedout"] = False
