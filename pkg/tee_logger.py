#!/usr/bin/env python3
"""
TeeLogger module for capturing stdout output to both console and log files.
"""

import re
import sys
from pathlib import Path


class TeeLogger:
    """A class to capture stdout and write to both console and log file."""

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.original_stdout = sys.stdout
        self.log_file = None

        # Ensure log directory exists
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        if self.log_file:
            self.log_file.close()

    def write(self, text):
        # Write to original stdout (console)
        self.original_stdout.write(text)
        self.original_stdout.flush()

        # Write to log file
        if self.log_file:
            # Remove Rich markup for cleaner log files
            clean_text = re.sub(r"\[/?[^\]]*\]", "", text)
            self.log_file.write(clean_text)
            self.log_file.flush()

    def flush(self):
        self.original_stdout.flush()
        if self.log_file:
            self.log_file.flush()
