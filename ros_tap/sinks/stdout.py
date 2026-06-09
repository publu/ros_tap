"""Stdout sink: prints telemetry as JSONL for piping."""

from __future__ import annotations

import sys

from ros_tap.models import TelemetryFrame
from ros_tap.sinks.base import Sink


class StdoutSink(Sink):
    def write(self, frame: TelemetryFrame) -> None:
        sys.stdout.write(self.serialize(frame) + "\n")

    def flush(self) -> None:
        sys.stdout.flush()

    def close(self) -> None:
        self.flush()
