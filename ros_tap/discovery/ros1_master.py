"""ROS 1 discovery via the ROS Master XML RPC API."""

from __future__ import annotations

import os
import socket
from xmlrpc.client import ServerProxy

from ros_tap.models import RobotNode, Topic, classify_topic

CALLER_ID = "/ros_tap"


def get_master_uri() -> str:
    return os.environ.get("ROS_MASTER_URI", "http://localhost:11311")


def is_master_reachable(uri: str | None = None, timeout: float = 2.0) -> bool:
    uri = uri or get_master_uri()
    try:
        host = uri.split("//")[1].split(":")[0]
        port = int(uri.split(":")[-1].rstrip("/"))
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (OSError, ValueError, IndexError):
        return False


def discover_ros1_nodes(master_uri: str | None = None) -> list[RobotNode]:
    uri = master_uri or get_master_uri()
    master = ServerProxy(uri)

    code, msg, state = master.getSystemState(CALLER_ID)
    if code != 1:
        raise RuntimeError(f"ROS Master error: {msg}")

    publishers, _subscribers, _services = state

    topic_types = {}
    code2, _msg2, type_list = master.getTopicTypes(CALLER_ID)
    if code2 == 1:
        topic_types = dict(type_list)

    nodes: dict[str, RobotNode] = {}

    for topic_name, pub_nodes in publishers:
        msg_type = topic_types.get(topic_name, "unknown")
        topic = Topic(
            name=topic_name,
            msg_type=msg_type,
            publishers=list(pub_nodes),
            category=classify_topic(topic_name),
        )
        for node_name in pub_nodes:
            if node_name not in nodes:
                ns = "/".join(node_name.split("/")[:-1]) or "/"
                nodes[node_name] = RobotNode(name=node_name, namespace=ns, ros_version=1)
            nodes[node_name].topics.append(topic)

    return list(nodes.values())
