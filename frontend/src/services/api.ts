/**
 * Base API client for DedupTickets backend.
 *
 * Handles authentication, error handling, and request/response formatting.
 */

import type { ApiError } from '../types';

const API_BASE_URL =
  (import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_API_URL ||
  '/api/v1';
const API_KEY =
  (import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_API_KEY ||
  'dev-api-key-change-in-production';

export class ApiClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = 'Unknown error';
    const text = await response.text();
    try {
      const errorData: ApiError = JSON.parse(text);
      errorDetail = errorData.message || errorDetail;
    } catch {
      errorDetail = text || errorDetail;
    }

    throw new ApiClientError(
      `HTTP ${response.status}: ${errorDetail}`,
      response.status,
      errorDetail
    );
  }

  return response.json();
}

function buildUrl(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): string {
  const path = `${API_BASE_URL}${endpoint}`;
  const url = path.startsWith('http')
    ? new URL(path)
    : new URL(path, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

function getHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  };
}

export async function apiGet<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);

  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
    ...options,
  });

  return handleResponse<T>(response);
}

export async function apiPost<T, D = unknown>(
  endpoint: string,
  data?: D,
  options?: RequestOptions
): Promise<T> {
  const url = buildUrl(endpoint, options?.params);

  const response = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: data ? JSON.stringify(data) : undefined,
    ...options,
  });

  return handleResponse<T>(response);
}

export async function apiPut<T, D = unknown>(
  endpoint: string,
  data?: D,
  options?: RequestOptions
): Promise<T> {
  const url = buildUrl(endpoint, options?.params);

  const response = await fetch(url, {
    method: 'PUT',
    headers: getHeaders(),
    body: data ? JSON.stringify(data) : undefined,
    ...options,
  });

  return handleResponse<T>(response);
}

export async function apiDelete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);

  const response = await fetch(url, {
    method: 'DELETE',
    headers: getHeaders(),
    ...options,
  });

  return handleResponse<T>(response);
}

export const api = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
};

export default api;
