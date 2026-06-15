from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


def _targets() -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    primary = os.environ.get("AFR_OTLP_EXPORT_ENDPOINT")
    if primary:
        targets.append({"name": "otlp", "endpoint": primary.rstrip("/")})

    langfuse_host = os.environ.get("LANGFUSE_HOST")
    langfuse_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    langfuse_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if langfuse_host and langfuse_key and langfuse_secret:
        targets.append(
            {
                "name": "langfuse",
                "endpoint": f"{langfuse_host.rstrip('/')}/api/public/otel/v1/traces",
                "public_key": langfuse_key,
                "secret_key": langfuse_secret,
            }
        )

    phoenix_endpoint = os.environ.get("PHOENIX_OTLP_ENDPOINT")
    if phoenix_endpoint:
        targets.append({"name": "phoenix", "endpoint": phoenix_endpoint.rstrip("/")})

    return targets


async def _forward_to_target(target: dict[str, str], body: bytes, content_type: str) -> dict[str, Any]:
    headers = {"Content-Type": content_type}
    if target.get("public_key") and target.get("secret_key"):
        import base64

        token = base64.b64encode(
            f"{target['public_key']}:{target['secret_key']}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(target["endpoint"], content=body, headers=headers)
        response.raise_for_status()
    return {"name": target["name"], "status": response.status_code}


async def forward_otlp_traces(body: bytes, content_type: str = "application/x-protobuf") -> list[dict[str, Any]]:
    targets = _targets()
    if not targets or not body:
        return []

    results: list[dict[str, Any]] = []
    for target in targets:
        try:
            results.append(await _forward_to_target(target, body, content_type))
        except Exception as exc:
            results.append({"name": target["name"], "error": str(exc)})
    return results


def forward_otlp_traces_background(body: bytes, content_type: str = "application/x-protobuf") -> None:
    if not _targets() or not body:
        return
    asyncio.create_task(forward_otlp_traces(body, content_type))