export type Span = {
  id: string;
  span_id: string;
  parent_span_id: string | null;
  span_type: string;
  name: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  attributes: Record<string, unknown>;
};

export type ModelCall = {
  id: string;
  provider: string;
  model: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
};

export type ToolCall = {
  id: string;
  tool_name: string;
  status: string;
  latency_ms: number | null;
};

export type RunDetail = {
  id: string;
  trace_id: string;
  agent_name: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  user_id: string | null;
  environment: string;
  spans: Span[];
  model_calls: ModelCall[];
  tool_calls: ToolCall[];
};

export function parseTime(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}

export function formatDuration(ms: number | null): string {
  if (ms === null || ms < 0) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function spanDuration(span: Span): number | null {
  const start = parseTime(span.started_at);
  const end = parseTime(span.ended_at);
  if (start === null || end === null) return null;
  return end - start;
}

export function runDuration(run: RunDetail): number | null {
  const start = parseTime(run.started_at);
  const end = parseTime(run.ended_at);
  if (start === null || end === null) return null;
  return end - start;
}

export type TimelineNode = Span & {
  depth: number;
  duration_ms: number | null;
  children: TimelineNode[];
};

export function buildTimeline(spans: Span[]): TimelineNode[] {
  const nodes = new Map<string, TimelineNode>();
  for (const span of spans) {
    nodes.set(span.span_id, {
      ...span,
      depth: 0,
      duration_ms: spanDuration(span),
      children: [],
    });
  }

  const roots: TimelineNode[] = [];
  for (const node of nodes.values()) {
    const parentId = node.parent_span_id;
    const parent = parentId ? nodes.get(parentId) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  const assignDepth = (node: TimelineNode, depth: number) => {
    node.depth = depth;
    for (const child of node.children) assignDepth(child, depth + 1);
  };
  for (const root of roots) assignDepth(root, 0);

  const sortTree = (node: TimelineNode) => {
    node.children.sort((a, b) => (parseTime(a.started_at) ?? 0) - (parseTime(b.started_at) ?? 0));
    node.children.forEach(sortTree);
  };
  roots.sort((a, b) => (parseTime(a.started_at) ?? 0) - (parseTime(b.started_at) ?? 0));
  roots.forEach(sortTree);

  return roots;
}

export function flattenTimeline(nodes: TimelineNode[]): TimelineNode[] {
  const out: TimelineNode[] = [];
  const walk = (node: TimelineNode) => {
    out.push(node);
    node.children.forEach(walk);
  };
  nodes.forEach(walk);
  return out;
}

export function spanTypeLabel(spanType: string): string {
  return spanType.replace(".", " ");
}

export function statusClass(status: string): string {
  if (status === "error" || status === "failed") return "status-error";
  if (status === "running") return "status-running";
  return "status-ok";
}