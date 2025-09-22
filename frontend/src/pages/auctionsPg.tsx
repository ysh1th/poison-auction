// frontend/src/pages/AuctionsPage.tsx
import Auctions from '../components/auctions';
import { useAuth } from '../utils/auth';

export default function AuctionsPage() {
  const { itemId, setItemId } = useAuth();
  return <Auctions itemId={itemId} setItemId={setItemId} />;
}