"""ROS 2 discovery via DDS (CycloneDDS)."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from ros_tap.models import RobotNode, Topic, classify_topic


@dataclass
class DDSParticipant:
    guid: bytes
    name: str
    namespace: str


def discover_ros2_nodes(domain_id: int = 0, timeout: float = 3.0) -> list[RobotNode]:
    """Discover ROS 2 nodes on the DDS network.

    Uses CycloneDDS to join the DDS domain and enumerate
    discovered participants and their endpoints.
    """
    try:
        from cyclonedds.core import WaitSet
        from cyclonedds.builtin import DcpsParticipant, DcpsEndpoint
        from cyclonedds.domain import DomainParticipant
        from cyclonedds.util import duration
        import cyclonedds.builtin as builtin
    except ImportError:
        raise RuntimeError(
            "cyclonedds not installed. Install with: pip install 'ros_tap[all]' "
            "or pip install cyclonedds"
        )

    dp = DomainParticipant(domain_id)

    participant_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsParticipant)
    endpoint_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)

    import time
    time.sleep(timeout)

    nodes: dict[str, RobotNode] = {}

    for sample in participant_reader.read():
        if sample is None:
            continue
        key = sample.key
        name = getattr(sample, "qos", {}).get("__name__", f"participant_{key.hex()[:8]}")
        node = RobotNode(
            name=name,
            namespace="/",
            ros_version=2,
        )
        nodes[key.hex()] = node

    for sample in endpoint_reader.read():
        if sample is None:
            continue
        topic_name = sample.topic_name
        type_name = sample.type_name
        topic = Topic(
            name=topic_name,
            msg_type=type_name,
            category=classify_topic(topic_name),
        )
        pkey = sample.participant_key.hex() if hasattr(sample, "participant_key") else None
        if pkey and pkey in nodes:
            nodes[pkey].topics.append(topic)
        else:
            fallback_key = f"unknown_{len(nodes)}"
            if fallback_key not in nodes:
                nodes[fallback_key] = RobotNode(name="unknown", namespace="/", ros_version=2)
            nodes[fallback_key].topics.append(topic)

    return list(nodes.values())


def discover_ros2_topics(domain_id: int = 0, timeout: float = 3.0) -> list[Topic]:
    """Discover all ROS 2 topics without node association."""
    try:
        from cyclonedds.domain import DomainParticipant
        import cyclonedds.builtin as builtin
    except ImportError:
        raise RuntimeError("cyclonedds not installed.")

    dp = DomainParticipant(domain_id)

    pub_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)
    sub_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsSubscription)

    import time
    time.sleep(timeout)

    seen: dict[str, Topic] = {}

    for sample in list(pub_reader.read()) + list(sub_reader.read()):
        if sample is None:
            continue
        name = sample.topic_name
        if name not in seen:
            seen[name] = Topic(
                name=name,
                msg_type=sample.type_name,
                category=classify_topic(name),
            )

    return list(seen.values())
