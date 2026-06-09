"""S3/R2 sink: buffers telemetry and uploads as JSONL."""

from __future__ import annotations

import time

from ros_tap.models import TelemetryFrame
from ros_tap.sinks.base import Sink


class S3Sink(Sink):
    def __init__(
        self,
        bucket: str,
        prefix: str = "ros_tap/",
        region: str | None = None,
        endpoint_url: str | None = None,
        buffer_size: int = 1000,
        flush_interval: float = 60.0,
    ):
        try:
            import boto3
        except ImportError:
            raise RuntimeError(
                "boto3 not installed. Install with: pip install 'ros_tap[s3]'"
            )

        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        kwargs = {}
        if region:
            kwargs["region_name"] = region
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._s3 = boto3.client("s3", **kwargs)
        self._buffer: list[str] = []
        self._last_flush = time.time()

    def write(self, frame: TelemetryFrame) -> None:
        self._buffer.append(self.serialize(frame))
        if len(self._buffer) >= self.buffer_size:
            self.flush()
        elif time.time() - self._last_flush > self.flush_interval:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        key = f"{self.prefix}{ts}_{len(self._buffer)}.jsonl"
        body = "\n".join(self._buffer) + "\n"
        self._s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/x-ndjson",
        )
        self._buffer.clear()
        self._last_flush = time.time()

    def close(self) -> None:
        self.flush()
