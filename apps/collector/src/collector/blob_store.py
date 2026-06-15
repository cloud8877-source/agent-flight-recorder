from __future__ import annotations

import json
import os
import uuid
from typing import Any

BLOB_PREFIXES = ("llm.prompt", "llm.response", "llm.system_prompt", "tool.arguments.", "tool.result.")
BLOB_THRESHOLD_BYTES = int(os.environ.get("AFR_BLOB_THRESHOLD_BYTES", "4096"))


def _enabled() -> bool:
    return bool(os.environ.get("AFR_OBJECT_STORAGE_ENDPOINT"))


def _client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("AFR_OBJECT_STORAGE_ENDPOINT"),
        aws_access_key_id=os.environ.get("AFR_OBJECT_STORAGE_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("AFR_OBJECT_STORAGE_SECRET_KEY", "minioadmin"),
        region_name=os.environ.get("AFR_OBJECT_STORAGE_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return os.environ.get("AFR_OBJECT_STORAGE_BUCKET", "afr-payloads")


def offload_large_attributes(
    agent_run_id: str,
    span_id: str,
    attributes: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    if not _enabled():
        return attributes, {}

    trimmed = dict(attributes)
    blob_refs: dict[str, str] = {}

    for key, value in list(attributes.items()):
        if not isinstance(value, str):
            continue
        if not (key in {"llm.prompt", "llm.response", "llm.system_prompt"} or key.startswith(BLOB_PREFIXES)):
            continue
        if len(value.encode("utf-8")) < BLOB_THRESHOLD_BYTES:
            continue

        object_key = f"runs/{agent_run_id}/spans/{span_id}/{key.replace('.', '_')}/{uuid.uuid4().hex}.txt"
        client = _client()
        client.put_object(
            Bucket=_bucket(),
            Key=object_key,
            Body=value.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        blob_refs[key] = object_key
        trimmed[key] = f"s3://{_bucket()}/{object_key}"
        trimmed[f"afr.blob.{key}"] = object_key

    return trimmed, blob_refs


def store_snapshot_blob(agent_run_id: str, snapshot: dict[str, Any]) -> str | None:
    if not _enabled():
        return None

    payload = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
    if len(payload) < BLOB_THRESHOLD_BYTES:
        return None

    object_key = f"runs/{agent_run_id}/snapshots/{uuid.uuid4().hex}.json"
    client = _client()
    client.put_object(
        Bucket=_bucket(),
        Key=object_key,
        Body=payload,
        ContentType="application/json",
    )
    return object_key