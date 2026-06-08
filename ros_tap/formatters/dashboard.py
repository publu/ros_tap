"""Rich-based terminal dashboard for live robot health."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.live import Live

from ros_tap.models import RobotNode, Topic


CATEGORY_ICONS = {
    "power": "⚡",
    "actuators": "⚙",
    "diagnostics": "🩺",
    "odometry": "📍",
    "imu": "🧭",
    "lidar": "📡",
    "camera": "📷",
    "command": "🎮",
    "transforms": "🔗",
    "logging": "📝",
    "thermal": "🌡",
    "system": "💻",
    "other": "◦",
    "unknown": "?",
}


def build_node_panel(node: RobotNode) -> Panel:
    ros_badge = f"[bold green]ROS {node.ros_version}[/bold green]"
    title = f"{node.name}  {ros_badge}"

    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 1))
    table.add_column("", width=2)
    table.add_column("Topic", style="cyan", min_width=20)
    table.add_column("Type", style="dim")
    table.add_column("Category", style="yellow")

    categories_seen: set[str] = set()
    for topic in sorted(node.topics, key=lambda t: t.name):
        icon = CATEGORY_ICONS.get(topic.category, "◦")
        table.add_row(icon, topic.name, topic.msg_type, topic.category)
        categories_seen.add(topic.category)

    health_parts = []
    for cat in ["power", "actuators", "diagnostics", "odometry", "imu", "lidar", "camera"]:
        if cat in categories_seen:
            health_parts.append(f"[green]● {cat}[/green]")
        else:
            health_parts.append(f"[dim]○ {cat}[/dim]")

    subtitle = "  ".join(health_parts)

    return Panel(
        table,
        title=title,
        subtitle=subtitle,
        border_style="bright_cyan",
        padding=(1, 2),
    )


def render_scan_results(nodes: list[RobotNode], console: Console | None = None):
    c = console or Console()

    if not nodes:
        c.print(Panel(
            "[yellow]No robots found on the network.[/yellow]\n\n"
            "  • For ROS 2: ensure a robot is running on the same DDS domain\n"
            "  • For ROS 1: set ROS_MASTER_URI to point to the robot's master\n"
            "  • Try increasing timeout with --timeout",
            title="[bold]Scan Results[/bold]",
            border_style="yellow",
        ))
        return

    ros1_count = sum(1 for n in nodes if n.ros_version == 1)
    ros2_count = sum(1 for n in nodes if n.ros_version == 2)
    topic_count = sum(len(n.topics) for n in nodes)

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Nodes", str(len(nodes)))
    summary.add_row("Topics", str(topic_count))
    if ros1_count:
        summary.add_row("ROS 1", str(ros1_count))
    if ros2_count:
        summary.add_row("ROS 2", str(ros2_count))

    c.print(Panel(summary, title="[bold]Network Summary[/bold]", border_style="green"))
    c.print()

    for node in nodes:
        c.print(build_node_panel(node))
        c.print()
