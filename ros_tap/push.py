"""Push local NPZ runs to S3/R2 with a top level index."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ros_tap.loader import Run, list_runs


def push_run(
    run: Run,
    bucket: str,
    prefix: str = "ros_tap/",
    region: str | None = None,
    endpoint_url: str | None = None,
) -> str:
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 not installed. Install with: pip install 'ros_tap[s3]'")

    kwargs = {}
    if region:
        kwargs["region_name"] = region
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    s3 = boto3.client("s3", **kwargs)

    prefix = prefix.rstrip("/") + "/"
    run_prefix = f"{prefix}runs/{run.path.name}/"

    for filepath in sorted(run.path.iterdir()):
        if filepath.is_file():
            key = f"{run_prefix}{filepath.name}"
            content_type = "application/json" if filepath.suffix == ".json" else "application/octet-stream"
            s3.upload_file(
                str(filepath),
                bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )

    _update_index(s3, bucket, prefix, run)

    return f"s3://{bucket}/{run_prefix}"


def _update_index(s3, bucket: str, prefix: str, run: Run):
    index_key = f"{prefix}index.json"

    try:
        resp = s3.get_object(Bucket=bucket, Key=index_key)
        index = json.loads(resp["Body"].read())
    except s3.exceptions.NoSuchKey:
        index = {"runs": [], "updated": None}
    except Exception:
        index = {"runs": [], "updated": None}

    existing_ids = {r["run_id"] for r in index["runs"]}
    if run.run_id not in existing_ids:
        index["runs"].append({
            "run_id": run.run_id,
            "dir": run.path.name,
            "start": run.start,
            "end": run.end,
            "duration_s": run.duration,
            "topics": list(run.manifest["topics"].keys()),
            "total_samples": sum(
                t["total_samples"] for t in run.manifest["topics"].values()
            ),
        })

    index["runs"].sort(key=lambda r: r["start"])
    index["updated"] = time.time()

    s3.put_object(
        Bucket=bucket,
        Key=index_key,
        Body=json.dumps(index, indent=2, default=str).encode("utf-8"),
        ContentType="application/json",
    )
