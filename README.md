# ros_tap

**Zero config telemetry tap for any ROS robot on your network.**

```
  ██████╗  ██████╗ ███████╗ ████████╗ █████╗ ██████╗
  ██╔══██╗██╔═══██╗██╔════╝ ╚══██╔══╝██╔══██╗██╔══██╗
  ██████╔╝██║   ██║███████╗    ██║   ███████║██████╔╝
  ██╔══██╗██║   ██║╚════██║    ██║   ██╔══██║██╔═══╝
  ██║  ██║╚██████╔╝███████║    ██║   ██║  ██║██║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝   ╚═╝  ╚═╝╚═╝
```

ros_tap discovers ROS 1 and ROS 2 robots on your network, subscribes to their topics, and streams telemetry wherever you want. No ROS install required. It's just a tap. You decide where the data goes.

## Install

```bash
pip install ros_tap          # core (CycloneDDS + NumPy)
pip install 'ros_tap[s3]'    # + S3/R2 support
pip install 'ros_tap[all]'   # everything
```

## Commands

### scan

See what's on the network.

```bash
ros_tap scan                                  # terminal dashboard
ros_tap scan --json                           # machine readable
ros_tap scan --domain 42                      # specific DDS domain
ros_tap scan --ros1-uri http://robot:11311    # specific ROS 1 master
```

### record

Stream telemetry to stdout, local NPZ files, or S3.

```bash
ros_tap record                          # stdout as JSONL
ros_tap record -o ./data                # NPZ to local dir (default)
ros_tap record -o ./data -f jsonl       # JSONL instead
ros_tap record -o s3://bucket/prefix    # stream to S3
ros_tap record -c power,actuators       # filter by category
ros_tap record -t /imu,/battery         # filter by topic
ros_tap record | jq '.data'             # pipe to anything
```

### runs

List recorded runs.

```bash
ros_tap runs                    # list all runs in ./ros_tap_data
ros_tap runs -d /path/to/data   # custom directory
```

### push

Upload a local run to S3 or Cloudflare R2.

```bash
ros_tap push ./ros_tap_data/run_20260608_abc -b my-bucket
ros_tap push ./ros_tap_data/run_20260608_abc -b my-bucket --endpoint https://acct.r2.cloudflarestorage.com
```

Each push updates an `index.json` in the bucket with all runs, their time ranges, topics, and sample counts.

```
s3://my-bucket/ros_tap/
  index.json
  runs/
    run_20260608_193000_a1b2c3/
      manifest.json
      imu_data_0000.npz
      joint_states_0000.npz
    run_20260608_200000_d4e5f6/
      manifest.json
      ...
```

### info

Check installed backends and environment.

```bash
ros_tap info
```

## Storage formats

### NPZ (default for local recording)

Compressed NumPy archives. Each session creates a run directory with per topic `.npz` files and a `manifest.json`. Dramatically smaller than JSONL for numeric sensors.

Load a run in Python:

```python
from ros_tap.loader import Run, list_runs

runs = list_runs("./ros_tap_data")
run = runs[-1]

imu = run.load("/imu")
print(imu["timestamps"].shape)
print(imu["linear_acceleration.x"])
```

### JSONL

Use `--format jsonl` or pipe to stdout:

```json
{"ts": 1718000000.0, "node": "/bot", "topic": "/battery_state", "type": "sensor_msgs/BatteryState", "ros": 2, "data": {...}}
```

## How it works

**ROS 2:** Joins the DDS network as a passive participant via CycloneDDS. Discovers nodes, topics, and types through multicast. No ROS 2 install needed.

**ROS 1:** Queries the ROS Master's XML RPC API. Gets the full topic graph in one call.

**Auto detect:** Tries both and merges results. Works with ros1_bridge setups.

Read only. Never publishes. Does not interfere with existing software on the robot.

## Auto detected categories

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
| `navigation` | `/gps`, `/gnss` |
| `force_torque` | `/force`, `/torque` |
| `system` | `/cpu_monitor`, `/memory_monitor` |

## License

Apache 2.0
