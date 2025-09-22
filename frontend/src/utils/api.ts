// frontend/src/utils/api.ts
interface Tokens {
  access_token: string;
  refresh_token: string;
}

async function api<T = unknown>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const isForm = options.body instanceof URLSearchParams;
  const headers: HeadersInit = {
    ...(options.headers || {}),
    ...(isForm ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    try {
      const refreshToken = document.cookie.match(/refresh_token=([^;]+)/)?.[1];
      if (!refreshToken) throw new Error('No refresh token');

      const response = await fetch('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) throw new Error('Refresh failed');

      const { access_token, refresh_token }: Tokens = await response.json();
      sessionStorage.setItem('access_token', access_token);
      document.cookie = `refresh_token=${refresh_token}; HttpOnly; Secure; SameSite=Strict`;
      const retryHeaders: HeadersInit = {
        ...headers,
        Authorization: `Bearer ${access_token}`,
      };

      const retryRes = await fetch(path, { ...options, headers: retryHeaders });
      if (!retryRes.ok) throw new Error(`${retryRes.status}`);

      const ct = retryRes.headers.get('content-type') || '';
      return ct.includes('application/json') ? retryRes.json() : (retryRes.text() as unknown as T);
    } catch {
      sessionStorage.clear();
      document.cookie = 'refresh_token=; Max-Age=0';
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (!res.ok) throw new Error(`${res.status}`);
  
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : (res.text() as unknown as T);
}

export default api;