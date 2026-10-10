const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

function getAuthToken() {
  return localStorage.getItem('secure_rag_token');
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  headers.set('Accept', 'application/json');

  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Debug: log outgoing request info to help trace unexpected 401s
  // eslint-disable-next-line no-console
  console.debug('[api] request', { endpoint, method: options.method ?? 'GET', hasToken: Boolean(token) });

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      typeof data?.detail === 'string'
        ? data.detail
        : typeof data?.message === 'string'
          ? data.message
          : 'Request failed.';

    if (response.status === 401) {
      // eslint-disable-next-line no-console
      console.warn('[api] 401 Unauthorized - clearing auth token', { endpoint, status: response.status, data, stack: new Error().stack });
      localStorage.removeItem('secure_rag_token');
      localStorage.removeItem('secure_rag_user');
    }

    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};

export interface QueryResponse {
  answer: string;
  sources: Array<{
    document_id?: string;
    document_name?: string;
    filename?: string;
    page?: number;
    chunk_index?: number;
    chunk_id?: string;
    relevance_score?: number;
  }>;
}

export async function queryRAG(query: string, documentId?: string): Promise<any> {
  return api.post<any>('/api/rag/query', { query, document_id: documentId ?? null });
}

export async function uploadDocument(file: File, roles: string[] = []) {
  const token = getAuthToken();
  const form = new FormData();
  form.append('file', file);
  roles.forEach((r) => form.append('allowed_roles', r));

  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(data?.detail || 'Upload failed', res.status, data);
  }

  return res.json();
}