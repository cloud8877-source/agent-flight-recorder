import { statusClass } from "@/lib/trace";

type AgentRun = {
  id: string;
  trace_id: string;
  agent_name: string;
  user_id: string | null;
  environment: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  metrics?: { cost_usd?: number; latency_ms?: number };
};

async function fetchRuns(params: {
  user_id?: string;
  trace_id?: string;
  status?: string;
}): Promise<AgentRun[]> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  const qs = new URLSearchParams();
  if (params.user_id) qs.set("user_id", params.user_id);
  if (params.trace_id) qs.set("trace_id", params.trace_id);
  if (params.status) qs.set("status", params.status);

  try {
    const res = await fetch(`${apiUrl}/v1/runs?${qs.toString()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ user_id?: string; trace_id?: string; status?: string }>;
}) {
  const params = await searchParams;
  const runs = await fetchRuns(params);

  return (
    <main>
      <h1>Agent Flight Recorder</h1>
      <p className="muted">Phase 1 complete — trace, replay stub, eval stub, regression export</p>

      <div className="card">
        <h2>Search runs</h2>
        <form className="search-form" method="get">
          <input name="user_id" placeholder="user_id" defaultValue={params.user_id ?? ""} />
          <input name="trace_id" placeholder="trace_id" defaultValue={params.trace_id ?? ""} />
          <select name="status" defaultValue={params.status ?? ""}>
            <option value="">any status</option>
            <option value="success">success</option>
            <option value="failed">failed</option>
            <option value="running">running</option>
          </select>
          <button type="submit">Search</button>
        </form>
      </div>

      <div className="card">
        <h2>Recent agent runs</h2>
        {runs.length === 0 ? (
          <p className="muted">No runs found. Start the collector and run <code>make demo</code>.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Status</th>
                <th>Env</th>
                <th>User</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className={run.status === "failed" ? "row-failed" : ""}>
                  <td>{run.agent_name}</td>
                  <td>
                    <span className={`status-pill ${statusClass(run.status)}`}>{run.status}</span>
                  </td>
                  <td>{run.environment}</td>
                  <td>{run.user_id ?? "—"}</td>
                  <td>{formatWhen(run.started_at)}</td>
                  <td>
                    <a href={`/runs/${run.id}`}>View trace</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}