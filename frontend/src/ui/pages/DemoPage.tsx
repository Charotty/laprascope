import { useMemo, useState } from 'react';
import { getHealth, listCases, type CaseInfo } from '../../api/laprascopeApi';

export default function DemoPage() {
  const [cases, setCases] = useState<CaseInfo[] | null>(null);
  const [status, setStatus] = useState<string>('idle');

  const canRender = useMemo(() => Array.isArray(cases), [cases]);

  async function onLoad() {
    setStatus('loading');
    try {
      const health = await getHealth();
      const data = await listCases();
      setCases(data);
      setStatus(`ok (${health.mode})`);
    } catch (e) {
      setStatus('error');
      setCases(null);
    }
  }

  return (
    <div className="row" style={{ gap: 16, alignItems: 'flex-start' }}>
      <section className="card" style={{ flex: '1 1 420px' }}>
        <h1>Demo</h1>
        <div className="muted" style={{ marginBottom: 12 }}>
          This page calls the API layer. If VITE_API_BASE_URL is not set, mock implementation is used.
        </div>
        <div className="row" style={{ alignItems: 'center' }}>
          <button className="button" onClick={onLoad}>
            Load cases
          </button>
          <span className="badge">status: <span className="muted">{status}</span></span>
        </div>
      </section>

      <section className="card" style={{ flex: '1 1 520px' }}>
        <h2>Cases</h2>
        {!canRender ? (
          <div className="muted">No data loaded.</div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {cases!.map((c) => (
              <div key={c.id} className="card" style={{ padding: 12 }}>
                <div style={{ fontWeight: 700 }}>{c.title}</div>
                <div className="muted">id: {c.id}</div>
                <div className="muted">modality: {c.modality}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
