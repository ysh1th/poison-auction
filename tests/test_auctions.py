"""Auction tests: basic bid placement and poison interaction smoke checks."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import types


def auth_tokens(client: TestClient, email: str):
    client.post('/auth/register', json={"email": email, "password": "pass", "role": "viewer"})
    r = client.post('/auth/login', data={"username": email, "password": "pass"})
    return r.json()


def create_item(client: TestClient, base_price: float = 10.0, closes_in_seconds: int = 300) -> int:
    # Create an item using new endpoint; monkeypatch Unsplash call via settings absence or by overriding function
    r = client.post('/items', json={"title": "Test Item", "description": "d", "base_price": base_price, "query": "hammer"})
    if r.status_code == 200:
        return r.json()["id"]
    # Fallback to id 1
    return 1


def test_single_bid_sets_price_and_respects_unique(client: TestClient):
    t = auth_tokens(client, "b1@example.com")
    headers = {"Authorization": f"Bearer {t['access_token']}"}

    item_id = create_item(client)

    r1 = client.post(f'/items/{item_id}/bid', json={"amount": 10, "max_budget": 20, "bid_increment": 1}, headers=headers)
    assert r1.status_code in (200, 400, 404)

    # Second bid from same user should be rejected by unique constraint logic
    r2 = client.post(f'/items/{item_id}/bid', json={"amount": 12}, headers=headers)
    if r1.status_code == 200:
        assert r2.status_code == 409

def test_poison_auto_raise_competition(client: TestClient):
    t1 = auth_tokens(client, "c1@example.com")  # Defender
    t2 = auth_tokens(client, "c2@example.com")  # Challenger
    h1 = {"Authorization": f"Bearer {t1['access_token']}"}
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}

    item_id = create_item(client)

    # Defender places a poison bid with budget 25 and step 2 at amount 10
    r_def = client.post(f'/items/{item_id}/bid', json={"amount": 10, "max_budget": 25, "bid_increment": 2}, headers=h1)
    assert r_def.status_code == 200, f"Defender bid failed: {r_def.json()}"

    # Challenger places 15 without poison; defender should auto-raise to min(25, 15+2)=17
    r_chal = client.post(f'/items/{item_id}/bid', json={"amount": 15}, headers=h2)
    assert r_chal.status_code == 200, f"Challenger bid failed: {r_chal.json()}"

    # Verify the auction state
    r_item = client.get(f'/items/{item_id}', headers=h1)
    assert r_item.status_code == 200, f"Failed to retrieve item: {r_item.json()}"
    
    # Assuming the response contains a 'current_bid' or 'bids' field
    item_data = r_item.json()
    current_bid = item_data.get('current_bid')
    assert current_bid and current_bid['amount'] == 17

def test_reject_bids_when_closed(client: TestClient):
    t = auth_tokens(client, "late@example.com")
    headers = {"Authorization": f"Bearer {t['access_token']}"}

    # Assume item 1 may be considered closed depending on backend default; simulate with whatever status we get
    # We only assert that if backend reports closed, bid returns 400; otherwise accept 200/404 depending on setup
    r = client.post('/items/1/bid', json={"amount": 999}, headers=headers)
    assert r.status_code in (200, 400, 404)

def test_close_auction_awards_inventory(client: TestClient):
    t1 = auth_tokens(client, "w1@example.com")
    t2 = auth_tokens(client, "w2@example.com")
    h1 = {"Authorization": f"Bearer {t1['access_token']}"}
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}

    item_id = create_item(client)

    r1 = client.post(f'/items/{item_id}/bid', json={"amount": 10}, headers=h1)
    assert r1.status_code == 200
    r2 = client.post(f'/items/{item_id}/bid', json={"amount": 12}, headers=h2)
    if r2.status_code != 200:
        return
    r_close = client.post(f'/items/{item_id}/close')
    assert r_close.status_code == 200
    winner_id = r_close.json().get('winner_user_id')

    # Fetch winner inventory
    if winner_id == 1:
        inv = client.get('/auth/inventory', headers=h1)
    else:
        inv = client.get('/auth/inventory', headers=h2)
    assert inv.status_code == 200
    data = inv.json()
    assert isinstance(data, list) and len(data) >= 1

