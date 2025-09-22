import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../utils/auth';

interface ItemDetail {
  id: number;
  title: string;
  description: string;
  base_price: number;
  status: 'scheduled' | 'in_progress' | 'closed';
  start_at?: string | null;
  end_at?: string | null;
  min_start_price: number;
  image?: { image_url?: string; image_thumb_url?: string } | null;
  current_bid?: { amount: number; user_id: number } | null;
  seconds_to_start?: number | null;
  seconds_to_end?: number | null;
  players: number;
  joined: boolean;
}

export default function AuctionRoomPg() {
  const { id } = useParams();
  const itemId = useMemo(() => (id ? parseInt(id, 10) : null), [id]);
  const { tokens } = useAuth();
  const nav = useNavigate();

  const [item, setItem] = useState<ItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [amount, setAmount] = useState<string>('100');
  const [maxBudget, setMaxBudget] = useState<string>('');
  const [bidIncrement, setBidIncrement] = useState<string>('');
  const [joining, setJoining] = useState(false);

  async function fetchItem() {
    if (!itemId) return;
    try {
      const res = await api<ItemDetail>(`/items/${itemId}`, {
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      setItem(res);
      setError(null);
    } catch (e: any) {
      setError('Failed to load auction');
    } finally {
      setLoading(false);
    }
  }

  async function join() {
    if (!itemId) return;
    setJoining(true);
    try {
      await api(`/items/${itemId}/join`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      await fetchItem();
    } catch (e: any) {
      setError('Unable to join. Auction may be locked.');
    } finally {
      setJoining(false);
    }
  }

  async function leave() {
    if (!itemId) return;
    try {
      await api(`/items/${itemId}/leave`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      await fetchItem();
    } catch {}
  }

  async function placeBid() {
    if (!itemId) return;
    try {
      await api(`/items/${itemId}/bid`, {
        method: 'POST',
        body: JSON.stringify({
          amount: parseFloat(amount),
          max_budget: maxBudget ? parseFloat(maxBudget) : null,
          bid_increment: bidIncrement ? parseFloat(bidIncrement) : null,
        }),
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      await fetchItem();
    } catch (e: any) {
      setError('Bid failed');
    }
  }

  useEffect(() => {
    fetchItem();
    const t = setInterval(fetchItem, 1000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId, tokens]);

  if (!itemId) return <div>Invalid auction</div>;
  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;
  if (!item) return <div>Not found</div>;

  const canJoin = item.status === 'scheduled' && !item.joined;
  const canLeave = item.joined && item.status === 'scheduled';
  const canBid = item.joined && item.status === 'in_progress' && (item.seconds_to_end ?? 0) > 0;

  return (
    <div>
      <button onClick={() => nav('/')}>{'< Back'}</button>
      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '240px 1fr', gap: 16 }}>
        <div>
          {item.image?.image_thumb_url || item.image?.image_url ? (
            <img src={item.image.image_thumb_url || item.image.image_url} style={{ width: '100%', borderRadius: 8 }} />
          ) : (
            <div style={{ width: '100%', height: 160, background: '#f5f5f5' }} />
          )}
        </div>
        <div>
          <h3>{item.title}</h3>
          <div>Status: {item.status}</div>
          {item.status === 'scheduled' && <div>Starts in: {item.seconds_to_start ?? 0}s</div>}
          {item.status === 'in_progress' && <div>Ends in: {item.seconds_to_end ?? 0}s</div>}
          <div>Players: {item.players}</div>
          <div>Base price: {item.base_price}</div>
          <div>Min start: {item.min_start_price}</div>
          <div>Current bid: {item.current_bid?.amount ?? '—'}</div>

          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button disabled={!canJoin || joining} onClick={join}>Join</button>
            <button disabled={!canLeave} onClick={leave}>Exit</button>
          </div>

          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8 }}>
            <input value={amount} onChange={e => setAmount(e.target.value)} placeholder="Amount" type="number" />
            <input value={maxBudget} onChange={e => setMaxBudget(e.target.value)} placeholder="Max budget (optional)" type="number" />
            <input value={bidIncrement} onChange={e => setBidIncrement(e.target.value)} placeholder="Step (optional)" type="number" />
            <button disabled={!canBid} onClick={placeBid}>Bid</button>
          </div>
        </div>
      </div>
    </div>
  );
}
