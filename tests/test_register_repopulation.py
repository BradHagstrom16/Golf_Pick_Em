"""Test that register form repopulates non-password fields on validation error."""


def test_register_error_repopulates_nonpassword_fields(client):
    resp = client.post('/register', data={
        'username': 'jordan_new',
        'email': 'jordan@example.test',
        'display_name': 'Jordan',
        'password': 'secret1',
        'confirm_password': 'MISMATCH',
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'jordan_new' in html, 'username must survive a validation error'
    assert 'jordan@example.test' in html
    assert 'Jordan' in html
    assert 'secret1' not in html, 'password must never be repopulated'
