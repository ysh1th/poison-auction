import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface Tokens {
  access_token: string;
  refresh_token: string;
}

interface AuthContextType {
  tokens: Tokens | null;
  setTokens: (tokens: Tokens | null) => void;
  email: string;
  setEmail: (email: string) => void;
  itemId: number | null;
  setItemId: (itemId: number | null) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<Tokens | null>(() => {
    const access_token = sessionStorage.getItem('access_token');
    const refresh_token = document.cookie.match(/refresh_token=([^;]+)/)?.[1];
    return access_token && refresh_token ? { access_token, refresh_token } : null;
  });
  const [email, setEmail] = useState<string>(sessionStorage.getItem('email') || '');
  const [itemId, setItemId] = useState<number | null>(() => {
    const saved = sessionStorage.getItem('itemId');
    return saved ? parseInt(saved, 10) : null;
  });

  useEffect(() => {
    if (tokens) {
      sessionStorage.setItem('access_token', tokens.access_token);
      document.cookie = `refresh_token=${tokens.refresh_token}; HttpOnly; Secure; SameSite=Strict`;
      sessionStorage.setItem('email', email);
    } else {
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('email');
      document.cookie = 'refresh_token=; Max-Age=0';
    }
  }, [tokens, email]);

  useEffect(() => {
    if (itemId) {
      sessionStorage.setItem('itemId', itemId.toString());
    } else {
      sessionStorage.removeItem('itemId');
    }
  }, [itemId]);

  return (
    <AuthContext.Provider value={{ tokens, setTokens, email, setEmail, itemId, setItemId }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}