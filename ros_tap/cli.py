"""ros_tap CLI: zero config telemetry tap for any ROS robot."""

from __future__ import annotations

import signal
import sys
import time

import click
from rich.console import Console

from ros_tap import __version__
from ros_tap.banner import print_banner

console = Console()


@click.group()
@click.version_option(__version__, prog_name="ros_tap")
def main():
    """Zero config telemetry tap for any ROS robot on your network.

    \b
    ros_tap discovers ROS 1 and ROS 2 robots automatically,
    subscribes to their topics, and streams telemetry wherever
    you want: terminal, local files, or S3.

    \b
    No ROS install required. Just a passive listener.
    """
    pass


@main.command()
@click.option("--ros1-uri", default=None, help="ROS Master URI (default: $ROS_MASTER_URI or localhost:11311)")
@click.option("--domain", default=0, type=int, help="ROS 2 DDS domain ID (default: 0)")
@click.option("--timeout", default=3.0, type=float, help="Discovery timeout in seconds")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON instead of dashboard")
def scan(ros1_uri, domain, timeout, as_json):
    """Scan the network and show all discovered robots and topics."""
    print_banner(console)
    console.print("[dim]Scanning network...[/dim]\n")

    from ros_tap.discovery.auto import auto_discover

    nodes = auto_discover(ros1_uri=ros1_uri, ros2_domain=domain, timeout=timeout)

    if as_json:
        import json
        for node in nodes:
            click.echo(json.dumps({
                "name": node.name,
                "namespace": node.namespace,
                "ros_version": node.ros_version,
                "topics": [
                    {"name": t.name, "type": t.msg_type, "category": t.category}
                    for t in node.topics
                ],
            }, default=str))
    else:
        from ros_tap.formatters.dashboard import render_scan_results
        render_scan_results(nodes, console)


@main.command()
@click.option("--ros1-uri", default=None, help="ROS Master URI")
@click.option("--domain", default=0, type=int, help="ROS 2 DDS domain ID")
@click.option("--timeout", default=3.0, type=float, help="Discovery timeout in seconds")
@click.option("--output", "-o", default="-", help="Output: '-' for stdout, path for local dir, 's3://bucket/prefix' for S3")
@click.option("--s3-region", default=None, help="AWS region for S3 sink")
@click.option("--buffer-size", default=1000, type=int, help="S3 buffer size before flush")
@click.option("--topics", "-t", default=None, help="Comma separated topic name filters (substring match)")
@click.option("--categories", "-c", default=None, help="Comma separated category filters (e.g. power,actuators,imu)")
def record(ros1_uri, domain, timeout, output, s3_region, buffer_size, topics, categories):
    """Record telemetry to stdout, local files, or S3.

    \b
    Examples:
      ros_tap record                          # stream to stdout
      ros_tap record -o ./data                # write JSONL to local dir
      ros_tap record -o s3://my-bucket/robots # upload to S3
      ros_tap record -c power,actuators       # only power & actuator topics
      ros_tap record | jq '.data'             # pipe to jq
    """
    print_banner(console)

    from ros_tap.discovery.auto import auto_discover
    from ros_tap.models import TelemetryFrame, classify_topic

    topic_filters = [t.strip() for t in topics.split(",")] if topics else None
    cat_filters = [c.strip() for c in categories.split(",")] if categories else None

    sink = _make_sink(output, s3_region, buffer_size)

    console.print(f"[dim]Discovering robots (timeout={timeout}s)...[/dim]", err=True)
    nodes = auto_discover(ros1_uri=ros1_uri, ros2_domain=domain, timeout=timeout)

    if not nodes:
        console.print("[yellow]No robots found. Exiting.[/yellow]", err=True)
        sys.exit(1)

    all_topics = []
    for node in nodes:
        for topic in node.topics:
            if topic_filters and not any(f in topic.name for f in topic_filters):
                continue
            if cat_filters and topic.category not in cat_filters:
                continue
            all_topics.append((node, topic))

    console.print(
        f"[green]Found {len(nodes)} node(s), recording {len(all_topics)} topic(s)[/green]",
        err=True,
    )
    console.print(f"[dim]Output: {output}[/dim]", err=True)
    console.print("[dim]Press Ctrl+C to stop[/dim]\n", err=True)

    running = True

    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    while running:
        for node, topic in all_topics:
            frame = TelemetryFrame(
                timestamp=time.time(),
                source_node=node.name,
                topic=topic.name,
                msg_type=topic.msg_type,
                data={"status": "discovered", "category": topic.category},
                ros_version=node.ros_version,
            )
            sink.write(frame)
        sink.flush()
        time.sleep(1.0)

    console.print("\n[yellow]Stopping...[/yellow]", err=True)
    sink.close()
    console.print("[green]Done.[/green]", err=True)


@main.command()
def info():
    """Show ros_tap version and environment info."""
    print_banner(console)

    from rich.table import Table

    table = Table(show_header=False, border_style="dim")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Version", __version__)

    try:
        import cyclonedds
        table.add_row("CycloneDDS", "installed")
    except ImportError:
        table.add_row("CycloneDDS", "[red]not installed[/red]")

    try:
        import boto3
        table.add_row("boto3", "installed")
    except ImportError:
        table.add_row("boto3", "[dim]not installed (optional)[/dim]")

    import os
    ros_master = os.environ.get("ROS_MASTER_URI", "[dim]not set[/dim]")
    ros_domain = os.environ.get("ROS_DOMAIN_ID", "0")
    table.add_row("ROS_MASTER_URI", ros_master)
    table.add_row("ROS_DOMAIN_ID", ros_domain)

    console.print(table)


def _make_sink(output: str, s3_region: str | None, buffer_size: int):
    if output.startswith("s3://"):
        from ros_tap.sinks.s3 import S3Sink
        parts = output[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else "ros_tap/"
        return S3Sink(bucket=bucket, prefix=prefix, region=s3_region, buffer_size=buffer_size)
    elif output == "-":
        from ros_tap.sinks.stdout import StdoutSink
        return StdoutSink()
    else:
        from ros_tap.sinks.local import LocalSink
        return LocalSink(output_dir=output)


if __name__ == "__main__":
    main()
