export default function HomePage() {
  return (
    <div className="row" style={{ gap: 16 }}>
      <section className="card" style={{ flex: '1 1 520px' }}>
        <h1>Frontend (offline-first)</h1>
        <div className="muted" style={{ lineHeight: 1.55 }}>
          This frontend runs without backend by default using mock data.
          Later you can point it to a real API via VITE_API_BASE_URL.
        </div>
      </section>

      <section className="card" style={{ flex: '1 1 360px' }}>
        <h2>Next</h2>
        <div className="muted" style={{ lineHeight: 1.55 }}>
          Tell me what screens you need first (dataset list, case viewer, segmentation results, STL export, etc.) and I’ll scaffold them.
        </div>
      </section>
    </div>
  );
}
