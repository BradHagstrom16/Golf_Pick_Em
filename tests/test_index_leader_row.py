"""
Tests: the standings leader-row highlight on the index page.

The first standings row carries row-leader EXCEPT when it is the signed-in
viewer's own row, where the gold row-current-user identity wins. The template
uses an elif, so the classes are mutually exclusive; a future refactor to two
independent ifs would double-class the leader's own row, and the mint
row-leader fill would override their gold tint by source order.
"""


def _row_slice(html, css_class):
    """Return the <tr> ... </tr> slice whose class attribute is css_class."""
    start = html.index(f'<tr class="{css_class}">')
    return html[start:html.index('</tr>', start)]


def test_logged_out_first_row_is_leader(db, client, make_user):
    make_user(display_name='Lead Dog', total_points=2_000_000)
    make_user(display_name='Chaser', total_points=1_000_000)
    html = client.get('/').get_data(as_text=True)
    assert html.count('row-leader') == 1
    assert 'row-current-user' not in html
    assert 'Lead Dog' in _row_slice(html, 'row-leader')


def test_logged_in_non_leader_gets_both_highlights_on_distinct_rows(
        db, client, make_user, login):
    make_user(display_name='Lead Dog', total_points=2_000_000)
    chaser = make_user(display_name='Chaser', total_points=1_000_000)
    login(chaser)
    html = client.get('/').get_data(as_text=True)
    assert 'Lead Dog' in _row_slice(html, 'row-leader')
    assert 'Chaser' in _row_slice(html, 'row-current-user')


def test_logged_in_leader_keeps_identity_gold_not_leader_mint(
        db, client, make_user, login):
    leader = make_user(display_name='Lead Dog', total_points=2_000_000)
    make_user(display_name='Chaser', total_points=1_000_000)
    login(leader)
    html = client.get('/').get_data(as_text=True)
    # self-identity wins: the leader's own row is gold, never double-classed mint
    assert 'row-leader' not in html
    assert 'Lead Dog' in _row_slice(html, 'row-current-user')
