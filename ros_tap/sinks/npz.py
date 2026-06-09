"""NPZ sink: buffers telemetry per topic and flushes as compressed numpy archives."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import numpy as np

from ros_tap.models import TelemetryFrame
from ros_tap.sinks.base import Sink


class NpzSink(Sink):
    def __init__(
        self,
        output_dir: str = "./ros_tap_data",
        flush_interval: float = 30.0,
        flush_samples: int = 10000,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.flush_interval = flush_interval
        self.flush_samples = flush_samples

        self._run_id = uuid.uuid4().hex[:12]
        self._run_start = time.time()
        self._run_dir = self.output_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}_{self._run_id}"
        self._run_dir.mkdir(parents=True, exist_ok=True)

        self._buffers: dict[str, list[dict]] = {}
        self._timestamps: dict[str, list[float]] = {}
        self._meta: dict[str, dict] = {}
        self._sample_counts: dict[str, int] = {}
        self._chunk_counts: dict[str, int] = {}
        self._last_flush = time.time()

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def write(self, frame: TelemetryFrame) -> None:
        topic = frame.topic

        if topic not in self._buffers:
            self._buffers[topic] = []
            self._timestamps[topic] = []
            self._sample_counts[topic] = 0
            self._chunk_counts[topic] = 0
            self._meta[topic] = {
                "msg_type": frame.msg_type,
                "source_node": frame.source_node,
                "ros_version": frame.ros_version,
                "category": frame.data.get("category", "unknown"),
            }

        self._buffers[topic].append(frame.data)
        self._timestamps[topic].append(frame.timestamp)
        self._sample_counts[topic] += 1

        total_buffered = sum(len(v) for v in self._buffers.values())
        if total_buffered >= self.flush_samples:
            self.flush()
        elif time.time() - self._last_flush > self.flush_interval:
            self.flush()

    def flush(self) -> None:
        for topic, samples in self._buffers.items():
            if not samples:
                continue
            self._flush_topic(topic, samples, self._timestamps[topic])

        self._buffers = {t: [] for t in self._buffers}
        self._timestamps = {t: [] for t in self._timestamps}
        self._last_flush = time.time()

    def _flush_topic(self, topic: str, samples: list[dict], timestamps: list[float]):
        safe_name = _topic_to_filename(topic)
        chunk = self._chunk_counts.get(topic, 0)
        self._chunk_counts[topic] = chunk + 1

        arrays: dict[str, np.ndarray] = {
            "timestamps": np.array(timestamps, dtype=np.float64),
        }

        for key, values in _to_columns(samples).items():
            try:
                arr = np.array(values)
                if arr.dtype.kind in ("f", "i", "u", "b"):
                    arrays[key] = arr
                else:
                    arrays[key] = np.array(values, dtype=object)
            except (ValueError, TypeError):
                arrays[key] = np.array(values, dtype=object)

        np.savez_compressed(self._run_dir / f"{safe_name}_{chunk:04d}.npz", **arrays)

    def close(self) -> None:
        self.flush()
        self._write_manifest()

    def _write_manifest(self):
        manifest = {
            "run_id": self._run_id,
            "start": self._run_start,
            "end": time.time(),
            "duration_s": round(time.time() - self._run_start, 2),
            "topics": {},
        }

        for topic, meta in self._meta.items():
            safe_name = _topic_to_filename(topic)
            chunks = self._chunk_counts.get(topic, 0)
            manifest["topics"][topic] = {
                **meta,
                "total_samples": self._sample_counts.get(topic, 0),
                "chunks": chunks,
                "files": [f"{safe_name}_{i:04d}.npz" for i in range(chunks)],
            }

        with open(self._run_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2, default=str)


def _topic_to_filename(topic: str) -> str:
    return topic.strip("/").replace("/", "_")


def _flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _to_columns(samples: list[dict]) -> dict[str, list]:
    if not samples:
        return {}

    all_keys: set[str] = set()
    flat_rows = []
    for s in samples:
        flat = _flatten(s)
        flat_rows.append(flat)
        all_keys.update(flat.keys())

    columns: dict[str, list] = {k: [] for k in sorted(all_keys)}
    for row in flat_rows:
        for k in columns:
            columns[k].append(row.get(k))

    return columns
