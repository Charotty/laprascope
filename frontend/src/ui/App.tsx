import { Link, Route, Routes } from 'react-router-dom';
import HomePage from './pages/HomePage';
import DemoPage from './pages/DemoPage';
import UploadPage from './pages/UploadPage';
import JobsPage from './pages/JobsPage';
import JobDetailPage from './pages/JobDetailPage';

function EnvBadge() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const useMock = (import.meta.env.VITE_USE_MOCK as string | undefined) === 'true' || !baseUrl;

  return (
    <span className="badge">
      <span>API:</span>
      <span className="muted">{useMock ? 'mock' : baseUrl}</span>
    </span>
  );
}

export default function App() {
  return (
    <>
      <header className="nav">
        <div className="row" style={{ alignItems: 'center' }}>
          <Link to="/" style={{ fontWeight: 800, letterSpacing: 0.3 }}>
            Laprascope
          </Link>
          <EnvBadge />
        </div>
        <nav className="navLinks">
          <Link className="badge" to="/">
            Home
          </Link>
          <Link className="badge" to="/upload">
            Upload
          </Link>
          <Link className="badge" to="/jobs">
            Jobs
          </Link>
          <Link className="badge" to="/demo">
            Demo
          </Link>
        </nav>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/job/:jobId" element={<JobDetailPage />} />
          <Route path="/demo" element={<DemoPage />} />
        </Routes>
      </main>
    </>
  );
}
