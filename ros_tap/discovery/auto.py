"""Auto detect available ROS versions on the network."""

from __future__ import annotations

from ros_tap.models import RobotNode


def auto_discover(
    ros1_uri: str | None = None,
    ros2_domain: int = 0,
    timeout: float = 3.0,
) -> list[RobotNode]:
    nodes: list[RobotNode] = []
    errors: list[str] = []

    try:
        from ros_tap.discovery.ros1_master import discover_ros1_nodes, is_master_reachable
        if is_master_reachable(ros1_uri):
            nodes.extend(discover_ros1_nodes(ros1_uri))
    except Exception as e:
        errors.append(f"ROS 1: {e}")

    try:
        from ros_tap.discovery.ros2_dds import discover_ros2_nodes
        nodes.extend(discover_ros2_nodes(ros2_domain, timeout))
    except Exception as e:
        errors.append(f"ROS 2: {e}")

    if not nodes and errors:
        from rich.console import Console
        c = Console(stderr=True)
        c.print("[yellow]No robots found. Discovery errors:[/yellow]")
        for err in errors:
            c.print(f"  [dim]{err}[/dim]")

    return nodes
