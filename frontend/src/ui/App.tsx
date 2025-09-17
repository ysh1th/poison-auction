import React, { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'

type Tokens = { access_token: string, refresh_token: string }

async function api(path: string, options: RequestInit = {}, token?: string) {
  const isForm = options.body instanceof URLSearchParams
  const headers: any = { ...(options.headers || {}) }
  if (!isForm) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(path, { ...options, headers })
  if (!res.ok) throw new Error(`${res.status}`)
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res.text()
}

function LoginView({ onAuthed }: { onAuthed: (t: Tokens, email: string) => void }) {
  const [email, setEmail] = useState('player@example.com')
  const [password, setPassword] = useState('pass')
  const [error, setError] = useState<string | null>(null)

  async function registerLogin() {
    try {
      setError(null)
      try { await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, role: 'viewer' }) }) } catch {}
      const tokens = await api('/auth/login', { method: 'POST', body: new URLSearchParams({ username: email, password }) })
      onAuthed(tokens, email)
    } catch (e: any) {
      setError(e.message || 'Login failed')
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '10vh auto', padding: 24, border: '1px solid #ddd', borderRadius: 8 }}>
      <h2>Login</h2>
      <div style={{ display: 'grid', gap: 8 }}>
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder='email' />
        <input value={password} onChange={e => setPassword(e.target.value)} placeholder='password' type='password' />
        <button onClick={registerLogin}>Register + Login</button>
        {error && <div style={{ color: 'crimson' }}>{error}</div>}
      </div>
    </div>
  )
}

function Auctions({ tokens, email }: { tokens: Tokens, email: string }) {
  const [itemId, setItemId] = useState<number | null>(null)
  const [item, setItem] = useState<any>(null)
  const [amount, setAmount] = useState<string>('10')
  const [startIn, setStartIn] = useState<number>(10)
  const [endsIn, setEndsIn] = useState<number | null>(null)
  const [winner, setWinner] = useState<any>(null)
  const auctionTimerRef = useRef<number | null>(null)
  const startTimerRef = useRef<number | null>(null)

  async function createItem() {
    const res = await api('/items', { method: 'POST', body: JSON.stringify({ title: 'Mystery', description: 'Random', base_price: 10 }) })
    setItemId(res.id)
  }
  async function refreshItem(id: number) { const res = await api(`/items/${id}`); setItem(res) }
  async function placeBid() { if (!itemId) return; await api(`/items/${itemId}/bid`, { method: 'POST', body: JSON.stringify({ amount: parseFloat(amount) }) }, tokens.access_token); await refreshItem(itemId) }
  async function closeAuction() { if (!itemId) return; const res = await api(`/items/${itemId}/close`, { method: 'POST' }); setWinner(res) }

  useEffect(() => { if (itemId) refreshItem(itemId) }, [itemId])
  useEffect(() => {
    if (startIn <= 0) { if (startTimerRef.current) window.clearInterval(startTimerRef.current); setEndsIn(60); auctionTimerRef.current = window.setInterval(() => setEndsIn(v => (v ? v - 1 : 0)), 1000); return }
    startTimerRef.current = window.setInterval(() => setStartIn(v => v - 1), 1000)
    return () => { if (startTimerRef.current) window.clearInterval(startTimerRef.current) }
  }, [startIn])
  useEffect(() => { if (endsIn === 0) { if (auctionTimerRef.current) window.clearInterval(auctionTimerRef.current); closeAuction() } }, [endsIn])

  // Auto create a new item every 5 minutes when none is active
  useEffect(() => {
    let interval: number | null = null
    const ensureItem = async () => { if (!itemId) await createItem() }
    ensureItem()
    interval = window.setInterval(() => { if (!itemId) createItem() }, 5 * 60 * 1000)
    return () => { if (interval) window.clearInterval(interval) }
  }, [itemId])

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button onClick={createItem}>Create Item</button>
        <button disabled={!itemId} onClick={() => refreshItem(itemId!)}>Refresh Item</button>
        {itemId && <span>Item ID: {itemId}</span>}
      </div>
      {item && (
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16 }}>
          <div>
            {item.image ? <img src={item.image.image_thumb_url || item.image.image_url} alt={item.title} style={{ width: '100%', borderRadius: 8 }} /> : <div style={{ width: '100%', height: 120, background: '#eee' }} />}
          </div>
          <div>
            <h3>{item.title}</h3>
            <div>{item.description}</div>
            <div>Status: {item.status}</div>
            <div>Base: {item.base_price}</div>
            <div>Current bid: {item.current_bid ? item.current_bid.amount : '—'}</div>
            {startIn > 0 ? <div>Starts in: {startIn}s</div> : <div>Ends in: {endsIn ?? '—'}s</div>}
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <input value={amount} onChange={e => setAmount(e.target.value)} type='number' step='1' />
              <button disabled={startIn > 0 || (endsIn ?? 0) <= 0} onClick={placeBid}>Bid</button>
              <button onClick={closeAuction}>Force Close</button>
            </div>
          </div>
        </div>
      )}
      {winner && (
        <div style={{ marginTop: 24, padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
          Winner user id: {winner.winner_user_id} amount: {winner.amount}
        </div>
      )}
    </div>
  )
}

function Inventory({ tokens }: { tokens: Tokens }) {
  const [items, setItems] = useState<any[]>([])
  useEffect(() => { (async () => { const res = await fetch('/auth/inventory', { headers: { Authorization: `Bearer ${tokens.access_token}` } }); setItems(await res.json()) })() }, [tokens.access_token])
  return (
    <div style={{ marginTop: 16 }}>
      <h3>My Inventory</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
        {items.map((it) => (
          <div key={it.id} style={{ border: '1px solid #eee', borderRadius: 8, padding: 8 }}>
            {it.image_thumb_url || it.image_url ? (
              <img src={it.image_thumb_url || it.image_url} alt={it.unsplash_id || 'img'} style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 6 }} />
            ) : (
              <div style={{ width: '100%', height: 120, background: '#f2f2f2' }} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export const App: React.FC = () => {
  const [tokens, setTokens] = useState<Tokens | null>(null)
  const [email, setEmail] = useState<string>('')
  const isAuthed = !!tokens?.access_token
  return (
    <BrowserRouter>
      {!isAuthed ? (
        <LoginView onAuthed={(t, e) => { setTokens(t); setEmail(e) }} />
      ) : (
        <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1000, margin: '0 auto' }}>
          <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Toxic Hammer Auction</h2>
            <nav style={{ display: 'flex', gap: 12 }}>
              <Link to="/">Auctions</Link>
              <Link to="/inventory">Inventory</Link>
              <button onClick={() => setTokens(null)}>Logout</button>
            </nav>
          </header>
          <Routes>
            <Route path="/" element={<Auctions tokens={tokens!} email={email} />} />
            <Route path="/inventory" element={<Inventory tokens={tokens!} />} />
          </Routes>
        </div>
      )}
    </BrowserRouter>
  )
}
