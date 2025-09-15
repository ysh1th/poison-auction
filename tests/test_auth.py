"""Auth flow tests: register, login, refresh rotation, and logout."""

def test_register_login_refresh_logout(client):
    """Ensures a user can register, obtain tokens, rotate refresh, and logout."""
    r = client.post('/auth/register', json={"email":"a@example.com","password":"pass","role":"viewer"})
    assert r.status_code == 200
    r = client.post('/auth/login', data={"username":"a@example.com","password":"pass"})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    r = client.post('/auth/refresh', json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_tokens = r.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    r = client.post('/auth/logout', headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
    assert r.status_code == 200

