type AgentRun = {
  id: string;
  trace_id: string;
  agent_name: string;
  user_id: string | null;
  environment: string;
  status: string;
  started_at: string;
};

async function fetchRuns(): Promise<AgentRun[]> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/runs`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const runs = await fetchRuns();

  return (
    <main>
      <h1>Agent Flight Recorder</h1>
      <p className="muted">Phase 1 trace viewer — local development</p>

      <div className="card">
        <h2>Recent agent runs</h2>
        {runs.length === 0 ? (
          <p className="muted">
            No runs yet. Start the collector and run the support-refund-agent example.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Status</th>
                <th>User</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.agent_name}</td>
                  <td>{run.status}</td>
                  <td>{run.user_id ?? "—"}</td>
                  <td>{run.started_at}</td>
                  <td>
                    <a href={`/runs/${run.id}`}>View</a>
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