export type Health = {
  mode: 'mock' | 'remote';
};

export type CaseInfo = {
  id: string;
  title: string;
  modality: string;
};

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
const forceMock = (import.meta.env.VITE_USE_MOCK as string | undefined) === 'true';

async function mockGetHealth(): Promise<Health> {
  return { mode: 'mock' };
}

async function mockListCases(): Promise<CaseInfo[]> {
  return [
    { id: 'case_00000', title: 'KiTS23 sample case', modality: 'CT' },
    { id: 'kidney_test', title: 'Local test volume', modality: 'NIfTI' }
  ];
}

async function httpJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${baseUrl}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}`);
  }

  return (await res.json()) as T;
}

export async function getHealth(): Promise<Health> {
  if (forceMock || !baseUrl) return mockGetHealth();
  return httpJson<Health>('/health');
}

export async function listCases(): Promise<CaseInfo[]> {
  if (forceMock || !baseUrl) return mockListCases();
  return httpJson<CaseInfo[]>('/cases');
}
