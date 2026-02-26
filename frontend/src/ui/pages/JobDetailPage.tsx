import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getDownloadUrl, getStatus, listFiles, type FilesListResponse, type JobStatus } from '../../api/backendApi';
import ProgressBar from '../components/ProgressBar';

export default function JobDetailPage() {
  const { jobId } = useParams();
  const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [files, setFiles] = useState<FilesListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    if (!jobId) {
      setError('job_id is missing');
      return;
    }
    if (!baseUrl) {
      setError('Set VITE_API_BASE_URL to your backend URL to use job details.');
      return;
    }

    try {
      const s = await getStatus(jobId);
      setStatus(s);
      try {
        const f = await listFiles(jobId);
        setFiles(f);
      } catch {
        setFiles(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load job');
      setStatus(null);
      setFiles(null);
    }
  }, [baseUrl, jobId]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const progress = typeof status?.progress === 'number' ? status!.progress! : 0;
  const jobIdString = jobId ?? '';

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section className="card">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Job</h1>
            <div className="muted">{jobId}</div>
          </div>
          <div className="row" style={{ alignItems: 'center' }}>
            <Link className="badge" to="/jobs">
              Jobs
            </Link>
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
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 800 }}>Status</div>
            <div className="muted">{status?.status ?? 'unknown'}</div>
          </div>
          <button className="buttonSecondary" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
        <div style={{ marginTop: 10 }}>
          <ProgressBar value={progress} />
        </div>
      </section>

      <section className="card">
        <h2>Downloads</h2>
        {!baseUrl ? (
          <div className="muted">Set VITE_API_BASE_URL first.</div>
        ) : (
          <div className="row" style={{ alignItems: 'center' }}>
            <a className="badge" href={getDownloadUrl(`/api/v1/nifti/${encodeURIComponent(jobIdString)}/kidney_left`)}>
              NIfTI kidney_left
            </a>
            <a className="badge" href={getDownloadUrl(`/api/v1/nifti/${encodeURIComponent(jobIdString)}/kidney_right`)}>
              NIfTI kidney_right
            </a>
            <a className="badge" href={getDownloadUrl(`/api/v1/stl/${encodeURIComponent(jobIdString)}/kidney_left`)}>
              STL kidney_left
            </a>
            <a className="badge" href={getDownloadUrl(`/api/v1/stl/${encodeURIComponent(jobIdString)}/kidney_right`)}>
              STL kidney_right
            </a>
            <a className="badge" href={getDownloadUrl(`/api/v1/download/${encodeURIComponent(jobIdString)}/all`)}>
              Download all
            </a>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Files</h2>
        {!files ? (
          <div className="muted">No files info (not ready yet or endpoint returned error).</div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {Object.values(files.files).map((f) => (
              <div key={f.path} className="card" style={{ padding: 10 }}>
                <div style={{ fontWeight: 700 }}>{f.path}</div>
                <div className="muted">{f.size_mb} MB</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
