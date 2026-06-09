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
err = Console(stderr=True)


@click.group()
@click.version_option(__version__, prog_name="ros_tap")
def main():
    """Zero config telemetry tap for any ROS robot on your network.

    \b
    ros_tap discovers ROS 1 and ROS 2 robots automatically,
    subscribes to their topics, and streams telemetry wherever
    you want: terminal, local NPZ files, or S3/R2.

    \b
    No ROS install required. Just a passive listener.
    """


@main.command()
@click.option("--ros1-uri", default=None, help="ROS Master URI (default: $ROS_MASTER_URI or localhost:11311)")
@click.option("--domain", default=0, type=int, help="ROS 2 DDS domain ID")
@click.option("--timeout", default=3.0, type=float, help="Discovery timeout in seconds")
@click.option("--json", "as_json", is_flag=True, help="Output JSON instead of dashboard")
def scan(ros1_uri, domain, timeout, as_json):
    """Scan the network for robots and topics."""
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
@click.option("--output", "-o", default="-", help="'-' for stdout, path for local dir, 's3://bucket/prefix' for S3")
@click.option("--format", "-f", "fmt", default="npz", type=click.Choice(["npz", "jsonl"]), help="Local format (default: npz)")
@click.option("--s3-region", default=None, help="AWS region for S3")
@click.option("--s3-endpoint", default=None, help="Custom S3 endpoint (for R2, MinIO, etc)")
@click.option("--buffer-size", default=1000, type=int, help="S3 buffer size before flush")
@click.option("--flush-interval", default=30.0, type=float, help="NPZ flush interval in seconds")
@click.option("--topics", "-t", default=None, help="Topic name filters, comma separated")
@click.option("--categories", "-c", default=None, help="Category filters, comma separated")
def record(ros1_uri, domain, timeout, output, fmt, s3_region, s3_endpoint, buffer_size, flush_interval, topics, categories):
    """Record telemetry to stdout, local NPZ/JSONL, or S3.

    \b
    Examples:
      ros_tap record                          # stdout as JSONL
      ros_tap record -o ./data                # NPZ to local dir
      ros_tap record -o ./data -f jsonl       # JSONL to local dir
      ros_tap record -o s3://bucket/prefix    # stream to S3
      ros_tap record -c power,actuators       # filter by category
      ros_tap record | jq '.data'             # pipe to jq
    """
    print_banner(err)

    from ros_tap.discovery.auto import auto_discover
    from ros_tap.models import TelemetryFrame

    topic_filters = [t.strip() for t in topics.split(",")] if topics else None
    cat_filters = [c.strip() for c in categories.split(",")] if categories else None

    sink = _make_sink(output, fmt, s3_region, s3_endpoint, buffer_size, flush_interval)

    err.print(f"[dim]Discovering robots (timeout={timeout}s)...[/dim]")
    nodes = auto_discover(ros1_uri=ros1_uri, ros2_domain=domain, timeout=timeout)

    if not nodes:
        err.print("[yellow]No robots found.[/yellow]")
        sys.exit(1)

    matched = []
    for node in nodes:
        for topic in node.topics:
            if topic_filters and not any(f in topic.name for f in topic_filters):
                continue
            if cat_filters and topic.category not in cat_filters:
                continue
            matched.append((node, topic))

    err.print(f"[green]Found {len(nodes)} node(s), recording {len(matched)} topic(s)[/green]")
    err.print(f"[dim]Output: {output} (format: {fmt})[/dim]")
    err.print("[dim]Ctrl+C to stop[/dim]\n")

    running = True

    def on_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, on_sigint)

    while running:
        for node, topic in matched:
            sink.write(TelemetryFrame(
                timestamp=time.time(),
                source_node=node.name,
                topic=topic.name,
                msg_type=topic.msg_type,
                data={"status": "discovered", "category": topic.category},
                ros_version=node.ros_version,
            ))
        sink.flush()
        time.sleep(1.0)

    err.print("\n[yellow]Stopping...[/yellow]")
    sink.close()
    err.print("[green]Done.[/green]")


@main.command()
@click.option("--data-dir", "-d", default="./ros_tap_data", help="Local data directory")
def runs(data_dir):
    """List recorded runs."""
    from ros_tap.loader import list_runs
    from rich.table import Table
    import datetime

    print_banner(console)

    all_runs = list_runs(data_dir)
    if not all_runs:
        console.print(f"[yellow]No runs found in {data_dir}[/yellow]")
        return

    table = Table(title=f"Recorded Runs ({data_dir})", border_style="dim")
    table.add_column("#", style="dim", width=4)
    table.add_column("Run ID", style="cyan")
    table.add_column("Started", style="green")
    table.add_column("Duration")
    table.add_column("Topics", justify="right")
    table.add_column("Directory", style="dim")

    for i, run in enumerate(all_runs):
        started = datetime.datetime.fromtimestamp(run.start).strftime("%Y-%m-%d %H:%M:%S")
        duration = f"{run.duration:.1f}s"
        table.add_row(str(i), run.run_id, started, duration, str(len(run.topics)), run.path.name)

    console.print(table)


@main.command()
@click.argument("run_dir", type=click.Path(exists=True))
@click.option("--bucket", "-b", required=True, help="S3/R2 bucket name")
@click.option("--prefix", "-p", default="ros_tap/", help="Key prefix in bucket")
@click.option("--region", default=None, help="AWS region")
@click.option("--endpoint", default=None, help="Custom S3 endpoint (for R2, MinIO, etc)")
def push(run_dir, bucket, prefix, region, endpoint):
    """Push a local run to S3/R2.

    \b
    Examples:
      ros_tap push ./ros_tap_data/run_20260608_193000_abc -b my-bucket
      ros_tap push ./ros_tap_data/run_20260608_193000_abc -b my-r2-bucket --endpoint https://acct.r2.cloudflarestorage.com
    """
    print_banner(console)

    from ros_tap.loader import Run
    from ros_tap.push import push_run

    run = Run(run_dir)
    console.print(f"[dim]Pushing run {run.run_id} ({len(run.topics)} topics, {run.duration}s)...[/dim]")

    dest = push_run(run, bucket=bucket, prefix=prefix, region=region, endpoint_url=endpoint)

    console.print(f"[green]Pushed to {dest}[/green]")
    console.print(f"[dim]Index updated at s3://{bucket}/{prefix.rstrip('/')}/index.json[/dim]")


@main.command()
def info():
    """Show version and environment."""
    print_banner(console)

    from rich.table import Table
    import os

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
        import numpy as np
        table.add_row("NumPy", np.__version__)
    except ImportError:
        table.add_row("NumPy", "[red]not installed[/red]")

    try:
        import boto3
        table.add_row("boto3", "installed")
    except ImportError:
        table.add_row("boto3", "[dim]not installed (optional)[/dim]")

    table.add_row("ROS_MASTER_URI", os.environ.get("ROS_MASTER_URI", "[dim]not set[/dim]"))
    table.add_row("ROS_DOMAIN_ID", os.environ.get("ROS_DOMAIN_ID", "0"))

    console.print(table)


def _make_sink(output, fmt, s3_region, s3_endpoint, buffer_size, flush_interval):
    if output.startswith("s3://"):
        from ros_tap.sinks.s3 import S3Sink
        parts = output[5:].split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else "ros_tap/"
        return S3Sink(
            bucket=bucket, prefix=prefix,
            region=s3_region, endpoint_url=s3_endpoint,
            buffer_size=buffer_size,
        )
    elif output == "-":
        from ros_tap.sinks.stdout import StdoutSink
        return StdoutSink()
    elif fmt == "npz":
        from ros_tap.sinks.npz import NpzSink
        return NpzSink(output_dir=output, flush_interval=flush_interval)
    else:
        from ros_tap.sinks.local import LocalSink
        return LocalSink(output_dir=output)


if __name__ == "__main__":
    main()
