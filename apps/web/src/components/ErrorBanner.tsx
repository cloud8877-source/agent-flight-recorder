import { collectErrors, type RunDetail } from "@/lib/trace";

export function ErrorBanner({ run }: { run: RunDetail }) {
  const errors = collectErrors(run.spans);
  if (run.status !== "failed" && errors.length === 0) return null;

  return (
    <div className="error-banner">
      <strong>Run failed or contains errors</strong>
      {errors.length > 0 ? (
        <ul>
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">Check span timeline for error details.</p>
      )}
    </div>
  );
}