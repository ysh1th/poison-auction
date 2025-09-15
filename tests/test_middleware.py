"""Middleware tests: verify X-Request-ID header is injected."""

def test_request_id_header(client):
    """Checks that every response contains X-Request-ID header."""
    r = client.get('/auth/login')
    assert 'X-Request-ID' in r.headers

