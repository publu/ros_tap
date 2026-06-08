# ros_tap

**Zero-config telemetry tap for any ROS robot on your network.**

```
 ██████╗  ██████╗ ███████╗    ████████╗ █████╗ ██████╗
 ██╔══██╗██╔═══██╗██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗
 ██████╔╝██║   ██║███████╗       ██║   ███████║██████╔╝
 ██╔══██╗██║   ██║╚════██║       ██║   ██╔══██║██╔═══╝
 ██║  ██║╚██████╔╝███████║       ██║   ██║  ██║██║
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝       ╚═╝   ╚═╝  ╚═╝╚═╝
```

ros_tap discovers ROS 1 and ROS 2 robots on your network, subscribes to their topics, and streams telemetry wherever you want. No ROS install required. It's just a tap — you decide where the data goes.

## Install

```bash
pip install ros_tap          # ROS 2 support (via CycloneDDS)
pip install 'ros_tap[s3]'    # + S3 output
pip install 'ros_tap[all]'   # everything
```

## Usage

### Scan — see what's on the network

```bash
ros_tap scan                         # rich terminal dashboard
ros_tap scan --json                  # machine-readable output
ros_tap scan --domain 42             # specific ROS 2 domain
ros_tap scan --ros1-uri http://robot:11311  # specific ROS 1 master
```

### Record — stream telemetry

```bash
ros_tap record                                # stream to stdout as JSONL
ros_tap record -o ./data                      # write to local directory
ros_tap record -o s3://my-bucket/robots       # upload to S3
ros_tap record -c power,actuators             # filter by category
ros_tap record -t /battery,/joint_states      # filter by topic name
ros_tap record | jq '.data'                   # pipe to anything
ros_tap record -o ./data -c power,imu,lidar   # local, filtered
```

### Info — check your setup

```bash
ros_tap info    # shows installed backends, env vars, version
```

## How it works

- **ROS 2**: Joins the DDS network as a passive participant using CycloneDDS. Discovers all nodes, topics, and types via DDS multicast. No ROS 2 install needed.
- **ROS 1**: Queries the ROS Master's XML-RPC API at `ROS_MASTER_URI`. Gets the full node/topic graph in one call.
- **Auto-detect**: `ros_tap` tries both and merges results. Works in mixed ROS 1 + ROS 2 environments (ros1_bridge).

Adding a subscriber does not interfere with any existing software on the robot. DDS pub/sub is like tuning into a radio station — other listeners and the broadcaster are unaffected.

## Output formats

All sinks write JSONL (one JSON object per line):

```json
{"ts": 1718000000.0, "node": "/turtlebot", "topic": "/battery_state", "type": "sensor_msgs/BatteryState", "ros": 2, "data": {...}}
```

| Sink | Flag | Notes |
|------|------|-------|
| stdout | `-o -` (default) | Pipe to `jq`, `grep`, `curl`, whatever |
| Local | `-o ./path` | Auto-rotating JSONL files (50 MB default) |
| S3 | `-o s3://bucket/prefix` | Buffered uploads, NDJSON content type |

## Auto-detected categories

ros_tap classifies topics into categories for filtering:

| Category | Example topics |
|----------|---------------|
| `power` | `/battery_state`, `/battery` |
| `actuators` | `/joint_states`, `/motor_states` |
| `diagnostics` | `/diagnostics` |
| `odometry` | `/odom` |
| `imu` | `/imu` |
| `lidar` | `/scan` |
| `camera` | `/camera/image_raw` |
| `command` | `/cmd_vel` |
| `thermal` | `/temperature` |
| `system` | `/cpu_monitor`, `/memory_monitor` |

## Why not ros2 doctor?

`ros2 doctor` checks if your ROS 2 *installation* is healthy. ros_tap checks if your *robot* is healthy. Different things entirely.

| | `ros2 doctor` | `ros_tap` |
|---|---|---|
| Checks | ROS 2 install, DDS config, QoS | Live robot telemetry |
| Requires ROS 2 | Yes | No |
| ROS 1 support | No | Yes |
| Output | Text report | JSONL stream |
| Use case | "Is my dev env broken?" | "Is my robot alive?" |

## License

Apache 2.0
