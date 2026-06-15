import { Timeline } from "@/components/Timeline";
import type { Span } from "@/lib/trace";

type ReplayDetail = {
  id: string;
  source_agent_run_id: string;
  mode: string;
  status: string;
  result?: { spans?: Span[]; identical?: boolean };
  snapshot?: { spans?: Span[] };
};

async function fetchReplay(id: string): Promise<ReplayDetail | null> {
  const apiUrl = process.env.NEXT_PUBLIC_AFR_API_URL ?? "http://localhost:4318";
  try {
    const res = await fetch(`${apiUrl}/v1/replays/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ReplayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const replay = await fetchReplay(id);

  if (!replay) {
    return (
      <main>
        <h1>Replay not found</h1>
        <p className="muted">
          <a href="/">Back to runs</a>
        </p>
      </main>
    );
  }

  const spans = replay.result?.spans ?? replay.snapshot?.spans ?? [];

  return (
    <main>
      <p className="muted">
        <a href={`/runs/${replay.source_agent_run_id}`}>← Back to source run</a>
      </p>
      <h1>Replay {replay.id}</h1>
      <p className="muted">
        mode {replay.mode} · status {replay.status}
        {replay.result?.identical ? " · identical to source" : ""}
      </p>

      <div className="card">
        <h2>Replay timeline</h2>
        <Timeline spans={spans} />
      </div>
    </main>
  );
}