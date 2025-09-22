// frontend/src/components/LoginView.tsx
import { useState } from 'react';
import api from '../utils/api';
import { useAuth, Tokens } from '../utils/auth';

export default function LoginView() {
  const [email, setEmail] = useState<string>('player@example.com');
  const [password, setPassword] = useState<string>('pass');
  const [error, setError] = useState<string | null>(null);
  const { setTokens, setEmail: setGlobalEmail } = useAuth();

  async function registerLogin() {
    try {
      setError(null);
      try {
        await api('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password, role: 'viewer' }),
        });
      } catch {}
      const tokens = await api<Tokens>('/auth/login', {
        method: 'POST',
        body: new URLSearchParams({ username: email, password }),
      });
      setTokens(tokens);
      setGlobalEmail(email);
    } catch (e: any) {
      setError(e.message || 'Login failed');
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '10vh auto', padding: 24, border: '1px solid #ddd', borderRadius: 8 }}>
      <h2>Login</h2>
      <div style={{ display: 'grid', gap: 8 }}>
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={e => setPassword(e.target.value)} placeholder="password" type="password" />
        <button onClick={registerLogin}>Register + Login</button>
        {error && <div style={{ color: 'crimson' }}>{error}</div>}
      </div>
    </div>
  );
}