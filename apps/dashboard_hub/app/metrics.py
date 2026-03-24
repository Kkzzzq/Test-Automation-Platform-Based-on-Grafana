from __future__ import annotations

import re

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


REQUEST_COUNT = Counter(
    "dashboard_hub_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "dashboard_hub_request_latency_seconds",
    "HTTP latency",
    ["method", "path"],
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_INT_RE = re.compile(r"^\d+$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]{16,}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{12,}$")


def normalize_metrics_path(request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path

    path = request.url.path
    parts = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue

        if _INT_RE.fullmatch(segment):
            parts.append("{id}")
        elif _UUID_RE.fullmatch(segment):
            parts.append("{uuid}")
        elif _HEX_RE.fullmatch(segment):
            parts.append("{hex}")
        elif _TOKEN_RE.fullmatch(segment):
            parts.append("{token}")
        else:
            parts.append(segment)

    return "/" + "/".join(parts) if parts else "/"


def metrics_response():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
