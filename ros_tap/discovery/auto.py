"""Auto-detect which ROS versions are available on the network."""

from __future__ import annotations

from ros_tap.models import RobotNode


def auto_discover(
    ros1_uri: str | None = None,
    ros2_domain: int = 0,
    timeout: float = 3.0,
) -> list[RobotNode]:
    """Try both ROS 1 and ROS 2 discovery, return whatever is found."""
    nodes: list[RobotNode] = []
    errors: list[str] = []

    try:
        from ros_tap.discovery.ros1_master import discover_ros1_nodes, is_master_reachable

        if is_master_reachable(ros1_uri):
            ros1_nodes = discover_ros1_nodes(ros1_uri)
            nodes.extend(ros1_nodes)
    except Exception as e:
        errors.append(f"ROS 1: {e}")

    try:
        from ros_tap.discovery.ros2_dds import discover_ros2_nodes

        ros2_nodes = discover_ros2_nodes(ros2_domain, timeout)
        nodes.extend(ros2_nodes)
    except Exception as e:
        errors.append(f"ROS 2: {e}")

    if not nodes and errors:
        from rich.console import Console
        c = Console(stderr=True)
        c.print("[yellow]No robots found. Discovery errors:[/yellow]")
        for err in errors:
            c.print(f"  [dim]{err}[/dim]")

    return nodes
