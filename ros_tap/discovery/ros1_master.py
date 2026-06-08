"""ROS 1 discovery via the ROS Master XML-RPC API."""

from __future__ import annotations

import socket
import os
from xmlrpc.client import ServerProxy
from ros_tap.models import RobotNode, Topic, classify_topic


def get_master_uri() -> str:
    return os.environ.get("ROS_MASTER_URI", "http://localhost:11311")


def is_master_reachable(uri: str | None = None, timeout: float = 2.0) -> bool:
    uri = uri or get_master_uri()
    host = uri.split("//")[1].split(":")[0]
    port = int(uri.split(":")[-1].rstrip("/"))
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (OSError, ValueError):
        return False


def discover_ros1_nodes(master_uri: str | None = None) -> list[RobotNode]:
    """Query the ROS 1 Master for all nodes and their topics."""
    uri = master_uri or get_master_uri()
    master = ServerProxy(uri)

    try:
        code, msg, state = master.getSystemState("/ros_tap")
    except Exception as e:
        raise RuntimeError(f"Cannot reach ROS Master at {uri}: {e}")

    if code != 1:
        raise RuntimeError(f"ROS Master returned error: {msg}")

    publishers, subscribers, services = state

    topic_type_map = {}
    try:
        code2, msg2, topic_types = master.getTopicTypes("/ros_tap")
        if code2 == 1:
            topic_type_map = {name: typ for name, typ in topic_types}
    except Exception:
        pass

    nodes: dict[str, RobotNode] = {}

    for topic_name, pub_nodes in publishers:
        msg_type = topic_type_map.get(topic_name, "unknown")
        topic = Topic(
            name=topic_name,
            msg_type=msg_type,
            publishers=list(pub_nodes),
            category=classify_topic(topic_name),
        )
        for node_name in pub_nodes:
            if node_name not in nodes:
                ns = "/".join(node_name.split("/")[:-1]) or "/"
                nodes[node_name] = RobotNode(
                    name=node_name,
                    namespace=ns,
                    ros_version=1,
                )
            nodes[node_name].topics.append(topic)

    return list(nodes.values())


def discover_ros1_topics(master_uri: str | None = None) -> list[Topic]:
    """Get all published topics from ROS 1 Master."""
    uri = master_uri or get_master_uri()
    master = ServerProxy(uri)

    try:
        code, msg, topics = master.getTopicTypes("/ros_tap")
    except Exception as e:
        raise RuntimeError(f"Cannot reach ROS Master at {uri}: {e}")

    if code != 1:
        raise RuntimeError(f"ROS Master returned error: {msg}")

    return [
        Topic(
            name=name,
            msg_type=msg_type,
            category=classify_topic(name),
        )
        for name, msg_type in topics
    ]
