type Dashboard = {
  window: number;
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  failure_rate: number;
  policy_violations: number;
  violation_rate: number;
  avg_latency_ms: number | null;
  avg_cost_usd: number | null;
  total_input_tokens: number;
  total_output_tokens: number;
  expensive_agents: Array<{ agent_name: string; total_cost_usd?: number; run_count?: number }>;
  failed_tools: Array<{ tool_name: string; failures: number }>;
  recent_violations: Array<{
    id: string;
    agent_run_id: string;
    agent_name: string;
    policy_name: string;
    action: string;
    severity: string;
    tool_name: string | null;
    message: string;
    created_at: string;
  }>;
};

async function fetchDashboard(): Promise<Dashboard | null> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/dashboard`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default async function DashboardPage() {
  const stats = await fetchDashboard();

  return (
    <main>
      <nav className="site-nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/">Runs</a>
        <a href="/policies">Policies</a>
      </nav>
      <h1>Dashboard</h1>
      <p className="muted">Reliability overview across recent agent runs</p>

      {!stats ? (
        <div className="card">
          <p className="muted">Could not load dashboard. Start the collector and run <code>make demo</code>.</p>
        </div>
      ) : (
        <>
          <div className="summary-grid">
            <div className="summary-card">
              <span className="summary-label">Total runs</span>
              <strong>{stats.total_runs}</strong>
              <span className="muted">last {stats.window}</span>
            </div>
            <div className="summary-card">
              <span className="summary-label">Failure rate</span>
              <strong className={stats.failure_rate > 0 ? "text-error" : ""}>{pct(stats.failure_rate)}</strong>
              <span className="muted">{stats.failed_runs} failed</span>
            </div>
            <div className="summary-card">
              <span className="summary-label">Policy violations</span>
              <strong className={stats.policy_violations > 0 ? "text-error" : ""}>{stats.policy_violations}</strong>
              <span className="muted">{pct(stats.violation_rate)} of runs</span>
            </div>
            <div className="summary-card">
              <span className="summary-label">Avg latency</span>
              <strong>{stats.avg_latency_ms != null ? `${stats.avg_latency_ms} ms` : "—"}</strong>
            </div>
            <div className="summary-card">
              <span className="summary-label">Avg cost</span>
              <strong>{stats.avg_cost_usd != null ? `$${stats.avg_cost_usd}` : "—"}</strong>
            </div>
            <div className="summary-card">
              <span className="summary-label">Tokens</span>
              <strong>{stats.total_input_tokens + stats.total_output_tokens}</strong>
              <span className="muted">
                {stats.total_input_tokens} in / {stats.total_output_tokens} out
              </span>
            </div>
          </div>

          <div className="card">
            <h2>Most expensive agents</h2>
            {stats.expensive_agents.length === 0 ? (
              <p className="muted">No agent cost data yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Metric</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.expensive_agents.map((agent) => (
                    <tr key={agent.agent_name}>
                      <td>{agent.agent_name}</td>
                      <td>
                        {agent.total_cost_usd != null
                          ? `$${agent.total_cost_usd}`
                          : `${agent.run_count ?? 0} runs`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Failed tools</h2>
            {stats.failed_tools.length === 0 ? (
              <p className="muted">No tool failures recorded.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th>Failures</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.failed_tools.map((tool) => (
                    <tr key={tool.tool_name}>
                      <td>{tool.tool_name}</td>
                      <td>{tool.failures}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Recent policy violations</h2>
            {stats.recent_violations.length === 0 ? (
              <p className="muted">No violations detected.</p>
            ) : (
              <ul className="violation-list">
                {stats.recent_violations.map((v) => (
                  <li key={v.id} className="violation-item">
                    <div className="violation-header">
                      <span className={`action-pill action-${v.action}`}>{v.action}</span>
                      <span className={`severity-pill severity-${v.severity}`}>{v.severity}</span>
                      <strong>{v.policy_name}</strong>
                      <span className="muted">{v.agent_name}</span>
                    </div>
                    <p className="muted">{v.message}</p>
                    <p className="muted">
                      <a href={`/runs/${v.agent_run_id}`}>View run</a> · {formatWhen(v.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </main>
  );
}