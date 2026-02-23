import { token } from './stores.js';
import { get } from 'svelte/store';

const BASE = 'http://localhost:8000/api';

async function request(method, path, body) {
  const t = get(token);
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

function authHeaders() {
  const t = get(token);
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),

  async downloadBlob(path) {
    const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },

  async upload(path, file) {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};
