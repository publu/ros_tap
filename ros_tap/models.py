from __future__ import annotations

import time
from dataclasses import dataclass, field

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

KEYWORD_CATEGORIES = [
    ("battery", "power"),
    ("joint", "actuators"),
    ("motor", "actuators"),
    ("imu", "imu"),
    ("camera", "camera"),
    ("image", "camera"),
    ("scan", "lidar"),
    ("lidar", "lidar"),
    ("odom", "odometry"),
    ("temp", "thermal"),
    ("gps", "navigation"),
    ("gnss", "navigation"),
    ("force", "force_torque"),
    ("torque", "force_torque"),
    ("gripper", "actuators"),
]


def classify_topic(topic_name: str) -> str:
    for pattern, category in HEALTH_TOPICS.items():
        if pattern in topic_name:
            return category
    lower = topic_name.lower()
    for keyword, category in KEYWORD_CATEGORIES:
        if keyword in lower:
            return category
    return "other"


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
    ros_version: int = 2


@dataclass
class TelemetryFrame:
    timestamp: float = field(default_factory=time.time)
    source_node: str = ""
    topic: str = ""
    msg_type: str = ""
    data: dict = field(default_factory=dict)
    ros_version: int = 2
