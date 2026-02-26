export type UploadResponse = {
  job_id: string;
  status: string;
  message: string;
  files_count?: number;
  input_type?: string;
};

export type JobStatus = {
  job_id: string;
  status: string;
  created_at?: string;
  upload_filename?: string;
  files_count?: number;
  input_type?: string;
  progress?: number;
  error?: unknown;
  [key: string]: unknown;
};

export type JobsListResponse = {
  jobs: Record<string, JobStatus>;
  total: number;
};

export type FilesListResponse = {
  job_id: string;
  files: Record<
    string,
    {
      path: string;
      size: number;
      size_mb: number;
    }
  >;
  total_files: number;
};

export type BackendHealth = {
  status: string;
  jobs_accessible?: boolean;
  active_jobs?: number;
  total_jobs?: number;
  error?: string;
};

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

function ensureBaseUrl(): string {
  if (!baseUrl) {
    throw new Error('VITE_API_BASE_URL is not set');
  }
  return baseUrl.replace(/\/$/, '');
}

async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${ensureBaseUrl()}${path}`;
  const res = await fetch(url, init);

  if (!res.ok) {
    let details: unknown = undefined;
    try {
      details = await res.json();
    } catch {
      // ignore
    }
    throw new Error(`HTTP ${res.status} ${res.statusText}${details ? `: ${JSON.stringify(details)}` : ''}`);
  }

  return (await res.json()) as T;
}

async function httpForm<T>(path: string, form: FormData): Promise<T> {
  const url = `${ensureBaseUrl()}${path}`;
  const res = await fetch(url, {
    method: 'POST',
    body: form
  });

  if (!res.ok) {
    let details: unknown = undefined;
    try {
      details = await res.json();
    } catch {
      // ignore
    }
    throw new Error(`HTTP ${res.status} ${res.statusText}${details ? `: ${JSON.stringify(details)}` : ''}`);
  }

  return (await res.json()) as T;
}

export function getDownloadUrl(path: string): string {
  return `${ensureBaseUrl()}${path}`;
}

export async function health(): Promise<BackendHealth> {
  return httpJson<BackendHealth>('/api/v1/health');
}

export async function uploadDicomZip(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  return httpForm<UploadResponse>('/api/v1/upload', form);
}

export async function uploadNifti(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  return httpForm<UploadResponse>('/api/v1/upload-nifti', form);
}

export async function getStatus(jobId: string): Promise<JobStatus> {
  return httpJson<JobStatus>(`/api/v1/status/${encodeURIComponent(jobId)}`);
}

export async function listJobs(): Promise<JobsListResponse> {
  return httpJson<JobsListResponse>('/api/v1/jobs');
}

export async function listFiles(jobId: string): Promise<FilesListResponse> {
  return httpJson<FilesListResponse>(`/api/v1/files/${encodeURIComponent(jobId)}`);
}
