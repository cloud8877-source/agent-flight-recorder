import {
  flattenTimeline,
  buildTimeline,
  formatDuration,
  spanTypeLabel,
  statusClass,
  type Span,
  type TimelineNode,
} from "@/lib/trace";

function AttributeList({ attributes }: { attributes: Record<string, unknown> }) {
  const entries = Object.entries(attributes).filter(([key]) => !key.startsWith("afr."));
  if (entries.length === 0) return null;

  return (
    <dl className="attr-list">
      {entries.slice(0, 6).map(([key, value]) => (
        <div key={key} className="attr-row">
          <dt>{key}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function TimelineItem({ node }: { node: TimelineNode }) {
  return (
    <div className="timeline-item" style={{ marginLeft: `${node.depth * 1.25}rem` }}>
      <div className="timeline-marker" data-type={node.span_type} />
      <div className="timeline-card">
        <div className="timeline-header">
          <span className={`type-badge type-${node.span_type.replace(".", "-")}`}>
            {spanTypeLabel(node.span_type)}
          </span>
          <strong>{node.name}</strong>
          <span className={`status-pill ${statusClass(node.status)}`}>{node.status}</span>
          <span className="timeline-duration">{formatDuration(node.duration_ms)}</span>
        </div>
        <div className="timeline-meta muted">
          {node.started_at}
          {node.ended_at ? ` → ${node.ended_at}` : ""}
        </div>
        <AttributeList attributes={node.attributes} />
      </div>
    </div>
  );
}

export function Timeline({ spans }: { spans: Span[] }) {
  const roots = buildTimeline(spans);
  const items = flattenTimeline(roots);

  if (items.length === 0) {
    return <p className="muted">No spans recorded.</p>;
  }

  return (
    <div className="timeline">
      {items.map((node) => (
        <TimelineItem key={node.id} node={node} />
      ))}
    </div>
  );
}