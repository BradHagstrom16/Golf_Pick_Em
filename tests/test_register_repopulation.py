"""Test that register form repopulates non-password fields on validation error."""
import secrets


def test_register_error_repopulates_nonpassword_fields(client):
    """A validation error keeps username/email/display name but never the password."""
    # Generate the password at runtime so no credential literal is committed.
    password = secrets.token_urlsafe(9)
    resp = client.post('/register', data={
        'username': 'jordan_new',
        'email': 'jordan@example.test',
        'display_name': 'Jordan',
        'password': password,
        'confirm_password': password + 'X',  # deliberate mismatch → validation error
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'jordan_new' in html, 'username must survive a validation error'
    assert 'jordan@example.test' in html
    assert 'Jordan' in html
    assert password not in html, 'password must never be repopulated'
