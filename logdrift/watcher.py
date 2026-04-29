"""Log file watcher module for logdrift.

Watches multiple log files for new lines and emits them for processing.
"""

import os
import time
from typing import Callable, Dict, Iterator, List, Optional


class LogFileWatcher:
    """Watches a single log file and yields new lines as they appear."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self._offset: int = 0
        self._inode: Optional[int] = None

    def _get_inode(self) -> Optional[int]:
        try:
            return os.stat(self.filepath).st_ino
        except FileNotFoundError:
            return None

    def _detect_rotation(self) -> bool:
        current_inode = self._get_inode()
        if current_inode is None:
            return False
        if self._inode is not None and current_inode != self._inode:
            self._offset = 0
            self._inode = current_inode
            return True
        self._inode = current_inode
        return False

    def read_new_lines(self) -> List[str]:
        """Read any new lines added since the last read."""
        self._detect_rotation()
        lines = []
        try:
            with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._offset)
                for line in f:
                    lines.append(line.rstrip("\n"))
                self._offset = f.tell()
        except FileNotFoundError:
            pass
        return lines


class MultiLogWatcher:
    """Watches multiple log files and dispatches new lines to a callback."""

    def __init__(self, filepaths: List[str], poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval
        self._watchers: Dict[str, LogFileWatcher] = {
            fp: LogFileWatcher(fp) for fp in filepaths
        }

    def add_file(self, filepath: str) -> None:
        if filepath not in self._watchers:
            self._watchers[filepath] = LogFileWatcher(filepath)

    def remove_file(self, filepath: str) -> None:
        self._watchers.pop(filepath, None)

    def poll_once(self) -> Iterator[tuple]:
        """Yield (filepath, line) tuples for all new lines across watched files."""
        for filepath, watcher in self._watchers.items():
            for line in watcher.read_new_lines():
                yield filepath, line

    def watch(self, callback: Callable[[str, str], None], stop_event=None) -> None:
        """Continuously poll files and invoke callback(filepath, line)."""
        while stop_event is None or not stop_event.is_set():
            for filepath, line in self.poll_once():
                callback(filepath, line)
            time.sleep(self.poll_interval)
