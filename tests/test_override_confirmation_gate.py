"""
Tests for the admin override pick confirmation gate (P0 fix).

When a complete-tournament override is submitted without confirm=1, the route
must show a consequence summary and write NOTHING to the DB.
When confirm=1 is present, it must commit + re-resolve exactly as before.
"""
import pytest


def test_complete_tournament_override_requires_confirm(db, login, make_user, make_player,
                                                       make_tournament, make_result, make_pick):
    from models import Pick, TournamentField, SeasonPlayerUsage
    admin = make_user(username='ovadmin', is_admin=True)
    member = make_user(username='ovmember')
    old_p = make_player(first_name='Patrick', last_name='Cantlay')
    new_p = make_player(first_name='Xander', last_name='Schauffele')
    backup = make_player(first_name='Backup', last_name='Golfer')
    done = make_tournament(name='RBC Heritage', status='complete')
    for p in (old_p, new_p, backup):
        db.session.add(TournamentField(tournament_id=done.id, player_id=p.id))
    make_result(done, new_p, status='complete', earnings=1_000_000)
    make_pick(member, done, primary=old_p, backup=backup)
    db.session.commit()

    resp = login(admin).post('/admin/override-pick', data={
        'tournament_id': done.id, 'user_id': member.id,
        'primary_player_id': new_p.id, 'backup_player_id': backup.id,
    })
    body = resp.get_data(as_text=True).lower()
    assert 'recalculat' in body or 'confirm' in body, 'must surface the re-resolve consequence'
    pick = Pick.query.filter_by(user_id=member.id, tournament_id=done.id).first()
    assert pick.primary_player_id == old_p.id, 'must not commit without confirm'
    assert pick.points_earned is None, 'must not have re-resolved'
    assert SeasonPlayerUsage.query.filter_by(user_id=member.id).count() == 0, 'no usage leak from the preview'


def test_complete_tournament_override_with_confirm_commits(db, login, make_user, make_player,
                                                           make_tournament, make_result, make_pick):
    from models import Pick, TournamentField
    admin = make_user(username='ovadmin2', is_admin=True)
    member = make_user(username='ovmember2')
    old_p = make_player(first_name='Patrick', last_name='Reed')
    new_p = make_player(first_name='Xander', last_name='Day')
    backup = make_player(first_name='Backup', last_name='Two')
    done = make_tournament(name='Travelers', status='complete')
    for p in (old_p, new_p, backup):
        db.session.add(TournamentField(tournament_id=done.id, player_id=p.id))
    make_result(done, new_p, status='complete', earnings=1_000_000)
    make_pick(member, done, primary=old_p, backup=backup)
    db.session.commit()

    resp = login(admin).post('/admin/override-pick', data={
        'tournament_id': done.id, 'user_id': member.id,
        'primary_player_id': new_p.id, 'backup_player_id': backup.id,
        'confirm': '1',
    }, follow_redirects=True)
    pick = Pick.query.filter_by(user_id=member.id, tournament_id=done.id).first()
    assert pick.primary_player_id == new_p.id, 'confirm must commit the override'
    assert pick.admin_override is True
    assert pick.points_earned == 1_000_000, 'confirm must re-resolve (non-major, no multiplier)'
