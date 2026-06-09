"""ROS 2 discovery via CycloneDDS."""

from __future__ import annotations

import time

from ros_tap.models import RobotNode, Topic, classify_topic


def discover_ros2_nodes(domain_id: int = 0, timeout: float = 3.0) -> list[RobotNode]:
    try:
        from cyclonedds.domain import DomainParticipant
        import cyclonedds.builtin as builtin
    except ImportError:
        raise RuntimeError(
            "cyclonedds not installed. Install with: pip install 'ros_tap[all]' "
            "or pip install cyclonedds"
        )

    dp = DomainParticipant(domain_id)
    participant_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsParticipant)
    endpoint_reader = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)

    time.sleep(timeout)

    nodes: dict[str, RobotNode] = {}

    for sample in participant_reader.read():
        if sample is None:
            continue
        key = sample.key
        name = getattr(sample, "qos", {}).get("__name__", f"participant_{key.hex()[:8]}")
        nodes[key.hex()] = RobotNode(name=name, namespace="/", ros_version=2)

    for sample in endpoint_reader.read():
        if sample is None:
            continue
        topic = Topic(
            name=sample.topic_name,
            msg_type=sample.type_name,
            category=classify_topic(sample.topic_name),
        )
        pkey = sample.participant_key.hex() if hasattr(sample, "participant_key") else None
        if pkey and pkey in nodes:
            nodes[pkey].topics.append(topic)
        else:
            fallback = f"unknown_{len(nodes)}"
            if fallback not in nodes:
                nodes[fallback] = RobotNode(name="unknown", namespace="/", ros_version=2)
            nodes[fallback].topics.append(topic)

    return list(nodes.values())
