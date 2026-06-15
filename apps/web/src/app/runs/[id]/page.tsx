import { ErrorBanner } from "@/components/ErrorBanner";
import { RunActions } from "@/components/RunActions";
import { RunSummary } from "@/components/RunSummary";
import { Timeline } from "@/components/Timeline";
import type { RunDetail } from "@/lib/trace";

async function fetchRun(id: string): Promise<RunDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/runs/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await fetchRun(id);
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";

  if (!run) {
    return (
      <main>
        <h1>Run not found</h1>
        <p className="muted">
          <a href="/">Back to runs</a>
        </p>
      </main>
    );
  }

  return (
    <main>
      <p className="muted">
        <a href="/">← Back to runs</a>
      </p>
      <h1>{run.agent_name}</h1>
      <p className="muted">
        {run.id} · user {run.user_id ?? "—"} · trace {run.trace_id}
      </p>

      <ErrorBanner run={run} />
      <RunSummary run={run} />
      <RunActions runId={run.id} apiUrl={apiUrl} />

      {(run.model_calls.length > 0 || run.tool_calls.length > 0) && (
        <div className="card">
          <h2>Calls</h2>
          <div className="calls-grid">
            {run.model_calls.map((call) => (
              <div key={call.id} className="call-chip type-llm-call">
                <span className="call-type">llm</span>
                <span>
                  {call.provider}/{call.model}
                </span>
                <span className="muted">
                  {call.latency_ms ?? "—"}ms · {call.input_tokens ?? 0}→{call.output_tokens ?? 0} tok
                </span>
              </div>
            ))}
            {run.tool_calls.map((call) => (
              <div key={call.id} className="call-chip type-tool-call">
                <span className="call-type">tool</span>
                <span>{call.tool_name}</span>
                <span className="muted">{call.latency_ms ?? "—"}ms</span>
                <span className={`status-pill ${call.status === "success" ? "status-ok" : "status-error"}`}>
                  {call.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Timeline</h2>
        <Timeline spans={run.spans} />
      </div>
    </main>
  );
}