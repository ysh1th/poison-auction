import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../utils/auth';

interface ItemSummary {
  id: number;
  title: string;
  status: 'scheduled' | 'in_progress' | 'closed';
  start_at?: string | null;
  end_at?: string | null;
  seconds_to_start?: number | null;
  seconds_to_end?: number | null;
  min_start_price: number;
  base_price: number;
  current_bid?: { amount: number } | null;
  players: number;
  image?: { image_url?: string; image_thumb_url?: string };
}

export default function AuctionsListPg() {
  const { tokens } = useAuth();
  const nav = useNavigate();
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchItems() {
    try {
      const res = await api<ItemSummary[]>('/items', {
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      setItems(res);
      setError(null);
    } catch (e: any) {
      setError('Failed to load auctions');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchItems();
    const t = setInterval(fetchItems, 1000);
    return () => clearInterval(t);
  }, [tokens]);

  if (loading) return <div>Loading auctions...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div>
      <h3>Live Auctions</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {items.map((it) => (
          <div key={it.id} onClick={() => nav(`/auction/${it.id}`)}
            style={{ cursor: 'pointer', border: '1px solid #eee', borderRadius: 8, padding: 12, background: '#fff' }}>
            <div>
              {it.image?.image_thumb_url || it.image?.image_url ? (
                <img src={it.image.image_thumb_url || it.image.image_url} style={{ width: '100%', borderRadius: 6 }} />
              ) : (
                <div style={{ width: '100%', height: 120, background: '#f5f5f5', borderRadius: 6 }} />
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{it.title}</strong>
              <span style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, background: it.status==='in_progress' ? '#fff1b8' : it.status==='scheduled' ? '#e6f7ff' : '#f0f0f0' }}>
                {it.status}
              </span>
            </div>
            <div style={{ marginTop: 8 }}>
              {it.status === 'scheduled' && (
                <div>Gonna start in: {it.seconds_to_start ?? 0}s</div>
              )}
              {it.status === 'in_progress' && (
                <div>
                  <div>Ends in: {it.seconds_to_end ?? 0}s</div>
                  <div style={{ color: '#fa8c16' }}>Locked</div>
                </div>
              )}
              {it.status === 'closed' && <div>Closed</div>}
            </div>
            <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div>Min start: {it.min_start_price}</div>
              <div>Current: {it.current_bid?.amount ?? '—'}</div>
              <div>Players: {it.players}</div>
              <div>Base: {it.base_price}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
