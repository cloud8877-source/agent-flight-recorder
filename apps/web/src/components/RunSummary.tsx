import { formatDuration, runDuration, statusClass, type RunDetail } from "@/lib/trace";

export function RunSummary({ run }: { run: RunDetail }) {
  const duration = runDuration(run);
  const errorSpans = run.spans.filter((s) => s.status === "error").length;
  const totalTokens = run.model_calls.reduce(
    (sum, call) => sum + (call.input_tokens ?? 0) + (call.output_tokens ?? 0),
    0,
  );

  return (
    <div className="summary-grid">
      <div className="summary-card">
        <span className="summary-label">Status</span>
        <span className={`status-pill ${statusClass(run.status)}`}>{run.status}</span>
      </div>
      <div className="summary-card">
        <span className="summary-label">Duration</span>
        <strong>{formatDuration(duration)}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Spans</span>
        <strong>{run.spans.length}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Model calls</span>
        <strong>{run.model_calls.length}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Tool calls</span>
        <strong>{run.tool_calls.length}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Tokens</span>
        <strong>{totalTokens || "—"}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Errors</span>
        <strong className={errorSpans > 0 ? "text-error" : ""}>{errorSpans}</strong>
      </div>
      <div className="summary-card">
        <span className="summary-label">Environment</span>
        <strong>{run.environment}</strong>
      </div>
    </div>
  );
}