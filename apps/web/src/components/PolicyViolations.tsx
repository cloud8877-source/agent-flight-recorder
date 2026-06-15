import type { PolicyViolation, RunDetail } from "@/lib/trace";

function severityClass(severity: string): string {
  if (severity === "critical" || severity === "high") return "severity-high";
  if (severity === "medium") return "severity-medium";
  return "severity-low";
}

function ViolationList({ violations }: { violations: PolicyViolation[] }) {
  return (
    <ul className="violation-list">
      {violations.map((violation) => (
        <li key={violation.id} className={`violation-item ${severityClass(violation.severity)}`}>
          <div className="violation-header">
            <span className={`action-pill action-${violation.action}`}>{violation.action}</span>
            <strong>{violation.policy_name}</strong>
            {violation.tool_name && <span className="muted">· {violation.tool_name}</span>}
          </div>
          <p>{violation.message}</p>
          {violation.rule_name && <p className="muted">rule: {violation.rule_name}</p>}
        </li>
      ))}
    </ul>
  );
}

export function PolicyViolations({ run }: { run: RunDetail }) {
  const violations = run.policy_violations ?? [];
  if (violations.length === 0) return null;

  return (
    <div className="policy-banner">
      <strong>Policy violations ({violations.length})</strong>
      <ViolationList violations={violations} />
    </div>
  );
}