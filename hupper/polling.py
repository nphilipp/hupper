import os
import threading
import time

from .interfaces import IFileMonitor


class PollingFileMonitor(threading.Thread, IFileMonitor):
    """ An :class:`hupper.interfaces.IFileMonitor` that stats the files
    a periodic intervals.

    ``callback`` is a callable that accepts a path to a changed file.

    ``poll_interval`` is a value in seconds between scans of the files on
    disk. Do not set this too low or it will eat your CPU and kill your drive.

    """
    def __init__(self, callback, poll_interval=1):
        super(PollingFileMonitor, self).__init__()
        self.callback = callback
        self.poll_interval = poll_interval
        self.paths = set()
        self.mtimes = {}
        self.lock = threading.Lock()

    def add_path(self, path):
        with self.lock:
            self.paths.add(path)

    def run(self):
        self.enabled = True
        while self.enabled:
            with self.lock:
                paths = list(self.paths)
            self.check_reload(paths)
            time.sleep(self.poll_interval)

    def stop(self):
        self.enabled = False

    def check_reload(self, paths):
        # if it's a python file then we could pyc and py as equivalent
        # and take the maximum mtime from both... we also update mtime
        # for both just incase both files are being tracked so that we
        # avoid counting both the first and second file as being changed
        changes = set()
        for path in paths:
            mtime = get_mtime(path)
            if path.endswith('.pyc'):
                py_path = path[:-1]
                mtime = max(get_mtime(py_path), mtime)
                self.mtimes[py_path] = mtime
            elif path.endswith('.py'):
                pyc_path = path + 'c'
                mtime = max(get_mtime(pyc_path), mtime)
                self.mtimes[pyc_path] = mtime
            if path not in self.mtimes:
                self.mtimes[path] = mtime
            elif self.mtimes[path] < mtime:
                self.mtimes[path] = mtime
                changes.add(path)
        for path in sorted(changes):
            self.callback(path)


def get_mtime(path):
    try:
        stat = os.stat(path)
        if stat:
            return stat.st_mtime
    except (OSError, IOError):
        pass
    return 0
