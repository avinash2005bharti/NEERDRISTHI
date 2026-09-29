/**
 * Centralized API Client for ORCA / NEERDRISTHI
 * Handles base URLs, JWT injection, response normalization, and structured error mapping.
 *
 * In production decoupled deployment (e.g. Render Static Site calling Render Web Service),
 * configure VITE_API_URL (e.g. https://orca-backend.onrender.com).
 * In local dev proxy or single-port mode, VITE_API_URL can be omitted or empty.
 */

const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const normalizedApiUrl = rawApiUrl
  ? rawApiUrl.startsWith('http://') || rawApiUrl.startsWith('https://')
    ? rawApiUrl
    : `https://${rawApiUrl}`
  : '';
const API_BASE = normalizedApiUrl ? `${normalizedApiUrl}/api/v1` : '/api/v1';


export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem('orca_jwt_token');
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem('orca_jwt_token', token);
  } else {
    localStorage.removeItem('orca_jwt_token');
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      // Clear token on 401 Unauthorized
      setStoredToken(null);
      window.dispatchEvent(new CustomEvent('orca:auth:unauthorized'));
    }

    const json = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMsg =
        json?.message ||
        json?.error?.message ||
        (typeof json?.error === 'string' ? json.error : null) ||
        json?.detail ||
        `Request failed with status ${res.status}`;
      throw new ApiError(errorMsg, res.status, json);
    }

    return json as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) throw err;
    const msg = err instanceof Error ? err.message : 'Network error or backend unavailable';
    throw new ApiError(msg, 0, err);
  }
}
