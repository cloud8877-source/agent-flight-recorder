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

function formatWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default async function HomePage() {
  const runs = await fetchRuns();

  return (
    <main>
      <h1>Agent Flight Recorder</h1>
      <p className="muted">OpenTelemetry-native trace viewer — Phase 1</p>

      <div className="card">
        <h2>Recent agent runs</h2>
        {runs.length === 0 ? (
          <p className="muted">
            No runs yet. Start the collector and run{" "}
            <code>make demo</code>.
          </p>
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
                <tr key={run.id}>
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