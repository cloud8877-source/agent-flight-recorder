type Span = {
  id: string;
  span_type: string;
  name: string;
  status: string;
  started_at: string;
  attributes: Record<string, unknown>;
};

type RunDetail = {
  id: string;
  trace_id: string;
  agent_name: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  spans: Span[];
};

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
        {run.id} · {run.status} · trace {run.trace_id}
      </p>

      <div className="card">
        <h2>Timeline</h2>
        {run.spans.length === 0 ? (
          <p className="muted">No spans recorded.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Name</th>
                <th>Status</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {run.spans.map((span) => (
                <tr key={span.id}>
                  <td>{span.span_type}</td>
                  <td>{span.name}</td>
                  <td>{span.status}</td>
                  <td>{span.started_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}