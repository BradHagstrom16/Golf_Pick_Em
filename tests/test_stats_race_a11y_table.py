"""
Test: the Season Race's screen-reader mirror table must not stretch the page.

Bootstrap's .visually-hidden clamps elements to 1x1px, but tables treat
``width`` as a *minimum* (CSS table layout), so a ``<table>`` carrying the
class still lays out at min-content width — on /stats that stretched
``document.scrollWidth`` to ~965px at a 375px viewport (a phantom horizontal
page scroll on phones). The class belongs on a wrapper <div>, which clamps
fine; the table inside it is hidden with the wrapper.
"""


def _seed_completed_event(db, make_user, make_player, make_tournament, make_pick):
    """One complete tournament with a resolved pick so the race section renders."""
    user = make_user(display_name='Racer')
    primary = make_player(last_name='Primary')
    backup = make_player(last_name='Backup')
    t = make_tournament(name='Race Seed Open', status='complete')
    make_pick(user, t, primary, backup,
              active_player_id=primary.id, points_earned=1_000_000)
    db.session.commit()


def test_sr_mirror_table_is_wrapped_not_classed(
        db, client, make_user, make_player, make_tournament, make_pick):
    _seed_completed_event(db, make_user, make_player, make_tournament, make_pick)
    html = client.get('/stats').get_data(as_text=True)

    caption = 'Cumulative earnings by member after each completed event'
    assert caption in html  # the a11y mirror still renders

    # the clamp lives on a wrapper div immediately around the table...
    start = html.index(caption)
    prefix = html[max(0, start - 400):start]
    assert '<div class="visually-hidden">' in prefix

    # ...never on the table itself, where it can't bite
    assert '<table class="visually-hidden">' not in html
