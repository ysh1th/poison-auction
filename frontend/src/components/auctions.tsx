// frontend/src/components/Auctions.tsx
import { useEffect, useRef, useState } from 'react';
import api from '../utils/api';
import { useAuth } from '../utils/auth';

interface Item {
  id: number;
  title: string;
  description: string;
  base_price: number;
  status: string;
  close_at: string;
  current_bid?: { amount: number };
  image?: { image_url: string; image_thumb_url?: string };
}

interface Winner {
  winner_user_id: number;
  amount: number;
}

interface AuctionsProps {
  itemId: number | null;
  setItemId: (id: number | null) => void;
}

export default function Auctions({ itemId, setItemId }: AuctionsProps) {
  const { tokens } = useAuth();
  const [item, setItem] = useState<Item | null>(null);
  const [amount, setAmount] = useState<string>('10');
  const [startIn, setStartIn] = useState<number>(10);
  const [endsIn, setEndsIn] = useState<number | null>(null);
  const [winner, setWinner] = useState<Winner | null>(null);
  const auctionTimerRef = useRef<number | null>(null);
  const startTimerRef = useRef<number | null>(null);

  const itemsApiRoute = '/items';

  async function createItem() {
    const res = await api<Item>(itemsApiRoute, {
      method: 'POST',
      body: JSON.stringify({
        title: 'Mystery',
        description: 'Random',
        base_price: 10,
        close_at: new Date(Date.now() + 3600000).toISOString(),
      }),
      headers: { Authorization: `Bearer ${tokens!.access_token}` },
    });
    setItemId(res.id);
  }

  async function refreshItem(id: number) {
    const res = await api<Item>(`${itemsApiRoute}/${id}`, {
      headers: { Authorization: `Bearer ${tokens!.access_token}` },
    });
    setItem(res);
  }

  async function placeBid() {
    if (!itemId) return;
    await api(`${itemsApiRoute}/${itemId}/bid`, {
      method: 'POST',
      body: JSON.stringify({ amount: parseFloat(amount) }),
      headers: { Authorization: `Bearer ${tokens!.access_token}` },
    });
    await refreshItem(itemId);
  }

  async function closeAuction() {
    if (!itemId) return;
    const res = await api<Winner>(`${itemsApiRoute}/${itemId}/close`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tokens!.access_token}` },
    });
    setWinner(res);
  }

  // Fetch active item on mount
  useEffect(() => {
    async function fetchActiveItem() {
      try {
        const activeItem = await api<Item | null>(`${itemsApiRoute}/active`, {
          headers: { Authorization: `Bearer ${tokens!.access_token}` },
        });
        if (activeItem) {
          setItemId(activeItem.id);
          setItem(activeItem);
        } else {
          await createItem();
        }
      } catch (e) {
        console.error('Failed to fetch active item:', e);
      }
    }
    if (!itemId) fetchActiveItem();
  }, [tokens, itemId, setItemId]);

  useEffect(() => {
    if (itemId && !item) refreshItem(itemId);
  }, [itemId, item]);

  useEffect(() => {
    if (startIn <= 0) {
      if (startTimerRef.current) window.clearInterval(startTimerRef.current);
      setEndsIn(60);
      auctionTimerRef.current = window.setInterval(() => setEndsIn(v => (v ? v - 1 : 0)), 1000);
      return;
    }
    startTimerRef.current = window.setInterval(() => setStartIn(v => v - 1), 1000);
    return () => {
      if (startTimerRef.current) window.clearInterval(startTimerRef.current);
    };
  }, [startIn]);

  useEffect(() => {
    if (endsIn === 0) {
      if (auctionTimerRef.current) window.clearInterval(auctionTimerRef.current);
      closeAuction();
    }
  }, [endsIn]);

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
            {item.image ? (
              <img
                src={item.image.image_thumb_url || item.image.image_url}
                alt={item.title}
                style={{ width: '100%', borderRadius: 8 }}
              />
            ) : (
              <div style={{ width: '100%', height: 120, background: '#eee' }} />
            )}
          </div>
          <div>
            <h3>{item.title}</h3>
            <div>{item.description}</div>
            <div>Status: {item.status}</div>
            <div>Base: {item.base_price}</div>
            <div>Current bid: {item.current_bid ? item.current_bid.amount : '—'}</div>
            {startIn > 0 ? <div>Starts in: {startIn}s</div> : <div>Ends in: {endsIn ?? '—'}s</div>}
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <input value={amount} onChange={e => setAmount(e.target.value)} type="number" step="1" />
              <button disabled={startIn > 0 || (endsIn ?? 0) <= 0} onClick={placeBid}>
                Bid
              </button>
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
  );
}