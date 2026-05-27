"""Tests for admin reset-password auto-generate (Bug A) and payment-toggle failure surfacing (Bug B)."""
import re

import pytest


# ---------------------------------------------------------------------------
# Bug A: blank reset auto-generates a non-guessable password
# ---------------------------------------------------------------------------

def test_reset_blank_autogenerates_non_guessable(db, login, make_user):
    admin = make_user(username='radmin', is_admin=True)
    target = make_user(username='rtarget')
    db.session.commit()
    resp = login(admin).post(f'/admin/reset-password/{target.id}',
                             data={'new_password': ''}, follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(target)
    assert not target.check_password(f'golf{target.id}'), 'must not be the guessable golf{id}'
    assert not target.check_password('pw'), 'password must have changed'
    m = re.search(r'Temporary password for .*?: (\S+)', resp.get_data(as_text=True))
    assert m, 'generated password must be surfaced once in the flash'
    assert target.check_password(m.group(1)), 'the surfaced password must be the one actually set'


def test_reset_explicit_password_still_works(db, login, make_user):
    admin = make_user(username='radmin2', is_admin=True)
    target = make_user(username='rtarget2')
    db.session.commit()
    login(admin).post(f'/admin/reset-password/{target.id}',
                      data={'new_password': 'chosen-secret'}, follow_redirects=True)
    db.session.refresh(target)
    assert target.check_password('chosen-secret')


# ---------------------------------------------------------------------------
# Bug B: payment toggle no longer silently swallows failures
# ---------------------------------------------------------------------------

def test_payment_toggle_surfaces_failure(db, login, make_user):
    admin = make_user(username='padmin', is_admin=True)
    db.session.commit()
    html = login(admin).get('/admin/payments').get_data(as_text=True)
    assert 'payment-toggle' in html
    assert '.catch(' in html, 'toggle must handle network failure'
    assert 'Could not update payment status' in html, 'failed toggle must be surfaced, not swallowed'
