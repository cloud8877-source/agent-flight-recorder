type Policy = {
  id: string;
  name: string;
  description: string | null;
  enabled: number;
  created_at: string;
};

type ViolationRow = {
  id: string;
  agent_run_id: string;
  agent_name: string;
  policy_name: string;
  action: string;
  severity: string;
  tool_name: string | null;
  message: string;
  created_at: string;
};

async function fetchPolicies(): Promise<Policy[]> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/policies`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

async function fetchViolations(): Promise<ViolationRow[]> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/violations?limit=25`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function PoliciesPage() {
  const [policies, violations] = await Promise.all([fetchPolicies(), fetchViolations()]);

  return (
    <main>
      <nav className="site-nav">
        <a href="/">Runs</a>
        <a href="/policies">Policies</a>
      </nav>
      <h1>Policies</h1>
      <p className="muted">Active policy definitions and recent violations.</p>

      <div className="card">
        <h2>Active policies</h2>
        {policies.length === 0 ? (
          <p className="muted">No policies loaded. Seed from examples/policies on collector startup.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((policy) => (
                <tr key={policy.id}>
                  <td>
                    <code>{policy.name}</code>
                  </td>
                  <td>{policy.description ?? "—"}</td>
                  <td>{policy.enabled ? "enabled" : "disabled"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Recent violations</h2>
        {violations.length === 0 ? (
          <p className="muted">No policy violations recorded yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Policy</th>
                <th>Action</th>
                <th>Agent run</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {violations.map((row) => (
                <tr key={row.id}>
                  <td>
                    <span className={`severity-pill severity-${row.severity}`}>{row.severity}</span>
                  </td>
                  <td>{row.policy_name}</td>
                  <td>
                    <span className={`action-pill action-${row.action}`}>{row.action}</span>
                  </td>
                  <td>
                    <a href={`/runs/${row.agent_run_id}`}>{row.agent_name}</a>
                  </td>
                  <td>{row.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}