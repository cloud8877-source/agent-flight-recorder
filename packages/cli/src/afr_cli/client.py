from __future__ import annotations

import os
from typing import Any

import httpx


class AFRClient:
    def __init__(self, endpoint: str | None = None, timeout: float = 30.0) -> None:
        self.endpoint = (endpoint or os.environ.get("AFR_ENDPOINT", "http://127.0.0.1:4318")).rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def list_runs(self, **params: Any) -> list[dict[str, Any]]:
        return self._get("/v1/runs", params=params)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._get(f"/v1/runs/{run_id}")

    def create_replay(
        self,
        run_id: str,
        *,
        mode: str = "exact",
        model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"source_agent_run_id": run_id, "mode": mode}
        if model:
            payload["model"] = model
        return self._post("/v1/replays", payload)

    def run_eval(self, run_id: str, eval_yaml: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"agent_run_id": run_id}
        if eval_yaml:
            payload["eval_yaml"] = eval_yaml
        return self._post("/v1/evals/run", payload)

    def list_policies(self) -> list[dict[str, Any]]:
        return self._get("/v1/policies")

    def load_policy(self, policy_yaml: str) -> dict[str, Any]:
        return self._post("/v1/policies", {"policy_yaml": policy_yaml})

    def policy_check(self, run_id: str) -> dict[str, Any]:
        return self._post(f"/v1/runs/{run_id}/policy-check", {})

    def list_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._get("/v1/violations", params={"limit": limit})

    def get_violations(self, run_id: str) -> list[dict[str, Any]]:
        return self._get(f"/v1/runs/{run_id}/violations")

    def regression_yaml(self, run_id: str) -> str:
        response = httpx.get(
            f"{self.endpoint}/v1/runs/{run_id}/regression-test",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = httpx.get(f"{self.endpoint}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        response = httpx.post(
            f"{self.endpoint}{path}",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()