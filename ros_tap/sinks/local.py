"""Local file sink — writes JSONL telemetry to disk."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ros_tap.models import TelemetryFrame
from ros_tap.sinks.base import Sink


class LocalSink(Sink):
    def __init__(self, output_dir: str = "./ros_tap_data", rotate_mb: int = 50):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rotate_bytes = rotate_mb * 1024 * 1024
        self._file = None
        self._bytes_written = 0
        self._open_new_file()

    def _open_new_file(self):
        if self._file:
            self._file.close()
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"tap_{ts}.jsonl"
        self._file = open(path, "a")
        self._bytes_written = 0

    def write(self, frame: TelemetryFrame) -> None:
        line = self.serialize(frame) + "\n"
        self._file.write(line)
        self._bytes_written += len(line.encode())
        if self._bytes_written >= self.rotate_bytes:
            self._open_new_file()

    def flush(self) -> None:
        if self._file:
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None
