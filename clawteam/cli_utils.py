"""
CLI utilities for ClawTeam

Provides interactive CLI features like colored output and progress indicators.
"""
import os
import sys
from typing import Optional


def is_color_supported() -> bool:
    """Check if terminal supports colors"""
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return os.environ.get("TERM", "") != "dumb"


class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


class OutputStyle:
    """Output styling utilities"""
    _colors_enabled = True

    @classmethod
    def enable_colors(cls, enabled: bool = True):
        cls._colors_enabled = enabled

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        if cls._colors_enabled and is_color_supported():
            return f"{color}{text}{Colors.RESET}"
        return text

    @classmethod
    def success(cls, text: str) -> str:
        return cls.colorize(text, Colors.GREEN)

    @classmethod
    def warning(cls, text: str) -> str:
        return cls.colorize(text, Colors.YELLOW)

    @classmethod
    def error(cls, text: str) -> str:
        return cls.colorize(text, Colors.RED)

    @classmethod
    def info(cls, text: str) -> str:
        return cls.colorize(text, Colors.CYAN)

    @classmethod
    def dim(cls, text: str) -> str:
        return cls.colorize(text, Colors.DIM)


class Spinner:
    """Simple spinner for CLI"""
    FRAMES = ["-", "\\", "|", "/"]

    def __init__(self, desc: str = ""):
        self.desc = desc
        self.frame = 0
        self._running = False

    def _spin(self):
        if not is_color_supported():
            return
        frame = self.FRAMES[self.frame % len(self.FRAMES)]
        self.frame += 1
        text = f"{frame} {self.desc}" if self.desc else f"{frame} Working..."
        sys.stdout.write(f"\r{text}")
        sys.stdout.flush()

    def stop(self):
        if is_color_supported():
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()

    def __enter__(self):
        self._running = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class ProgressBar:
    """Simple progress bar for CLI"""

    def __init__(self, total: int, desc: str = "", width: int = 40):
        self.total = max(total, 1)
        self.desc = desc
        self.width = width
        self.current = 0

    def update(self, n: int = 1):
        self.current = min(self.current + n, self.total)
        self._render()

    def _render(self):
        if not is_color_supported():
            return
        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = "=" * filled + "-" * (self.width - filled)
        sys.stdout.write(f"\r[{bar}] {self.current}/{self.total} ({percent * 100:.0f}%)")
        sys.stdout.flush()
        if self.current >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def __enter__(self):
        self._render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.write("\n")
        sys.stdout.flush()
        return False


class Table:
    """Simple table renderer for CLI"""

    def __init__(self, headers):
        self.headers = headers
        self.rows = []

    def add_row(self, row):
        if len(row) != len(self.headers):
            raise ValueError(f"Row has {len(row)} columns, expected {len(self.headers)}")
        self.rows.append(row)

    def render(self):
        if not self.rows:
            return ""
        widths = [len(h) for h in self.headers]
        for row in self.rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        lines = []
        sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        lines.append(sep)
        header_cells = []
        for h, w in zip(self.headers, widths):
            header_cells.append(f" {h:<{w}} ")
        lines.append("|" + "|".join(header_cells) + "|")
        lines.append(sep.replace("-", "="))
        for row in self.rows:
            cells = []
            for cell, w in zip(row, widths):
                cells.append(f" {str(cell):<{w}} ")
            lines.append("|" + "|".join(cells) + "|")
        lines.append(sep)
        return "\n".join(lines)


class Confirm:
    """Simple yes/no confirmation prompt"""

    @staticmethod
    def prompt(message, default=None):
        choices = "[Y/n]" if default is True else "[y/N]" if default is False else "[y/n]"
        while True:
            response = input(f"{message} {choices}: ").strip().lower()
            if not response and default is not None:
                return default
            if response in ("y", "yes"):
                return True
            if response in ("n", "no"):
                return False
            print("Please enter 'y' or 'n'")


__all__ = [
    "Colors",
    "OutputStyle",
    "Spinner",
    "ProgressBar",
    "Table",
    "Confirm",
    "is_color_supported",
]
