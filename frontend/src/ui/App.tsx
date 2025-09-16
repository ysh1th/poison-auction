import React, { useEffect, useMemo, useRef, useState } from 'react'

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

export const App: React.FC = () => {
  const [email, setEmail] = useState('player@example.com')
  const [password, setPassword] = useState('pass')
  const [tokens, setTokens] = useState<Tokens | null>(null)
  const [itemId, setItemId] = useState<number | null>(null)
  const [item, setItem] = useState<any>(null)
  const [amount, setAmount] = useState<string>('10')
  const [startIn, setStartIn] = useState<number>(10) // seconds to auction start
  const [endsIn, setEndsIn] = useState<number | null>(null)
  const [winner, setWinner] = useState<any>(null)
  const auctionTimerRef = useRef<number | null>(null)
  const startTimerRef = useRef<number | null>(null)

  const isAuthed = !!tokens?.access_token

  async function ensureLogin() {
    try {
      await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, role: 'viewer' }) })
    } catch {}
    const res = await api('/auth/login', { method: 'POST', body: new URLSearchParams({ username: email, password }) })
    setTokens(res)
  }

  async function createItem() {
    const res = await api('/items', { method: 'POST', body: JSON.stringify({ title: 'Mystery', desc: 'Random', base_price: 10 }) })
    setItemId(res.id)
  }

  async function refreshItem(id: number) {
    const res = await api(`/items/${id}`)
    setItem(res)
  }

  async function placeBid() {
    if (!itemId || !tokens) return
    await api(`/items/${itemId}/bid`, { method: 'POST', body: JSON.stringify({ amount: parseFloat(amount) }) }, tokens.access_token)
    await refreshItem(itemId)
  }

  async function closeAuction() {
    if (!itemId) return
    const res = await api(`/items/${itemId}/close`, { method: 'POST' })
    setWinner(res)
  }

  useEffect(() => {
    if (!itemId) return
    refreshItem(itemId)
  }, [itemId])

  useEffect(() => {
    if (startIn <= 0) {
      if (startTimerRef.current) window.clearInterval(startTimerRef.current)
      setEndsIn(60)
      auctionTimerRef.current = window.setInterval(() => setEndsIn(v => (v ? v - 1 : 0)), 1000)
      return
    }
    startTimerRef.current = window.setInterval(() => setStartIn(v => v - 1), 1000)
    return () => { if (startTimerRef.current) window.clearInterval(startTimerRef.current) }
  }, [startIn])

  useEffect(() => {
    if (endsIn === 0) {
      if (auctionTimerRef.current) window.clearInterval(auctionTimerRef.current)
      closeAuction()
    }
  }, [endsIn])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h1>Toxic Hammer Auction</h1>
      {!isAuthed ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder='email' />
          <input value={password} onChange={e => setPassword(e.target.value)} placeholder='password' type='password' />
          <button onClick={ensureLogin}>Register + Login</button>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span>Logged in as {email}</span>
          <button onClick={() => setTokens(null)}>Logout</button>
        </div>
      )}

      <hr style={{ margin: '16px 0' }} />

      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button onClick={createItem}>Create Item</button>
        <button disabled={!itemId} onClick={() => refreshItem(itemId!)}>Refresh Item</button>
        {itemId && <span>Item ID: {itemId}</span>}
      </div>

      {item && (
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16 }}>
          <div>
            {item.image_url ? <img src={item.image_thumb_url || item.image_url} alt={item.title} style={{ width: '100%', borderRadius: 8 }} /> : <div style={{ width: '100%', height: 120, background: '#eee' }} />}
          </div>
          <div>
            <h3>{item.title}</h3>
            <div>{item.desc}</div>
            <div>Status: {item.status}</div>
            <div>Base: {item.base_price}</div>
            <div>Current bid: {item.current_bid ? item.current_bid.amount : '—'}</div>
            {startIn > 0 ? (
              <div>Starts in: {startIn}s</div>
            ) : (
              <div>Ends in: {endsIn ?? '—'}s</div>
            )}

            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <input value={amount} onChange={e => setAmount(e.target.value)} type='number' step='1' />
              <button disabled={!isAuthed || startIn > 0 || (endsIn ?? 0) <= 0} onClick={placeBid}>Bid</button>
              <button onClick={closeAuction}>Force Close</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <button disabled={!isAuthed} onClick={async () => {
          const inv = await api('/auth/inventory', {}, tokens!.access_token)
          alert(JSON.stringify(inv, null, 2))
        }}>My Inventory</button>
      </div>

      {winner && (
        <div style={{ marginTop: 24, padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
          Winner user id: {winner.winner_user_id} amount: {winner.amount}
        </div>
      )}
    </div>
  )
}


