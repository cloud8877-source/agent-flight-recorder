"use client";

import { useState } from "react";

export function RunActions({ runId, apiUrl }: { runId: string; apiUrl: string }) {
  const [replayId, setReplayId] = useState<string | null>(null);
  const [evalResult, setEvalResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function startReplay() {
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/v1/replays`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_agent_run_id: runId, mode: "exact" }),
      });
      const data = await res.json();
      setReplayId(data.id);
    } finally {
      setBusy(false);
    }
  }

  async function runEval() {
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/v1/evals/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_run_id: runId }),
      });
      const data = await res.json();
      setEvalResult(data.passed ? `passed (score ${data.score})` : `failed: ${data.failures?.join(", ")}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="actions-row">
      <button type="button" onClick={startReplay} disabled={busy}>
        Replay (exact)
      </button>
      <button type="button" onClick={runEval} disabled={busy}>
        Run eval
      </button>
      <a href={`${apiUrl}/v1/runs/${runId}/regression-test`} download={`${runId}-regression.yml`}>
        Create regression test
      </a>
      {replayId && (
        <a href={`/replays/${replayId}`} className="action-result">
          View replay {replayId}
        </a>
      )}
      {evalResult && <span className="action-result muted">{evalResult}</span>}
    </div>
  );
}