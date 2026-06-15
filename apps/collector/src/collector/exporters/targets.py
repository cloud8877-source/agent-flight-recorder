from __future__ import annotations

from collector.exporters.otlp_forward import _targets


def export_targets() -> list[dict[str, str]]:
    return [{"name": target["name"], "endpoint": target["endpoint"]} for target in _targets()]