// frontend/src/App.tsx
import { BrowserRouter, Link, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './utils/auth';
import LoginPage from './pages/loginPg';
import InventoryPage from './pages/inventoryPg';
import AuctionsListPg from './pages/AuctionsListPg';
import AuctionRoomPg from './pages/AuctionRoomPg';

function AppContent() {
  const { tokens, setTokens, setItemId } = useAuth();
  const isAuthed = !!tokens?.access_token;

  if (!isAuthed) {
    return <LoginPage />;
  }

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Toxic Hammer Auction</h2>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/">Auctions</Link>
          <Link to="/inventory">Inventory</Link>
          <button
            onClick={() => {
              setTokens(null);
              setItemId(null);
              sessionStorage.clear();
              document.cookie = 'refresh_token=; Max-Age=0';
            }}
          >
            Logout
          </button>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<AuctionsListPg />} />
        <Route path="/auction/:id" element={<AuctionRoomPg />} />
        <Route path="/inventory" element={<InventoryPage />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}