from __future__ import annotations

from collector.exporters.otlp_forward import forward_otlp_traces
from collector.exporters.targets import export_targets

__all__ = ["forward_otlp_traces", "export_targets"]