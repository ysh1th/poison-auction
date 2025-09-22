// frontend/src/components/Inventory.tsx
import { useEffect, useState } from 'react';
import api from '../utils/api';
import { useAuth } from '../utils/auth';

interface Item {
  id: number;
  image_url?: string;
  image_thumb_url?: string;
  unsplash_id?: string;
}

export default function Inventory() {
  const { tokens } = useAuth();
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    (async () => {
      const res = await api<Item[]>('/auth/inventory', {
        headers: { Authorization: `Bearer ${tokens!.access_token}` },
      });
      setItems(res);
    })();
  }, [tokens]);

  return (
    <div style={{ marginTop: 16 }}>
      <h3>My Inventory</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
        {items.map(it => (
          <div key={it.id} style={{ border: '1px solid #eee', borderRadius: 8, padding: 8 }}>
            {it.image_thumb_url || it.image_url ? (
              <img
                src={it.image_thumb_url || it.image_url}
                alt={it.unsplash_id || 'img'}
                style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 6 }}
              />
            ) : (
              <div style={{ width: '100%', height: 120, background: '#f2f2f2' }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}