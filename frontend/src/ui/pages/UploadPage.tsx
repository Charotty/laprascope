import { useMemo, useState } from 'react';
import { uploadDicomZip, uploadNifti, type UploadResponse } from '../../api/backendApi';
import FileUpload from '../components/FileUpload';
import { Link } from 'react-router-dom';

type Mode = 'dicom_zip' | 'nifti';

export default function UploadPage() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const [mode, setMode] = useState<Mode>('dicom_zip');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const accept = useMemo(() => {
    if (mode === 'dicom_zip') return '.zip';
    return '.nii,.nii.gz';
  }, [mode]);

  async function onFileSelected(file: File) {
    setError(null);
    setResult(null);

    if (!baseUrl) {
      setError('Set VITE_API_BASE_URL to your backend URL to use upload.');
      return;
    }

    setBusy(true);
    try {
      const res = mode === 'dicom_zip' ? await uploadDicomZip(file) : await uploadNifti(file);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section className="card">
        <h1>Upload</h1>
        <div className="muted" style={{ lineHeight: 1.55 }}>
          Upload DICOM as ZIP to start processing on backend.
        </div>

        <div className="row" style={{ alignItems: 'center', marginTop: 12 }}>
          <button
            className={mode === 'dicom_zip' ? 'button' : 'buttonSecondary'}
            onClick={() => setMode('dicom_zip')}
            disabled={busy}
          >
            DICOM ZIP
          </button>
          <button
            className={mode === 'nifti' ? 'button' : 'buttonSecondary'}
            onClick={() => setMode('nifti')}
            disabled={busy}
          >
            NIfTI
          </button>
          <span className="badge">
            backend: <span className="muted">{baseUrl ?? 'not set'}</span>
          </span>
        </div>
      </section>

      <FileUpload
        accept={accept}
        label={mode === 'dicom_zip' ? 'Select .zip with DICOM files' : 'Select .nii / .nii.gz'}
        disabled={busy}
        onFileSelected={onFileSelected}
      />

      {busy && (
        <section className="card">
          <div style={{ fontWeight: 700 }}>Uploading…</div>
          <div className="muted">Please wait.</div>
        </section>
      )}

      {error && (
        <section className="card">
          <div style={{ fontWeight: 800 }}>Error</div>
          <div className="muted" style={{ whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        </section>
      )}

      {result && (
        <section className="card">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Uploaded</div>
          <div className="muted">job_id: {result.job_id}</div>
          <div className="row" style={{ marginTop: 12, alignItems: 'center' }}>
            <Link className="badge" to={`/job/${result.job_id}`}>
              Open job
            </Link>
            <Link className="badge" to="/jobs">
              Jobs list
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
