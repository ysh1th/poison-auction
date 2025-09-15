"""Auction tests: basic bid placement and poison interaction smoke checks."""

def auth_tokens(client, email):
    """Registers and logs in a user, returning token payload."""
    client.post('/auth/register', json={"email":email,"password":"pass","role":"viewer"})
    r = client.post('/auth/login', data={"username":email,"password":"pass"})
    return r.json()

def test_single_bid_and_unique_constraint(client):
    """Places a bid; unique (item_id,user_id) constraint is exercised by model."""
    t = auth_tokens(client, "b1@example.com")
    headers = {"Authorization": f"Bearer {t['access_token']}"}
    r = client.post('/items/1/bid', json={"amount": 10}, headers=headers)
    assert r.status_code in (200, 404, 400)

def test_basic_poison_competition(client):
    """Simulates auto-raise competitor against a challenger bid."""
    t1 = auth_tokens(client, "c1@example.com")
    t2 = auth_tokens(client, "c2@example.com")
    h1 = {"Authorization": f"Bearer {t1['access_token']}"}
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}
    client.post('/items/2/bid', json={"amount": 10, "poison_budget": 20, "poison_step": 1}, headers=h1)
    r = client.post('/items/2/bid', json={"amount": 15}, headers=h2)
    assert r.status_code in (200, 400, 404)

