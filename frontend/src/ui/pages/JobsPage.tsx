import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listJobs, type JobStatus } from '../../api/backendApi';
import ProgressBar from '../components/ProgressBar';

function normalizeJobs(input: Record<string, JobStatus>): JobStatus[] {
  return Object.entries(input).map(([job_id, data]) => ({ ...data, job_id }));
}

export default function JobsPage() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const [jobs, setJobs] = useState<JobStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    if (!baseUrl) {
      setJobs(null);
      setError('Set VITE_API_BASE_URL to your backend URL to load jobs.');
      return;
    }

    setBusy(true);
    try {
      const res = await listJobs();
      setJobs(normalizeJobs(res.jobs));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load jobs');
      setJobs(null);
    } finally {
      setBusy(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      void refresh();
    }, 3000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const sorted = useMemo(() => {
    if (!jobs) return null;
    return [...jobs].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
  }, [jobs]);

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section className="card">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Jobs</h1>
            <div className="muted">Auto-refresh every 3 seconds</div>
          </div>
          <div className="row" style={{ alignItems: 'center' }}>
            <button className="buttonSecondary" onClick={() => void refresh()} disabled={busy}>
              Refresh
            </button>
            <Link className="badge" to="/upload">
              Upload
            </Link>
          </div>
        </div>
      </section>

      {error && (
        <section className="card">
          <div style={{ fontWeight: 800 }}>Error</div>
          <div className="muted" style={{ whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        </section>
      )}

      <section className="card">
        {!sorted ? (
          <div className="muted">No jobs loaded.</div>
        ) : sorted.length === 0 ? (
          <div className="muted">No jobs found.</div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {sorted.map((j) => (
              <div key={j.job_id} className="card" style={{ padding: 12 }}>
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 800 }}>{j.job_id}</div>
                    <div className="muted">status: {j.status}</div>
                  </div>
                  <Link className="badge" to={`/job/${j.job_id}`}>
                    Open
                  </Link>
                </div>
                <div style={{ marginTop: 10 }}>
                  <ProgressBar value={typeof j.progress === 'number' ? j.progress : 0} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
