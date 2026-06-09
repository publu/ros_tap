from __future__ import annotations

import json
from abc import ABC, abstractmethod

from ros_tap.models import TelemetryFrame


class Sink(ABC):
    @abstractmethod
    def write(self, frame: TelemetryFrame) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    def serialize(self, frame: TelemetryFrame) -> str:
        return json.dumps({
            "ts": frame.timestamp,
            "node": frame.source_node,
            "topic": frame.topic,
            "type": frame.msg_type,
            "ros": frame.ros_version,
            "data": frame.data,
        }, default=str)
