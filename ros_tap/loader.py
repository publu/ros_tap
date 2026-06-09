"""Load recorded NPZ runs back into Python for analysis."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class Run:
    """A recorded ros_tap run with its manifest and NPZ data."""

    def __init__(self, run_dir: str | Path):
        self.path = Path(run_dir)
        manifest_path = self.path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest.json in {self.path}")

        with open(manifest_path) as f:
            self.manifest = json.load(f)

        self.run_id = self.manifest["run_id"]
        self.start = self.manifest["start"]
        self.end = self.manifest["end"]
        self.duration = self.manifest["duration_s"]

    @property
    def topics(self) -> list[str]:
        return list(self.manifest["topics"].keys())

    def topic_info(self, topic: str) -> dict:
        return self.manifest["topics"][topic]

    def load(self, topic: str) -> dict[str, np.ndarray]:
        """Load all chunks for a topic, concatenated into single arrays."""
        info = self.manifest["topics"].get(topic)
        if not info:
            raise KeyError(f"Topic {topic} not in this run")

        merged: dict[str, list[np.ndarray]] = {}

        for filename in info["files"]:
            data = np.load(self.path / filename, allow_pickle=True)
            for key in data.files:
                if key not in merged:
                    merged[key] = []
                merged[key].append(data[key])

        return {k: np.concatenate(v) for k, v in merged.items()}

    def __repr__(self) -> str:
        return (
            f"Run(id={self.run_id}, "
            f"topics={len(self.topics)}, "
            f"duration={self.duration}s)"
        )


def list_runs(data_dir: str | Path = "./ros_tap_data") -> list[Run]:
    """Find all recorded runs in a directory."""
    data_path = Path(data_dir)
    if not data_path.exists():
        return []

    runs = []
    for d in sorted(data_path.iterdir()):
        if d.is_dir() and (d / "manifest.json").exists():
            runs.append(Run(d))
    return runs
