"""Tests for override_pick admin page: USED options disabled, no alert() guard."""
import re


def test_override_used_player_option_is_disabled_and_no_alert(db, login, make_user, make_player, make_tournament):
    from models import TournamentField, SeasonPlayerUsage
    admin = make_user(username='ovadmin6', is_admin=True)
    member = make_user(username='ovmember6')
    used_p = make_player(first_name='Used', last_name='Golfer')
    free_p = make_player(first_name='Free', last_name='Golfer')
    t = make_tournament(name='Override Field', status='upcoming')
    db.session.add(TournamentField(tournament_id=t.id, player_id=used_p.id))
    db.session.add(TournamentField(tournament_id=t.id, player_id=free_p.id))
    db.session.add(SeasonPlayerUsage(user_id=member.id, player_id=used_p.id, season_year=t.season_year))
    db.session.commit()

    resp = login(admin).post('/admin/override-pick',
                             data={'tournament_id': t.id, 'user_id': member.id, 'load_field': '1'})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '(USED)' in html, 'USED suffix should render'
    assert 'alert(' not in html, 'same-player guard must not use a native alert'
    # The used player's <option> must carry disabled; the free player's must not.
    # Anchor to options that contain the (USED) text to avoid matching same id in tournament select.
    used_opt = re.search(
        r'<option value="%d"[^>]*>.*?\(USED\).*?</option>' % used_p.id, html, re.S
    )
    # Free player option: match option containing the player's last name ("Golfer, Free" order).
    free_opt = re.search(
        r'<option value="%d".*?</option>' % free_p.id, html, re.S
    )
    # Find ALL matches of the free player id to get the player-select occurrence, not tournament.
    free_opts = list(re.finditer(r'<option value="%d".*?</option>' % free_p.id, html, re.S))
    # The free player option is in the player selects; filter by containing the player's last name.
    free_player_opts = [m for m in free_opts if 'Golfer' in m.group(0)]
    assert used_opt and 'disabled' in used_opt.group(0), 'USED option must be disabled'
    assert free_player_opts and all('disabled' not in m.group(0) for m in free_player_opts), \
        'available option must remain selectable'
