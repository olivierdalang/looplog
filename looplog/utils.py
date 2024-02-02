import sys
import time
from datetime import timedelta
from typing import Optional


class LineWriter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.last_len = 0

    def provln(self, text: str):
        """Write a provisional line (no break, replacing current line)"""
        if not self.enabled:
            return
        pad = " " * self.last_len
        sys.stdout.write(f"\r{pad}")
        sys.stdout.write(f"\r{text}")
        self.last_len = len(text)

    def nextln(self):
        """Make the current line definitive"""
        if not self.enabled:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()

    def writeln(self, text: str):
        """Write a definitive line"""
        if not self.enabled:
            return
        self.provln(text)
        self.nextln()


def progress(val: int, max_val: Optional[int]):
    WIDTH = 22
    if max_val:
        p = round(WIDTH * val / max(1, max_val - 1))
        f = "#" * p
        e = " " * (WIDTH - p)
        return f"{f}{e}"
    else:
        q = [" "] * WIDTH
        q[val % WIDTH] = "#"
        return "".join(q)


class Timer:
    def __init__(self):
        self.start = time.time()

    def __str__(self):
        return str(timedelta(seconds=round(time.time() - self.start)))
