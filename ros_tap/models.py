"""Shared data models for ros_tap."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Topic:
    name: str
    msg_type: str
    publishers: list[str] = field(default_factory=list)
    hz: float | None = None
    category: str = "unknown"


@dataclass
class RobotNode:
    name: str
    namespace: str
    topics: list[Topic] = field(default_factory=list)
    ros_version: int = 2  # 1 or 2


@dataclass
class TelemetryFrame:
    timestamp: float = field(default_factory=time.time)
    source_node: str = ""
    topic: str = ""
    msg_type: str = ""
    data: dict = field(default_factory=dict)
    ros_version: int = 2


HEALTH_TOPICS = {
    "/battery_state": "power",
    "/battery": "power",
    "/joint_states": "actuators",
    "/diagnostics": "diagnostics",
    "/odom": "odometry",
    "/imu": "imu",
    "/scan": "lidar",
    "/camera/image_raw": "camera",
    "/cmd_vel": "command",
    "/tf": "transforms",
    "/rosout": "logging",
    "/robot_description": "description",
    "/motor_states": "actuators",
    "/temperature": "thermal",
    "/cpu_monitor": "system",
    "/memory_monitor": "system",
}


def classify_topic(topic_name: str) -> str:
    for pattern, category in HEALTH_TOPICS.items():
        if pattern in topic_name:
            return category
    if "battery" in topic_name.lower():
        return "power"
    if "joint" in topic_name.lower():
        return "actuators"
    if "imu" in topic_name.lower():
        return "imu"
    if "camera" in topic_name.lower() or "image" in topic_name.lower():
        return "camera"
    if "scan" in topic_name.lower() or "lidar" in topic_name.lower():
        return "lidar"
    if "odom" in topic_name.lower():
        return "odometry"
    if "temp" in topic_name.lower():
        return "thermal"
    return "other"
