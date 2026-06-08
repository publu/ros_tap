from rich.console import Console
from rich.text import Text

BANNER = r"""
 ┌─────────────────────────────────────────────────────┐
 │                                                     │
 │   ██████╗  ██████╗ ███████╗    ████████╗ █████╗ ██████╗  │
 │   ██╔══██╗██╔═══██╗██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗ │
 │   ██████╔╝██║   ██║███████╗       ██║   ███████║██████╔╝ │
 │   ██╔══██╗██║   ██║╚════██║       ██║   ██╔══██║██╔═══╝  │
 │   ██║  ██║╚██████╔╝███████║       ██║   ██║  ██║██║      │
 │   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝       ╚═╝   ╚═╝  ╚═╝╚═╝      │
 │                                                     │
 │   zero-config telemetry tap for any ROS robot       │
 │                                                     │
 └─────────────────────────────────────────────────────┘
"""


def print_banner(console: Console | None = None):
    c = console or Console()
    text = Text(BANNER)
    text.stylize("bold cyan")
    c.print(text)
