"""Stats Hub aggregation layer.

Pure, query-only functions that turn the season's accumulated picks and results
into the data the Stats Hub renders. Kept out of app.py so each piece stays small
and unit-testable. Every function restricts to ``status='complete'`` so live /
projected earnings never leak into season stats.

Two money concepts live here and must not be confused:

- **Member points** = ``Pick.points_earned``. Already includes the major x1.5 and
  Zurich team /2 multipliers. Used for the race, superlatives, and return-when-picked.
- **Golfer prize** = raw ``TournamentResult.earnings`` (actual PGA money, full field).
  Used for the form guide and untouched stars.
"""
import math

from sqlalchemy import and_, func

from models import (
    db,
    User,
    Player,
    SeasonPlayerUsage,
    Tournament,
    TournamentResult,
    Pick,
)

# Display limits for the golfer-focused tables.
FORM_GUIDE_LIMIT = 10
UNTOUCHED_LIMIT = 5

# Race-chart end labels are 12px text in SVG user units; keep at least this much
# vertical separation so neck-and-neck names never print on top of each other.
LABEL_MIN_SEP = 15
# Estimated width of one end-label character (12px bold Plus Jakarta Sans), used
# to size the right gutter to the names it must hold.
LABEL_CHAR_W = 7


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------
def format_money_compact(n):
    """Compact money for axis ticks and chips: $0, $950, $25K, $1.2M."""
    n = int(n or 0)
    if abs(n) >= 1_000_000:
        return f'${n / 1_000_000:.1f}M'
    if abs(n) >= 1_000:
        return f'${round(n / 1_000)}K'
    return f'${n}'


def _nice_axis(value, max_ticks=5):
    """Round axis ceiling and tick step for a money axis.

    Returns ``(axis_max, step)`` where ``step`` is a 1/2/2.5/5 x 10^n value and
    ``axis_max`` is the smallest multiple of ``step`` that covers ``value`` in at
    most ``max_ticks`` intervals. Keeps gridlines on round money ($0, $500K, $1M)
    instead of raw max/steps fractions ($549K). ``value <= 0`` yields a 0..1 axis.
    """
    if value <= 0:
        return 1, 1
    magnitude = 10 ** math.floor(math.log10(value))
    for mult in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10):
        step = mult * magnitude
        intervals = math.ceil(value / step)
        if intervals <= max_ticks:
            return int(intervals * step), int(step)
    return int(value), int(value)


def _user_name(user_id):
    user = db.session.get(User, user_id)
    return user.get_display_name() if user else f'User {user_id}'


def _finish_sort_key(position):
    """Numeric sort key for a finish string ('1', 'T5'); None for non-numeric (CUT/WD)."""
    if not position:
        return None
    stripped = str(position).strip().upper().lstrip('T')
    try:
        return int(stripped)
    except ValueError:
        return None


def _completed_pick_query(season_year):
    """Picks in completed tournaments of the season, with resolved points."""
    return (Pick.query
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    Pick.points_earned.isnot(None)))


# ---------------------------------------------------------------------------
# Season progress + the race
# ---------------------------------------------------------------------------
def season_progress(season_year):
    """How far into the season we are: completed vs total events."""
    completed = Tournament.query.filter_by(status='complete', season_year=season_year).count()
    total = Tournament.query.filter_by(season_year=season_year).count()
    return {'completed': completed, 'total': total}


def season_race(season_year):
    """Cumulative-earnings trajectory per member across completed events.

    Returns ordered tournaments, one series per participating member (sorted by
    final total desc), and the max cumulative value for y-scaling.
    """
    tournaments = (Tournament.query
                   .filter_by(status='complete', season_year=season_year)
                   .order_by(Tournament.start_date, Tournament.id)
                   .all())
    t_list = [{'id': t.id, 'name': t.name, 'short': t.start_date.strftime('%b'),
               'start_date': t.start_date} for t in tournaments]
    if not tournaments:
        return {'tournaments': [], 'series': [], 'max_value': 0, 'count': 0}

    t_index = {t.id: i for i, t in enumerate(tournaments)}

    rows = (db.session.query(
                Pick.user_id, Pick.tournament_id,
                func.coalesce(func.sum(Pick.points_earned), 0))
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    Pick.points_earned.isnot(None))
            .group_by(Pick.user_id, Pick.tournament_id)
            .all())

    per_user = {}
    for uid, tid, pts in rows:
        arr = per_user.setdefault(uid, [0] * len(tournaments))
        arr[t_index[tid]] = int(pts or 0)

    if not per_user:
        return {'tournaments': t_list, 'series': [], 'max_value': 0, 'count': len(tournaments)}

    users = {u.id: u for u in User.query.filter(User.id.in_(list(per_user.keys()))).all()}

    series = []
    for uid, arr in per_user.items():
        cumulative, running = [], 0
        for value in arr:
            running += value
            cumulative.append(running)
        user = users.get(uid)
        series.append({
            'user_id': uid,
            'name': user.get_display_name() if user else f'User {uid}',
            'cumulative': cumulative,
            'final': running,
        })

    series.sort(key=lambda s: (-s['final'], s['name']))
    for i, entry in enumerate(series):
        entry['rank'] = i + 1
        entry['is_leader'] = (i == 0)

    return {
        'tournaments': t_list,
        'series': series,
        'max_value': max((s['final'] for s in series), default=0),
        'count': len(tournaments),
    }


def race_chart_geometry(race, current_user_id=None, width=720, height=320,
                        pad_left=12, pad_right=78, pad_top=18, pad_bottom=34):
    """Convert a ``season_race`` payload into SVG coordinates (pure math).

    Keeps trig/scaling out of the template. Returns polyline point strings, axis
    ticks, and per-line role ('you' | 'leader' | 'pack') for stroke styling.
    """
    count = race['count']
    axis_max, tick_step = _nice_axis(race['max_value'])

    # Size the right gutter to the names it must label (you + leader; just the
    # leader for a signed-out viewer) so a long display name never hangs off the
    # card; capped so one extreme name can't crush the plot. Pack lines carry no
    # labels and reserve nothing.
    labeled_names = [s['name'] for s in race['series']
                     if s['user_id'] == current_user_id or s['is_leader']]
    if labeled_names:
        longest = max(len(name) for name in labeled_names)
        pad_right = max(pad_right, min(150, 11 + LABEL_CHAR_W * longest))

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    baseline_y = height - pad_bottom

    def x_at(i):
        if count <= 1:
            return pad_left
        return pad_left + plot_w * i / (count - 1)

    def y_at(v):
        return baseline_y - plot_h * (v / axis_max)

    # Tick labels print inside the plot, just above each gridline (ledger style).
    # $0 keeps its gridline but loses its text: the baseline + month row already
    # read as the floor, and an inside label would collide with the line starts.
    n_ticks = axis_max // tick_step
    y_ticks = [{
        'value': value,
        'label': format_money_compact(value) if value else '',
        'y': y_at(value),
    } for value in (i * tick_step for i in range(n_ticks + 1))]

    # Collapse consecutive duplicate month labels: two events in the same month
    # render the month once (at the first), not 'Mar Mar'.
    x_ticks, prev_label = [], None
    for i, t in enumerate(race['tournaments']):
        if t['short'] != prev_label:
            x_ticks.append({'index': i, 'label': t['short'], 'x': x_at(i)})
            prev_label = t['short']

    lines = []
    for s in race['series']:
        # coords feed the replay payload; they must parse-equal the polyline
        # points string below, so derive both from the same %.1f formatting.
        coords = [[float(f'{x_at(i):.1f}'), float(f'{y_at(v):.1f}')]
                  for i, v in enumerate(s['cumulative'])]
        points = ' '.join(f'{x},{y}' for x, y in coords)
        if s['user_id'] == current_user_id:
            role = 'you'
        elif s['is_leader']:
            role = 'leader'
        else:
            role = 'pack'
        end_y = y_at(s['cumulative'][-1]) if s['cumulative'] else baseline_y
        lines.append({
            'user_id': s['user_id'],
            'name': s['name'],
            'role': role,
            'points': points,
            'coords': coords,
            'cumulative': s['cumulative'],
            'end_x': x_at(count - 1) if count else pad_left,
            'end_y': end_y,
            'label_y': end_y + 3,   # +3: nudge the CSS-centered label down off the line tip
            'final': s['final'],
            'final_label': format_money_compact(s['final']),
        })

    # Neck-and-neck guard: when the member's and the leader's lines finish within
    # LABEL_MIN_SEP of each other, spread the two name labels around their
    # midpoint, then shift the pair (never each alone) back inside the plot.
    labeled = [line for line in lines if line['role'] in ('leader', 'you')]
    if len(labeled) == 2:
        upper, lower = sorted(labeled, key=lambda line: line['label_y'])
        if lower['label_y'] - upper['label_y'] < LABEL_MIN_SEP:
            mid = (upper['label_y'] + lower['label_y']) / 2
            upper['label_y'] = mid - LABEL_MIN_SEP / 2
            lower['label_y'] = mid + LABEL_MIN_SEP / 2
            lo, hi = pad_top + 6, baseline_y - 4
            if upper['label_y'] < lo:
                shift = lo - upper['label_y']
            elif lower['label_y'] > hi:
                shift = hi - lower['label_y']
            else:
                shift = 0
            upper['label_y'] += shift
            lower['label_y'] += shift

    # One stop per event for the client-side "Play the season" scrubber. Unlike
    # x_ticks, every event keeps its own stop (no month dedupe). None when there's
    # nothing to scrub (0 or 1 event), so the template can hide the controls.
    replay = None
    if count > 1:
        replay = {
            'count': count,
            'width': width, 'height': height,
            'pad_left': pad_left, 'pad_right': pad_right,
            'baseline_y': baseline_y,
            'events': [{'name': t['name'], 'short': t['short'],
                        'x': float(f'{x_at(i):.1f}')}
                       for i, t in enumerate(race['tournaments'])],
            'lines': [{'user_id': line['user_id'], 'name': line['name'],
                       'role': line['role'], 'coords': line['coords'],
                       'cumulative': line['cumulative'], 'final': line['final']}
                      for line in lines],
        }

    return {
        'width': width, 'height': height,
        'pad_left': pad_left, 'pad_right': pad_right,
        'pad_top': pad_top, 'pad_bottom': pad_bottom,
        'baseline_y': baseline_y, 'plot_w': plot_w, 'plot_h': plot_h,
        'lines': lines, 'y_ticks': y_ticks, 'x_ticks': x_ticks,
        'replay': replay,
    }


# ---------------------------------------------------------------------------
# Superlatives
# ---------------------------------------------------------------------------
def superlatives(season_year):
    """The season's award statements."""
    return {
        'pick_of_season': _pick_of_season(season_year),
        'most_cuts': _most_cuts(season_year),
        'wd_survivor': _wd_survivor(season_year),
        'coldest_pick': _coldest_pick(season_year),
        'most_cashes': _most_cashes(season_year),
    }


def _pick_of_season(season_year):
    pick = (_completed_pick_query(season_year)
            .order_by(Pick.points_earned.desc(), Pick.id)
            .first())
    if not pick:
        return None
    golfer = pick.active_player or pick.primary_player
    return {
        'member': pick.user.get_display_name(),
        'golfer': golfer.full_name() if golfer else '—',
        'event': pick.tournament.name,
        'amount': pick.points_earned,
    }


def _most_cuts(season_year):
    rows = (db.session.query(Pick.user_id, func.count(Pick.id))
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .join(TournamentResult, and_(
                TournamentResult.tournament_id == Pick.tournament_id,
                TournamentResult.player_id == Pick.active_player_id))
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    TournamentResult.status.in_(['cut', 'dq']))
            .group_by(Pick.user_id)
            .order_by(func.count(Pick.id).desc())
            .all())
    if not rows:
        return None
    uid, count = rows[0]
    return {'member': _user_name(uid), 'count': int(count)}


def _wd_survivor(season_year):
    rows = (db.session.query(Pick.user_id, func.count(Pick.id))
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    Pick.backup_used.is_(True))
            .group_by(Pick.user_id)
            .order_by(func.count(Pick.id).desc())
            .all())
    if not rows:
        return None
    uid, count = rows[0]
    return {'member': _user_name(uid), 'count': int(count)}


def _coldest_pick(season_year):
    pick = (Pick.query
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    Pick.points_earned == 0)
            .order_by(Tournament.purse.desc(), Pick.id)
            .first())
    if not pick:
        return None
    golfer = pick.active_player or pick.primary_player
    return {
        'member': pick.user.get_display_name(),
        'golfer': golfer.full_name() if golfer else '—',
        'event': pick.tournament.name,
        'purse': pick.tournament.purse,
    }


def _most_cashes(season_year):
    base = (db.session.query(Pick.user_id, func.count(Pick.id))
            .join(Tournament, Pick.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    Pick.points_earned.isnot(None)))
    played = dict(base.group_by(Pick.user_id).all())
    # points_earned is non-negative and already filtered isnot(None), so != 0
    # means "in the money" — avoids ordering-operator typing on a nullable column.
    cashed = dict(base.filter(Pick.points_earned != 0).group_by(Pick.user_id).all())
    if not cashed:
        return None
    best = sorted(cashed, key=lambda uid: (-cashed[uid], played.get(uid, 0), _user_name(uid)))[0]
    return {'member': _user_name(best), 'cashes': cashed[best], 'played': played.get(best, 0)}


# ---------------------------------------------------------------------------
# The Field — golfer form + pool intel
# ---------------------------------------------------------------------------
def field_form(season_year):
    """Golfer-centric stats: form guide (raw prize), most-picked, untouched stars."""
    earn_rows = (db.session.query(
                    TournamentResult.player_id,
                    func.coalesce(func.sum(TournamentResult.earnings), 0),
                    func.count(TournamentResult.id))
                 .join(Tournament, TournamentResult.tournament_id == Tournament.id)
                 .filter(Tournament.status == 'complete',
                         Tournament.season_year == season_year)
                 .group_by(TournamentResult.player_id)
                 .order_by(func.coalesce(func.sum(TournamentResult.earnings), 0).desc())
                 .all())
    if not earn_rows:
        return {'form_guide': [], 'untouched_stars': []}

    cut_counts = dict(db.session.query(
                        TournamentResult.player_id, func.count(TournamentResult.id))
                      .join(Tournament, TournamentResult.tournament_id == Tournament.id)
                      .filter(Tournament.status == 'complete',
                              Tournament.season_year == season_year,
                              TournamentResult.status.in_(['cut', 'dq']))
                      .group_by(TournamentResult.player_id).all())

    earn_map = {pid: int(total or 0) for pid, total, _events in earn_rows}

    top_ids = [pid for pid, _total, _events in earn_rows[:FORM_GUIDE_LIMIT]]
    top_players = _player_map(top_ids)
    best_finish = _best_finishes(season_year, top_ids)
    form_guide = [{
        'golfer': _player_name(top_players, pid),
        'events': int(events),
        'prize': int(total or 0),
        'cuts': int(cut_counts.get(pid, 0)),
        'best_finish': best_finish.get(pid),
    } for pid, total, events in earn_rows[:FORM_GUIDE_LIMIT]]

    chosen = set()
    for primary, backup in (db.session.query(Pick.primary_player_id, Pick.backup_player_id)
                            .join(Tournament, Pick.tournament_id == Tournament.id)
                            .filter(Tournament.status == 'complete',
                                    Tournament.season_year == season_year).all()):
        chosen.update((primary, backup))
    untouched_ids = [pid for pid, _t, _e in earn_rows if pid not in chosen][:UNTOUCHED_LIMIT]
    untouched_players = _player_map(untouched_ids)
    untouched_stars = [{
        'golfer': _player_name(untouched_players, pid),
        'prize': earn_map.get(pid, 0),
    } for pid in untouched_ids]

    return {'form_guide': form_guide, 'untouched_stars': untouched_stars}


# ---------------------------------------------------------------------------
# The Burn List — field-usage percentages
# ---------------------------------------------------------------------------
def _usage_counts(season_year):
    """(total registered users, {player_id: burn count}) for the season.

    Sourced from SeasonPlayerUsage — the table that gates pick availability —
    so counts move only at finalization, never on in-flight picks.
    """
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    counts = dict(db.session.query(
                      SeasonPlayerUsage.player_id,
                      func.count(SeasonPlayerUsage.id))
                  .filter(SeasonPlayerUsage.season_year == season_year)
                  .group_by(SeasonPlayerUsage.player_id)
                  .all())
    return total_users, counts


def _pct(count, total):
    """Whole-number share of the field, safe when the league is empty."""
    return round(100 * count / total) if total else 0


def burn_list(season_year):
    """Every golfer the league has burned, most-burned first.

    Each row: golfer, times_used, pct_burned (share of ALL registered users,
    matching the standings denominator), and total_return (member points,
    multipliers included; 0 when usage exists without a matching completed
    pick, e.g. a manually inserted usage row). Order: pct desc, return desc,
    last name, then full name so equal rows never depend on query order.
    """
    total_users, counts = _usage_counts(season_year)
    if not counts:
        return []
    returns = dict(db.session.query(
                       Pick.active_player_id,
                       func.coalesce(func.sum(Pick.points_earned), 0))
                   .join(Tournament, Pick.tournament_id == Tournament.id)
                   .filter(Tournament.status == 'complete',
                           Tournament.season_year == season_year,
                           Pick.active_player_id.isnot(None))
                   .group_by(Pick.active_player_id)
                   .all())
    players = _player_map(list(counts))
    rows = []
    for pid, count in counts.items():
        player = players.get(pid)
        rows.append({
            'golfer': _player_name(players, pid),
            'times_used': int(count),
            'pct_burned': _pct(count, total_users),
            'total_return': int(returns.get(pid, 0) or 0),
            '_last': player.last_name if player else '',
        })
    rows.sort(key=lambda r: (-r['pct_burned'], -r['total_return'],
                             r['_last'], r['golfer']))
    for row in rows:
        del row['_last']
    return rows


def remaining_pct_map(season_year, player_ids):
    """{player_id: % of the field that still has them}; None before any burn.

    The value is the complement of the rounded burn % (100 - pct_burned) so
    the pick page and the Burn List always sum to exactly 100. Returns None
    (rather than an all-100 map) while the season has no usage rows, so the
    pick page can suppress the indicators entirely when there is no signal.
    """
    total_users, counts = _usage_counts(season_year)
    if not counts:
        return None
    return {pid: 100 - _pct(counts.get(pid, 0), total_users)
            for pid in player_ids}


def _player_map(player_ids):
    if not player_ids:
        return {}
    return {p.id: p for p in Player.query.filter(Player.id.in_(player_ids)).all()}


def _player_name(player_map, player_id):
    player = player_map.get(player_id)
    return player.full_name() if player else f'Player {player_id}'


def _best_finishes(season_year, player_ids):
    """Best (lowest) numeric finish per player, as the original position string."""
    if not player_ids:
        return {}
    rows = (db.session.query(TournamentResult.player_id, TournamentResult.final_position)
            .join(Tournament, TournamentResult.tournament_id == Tournament.id)
            .filter(Tournament.status == 'complete',
                    Tournament.season_year == season_year,
                    TournamentResult.player_id.in_(player_ids),
                    TournamentResult.status == 'complete')
            .all())
    best = {}
    for pid, position in rows:
        key = _finish_sort_key(position)
        if key is None:
            continue
        current = best.get(pid)
        if current is None or key < current[0]:
            best[pid] = (key, position)
    return {pid: value[1] for pid, value in best.items()}


# ---------------------------------------------------------------------------
# Personal scorecard
# ---------------------------------------------------------------------------
def personal_scorecard(user, season_year):
    """The logged-in member's own season at a glance."""
    # Season-scoped points per member, matching the race standings shown above and
    # the module-wide status='complete' rule. There is no per-season points table;
    # User.total_points is the app-wide lifetime tally, so rank/total are derived
    # here from this season's completed picks (identical in a single-season DB,
    # correct if seasons ever accumulate).
    points_by_user = dict(
        db.session.query(Pick.user_id, func.coalesce(func.sum(Pick.points_earned), 0))
        .join(Tournament, Pick.tournament_id == Tournament.id)
        .filter(Tournament.status == 'complete',
                Tournament.season_year == season_year,
                Pick.points_earned.isnot(None))
        .group_by(Pick.user_id).all())
    my_points = int(points_by_user.get(user.id, 0) or 0)
    higher = sum(1 for pts in points_by_user.values() if int(pts or 0) > my_points)

    completed = _completed_pick_query(season_year).filter(Pick.user_id == user.id)
    events_played = completed.count()
    cashes = completed.filter(Pick.points_earned != 0).count()  # in the money (non-negative)

    best = completed.order_by(Pick.points_earned.desc(), Pick.id).first()
    best_pick = None
    if best:
        golfer = best.active_player or best.primary_player
        best_pick = {
            'golfer': golfer.full_name() if golfer else '—',
            'event': best.tournament.name,
            'amount': best.points_earned,
        }

    cuts_at_majors = int(db.session.query(func.count(Pick.id))
                         .join(Tournament, Pick.tournament_id == Tournament.id)
                         .filter(Pick.user_id == user.id,
                                 Pick.penalty_triggered.is_(True),
                                 Tournament.season_year == season_year)
                         .scalar() or 0)

    return {
        'rank': higher + 1,
        'total': my_points,
        'best_pick': best_pick,
        'events_played': events_played,
        'cashes': cashes,
        'cuts_at_majors': cuts_at_majors,
        'penalty_outstanding': user.penalty_outstanding(season_year),
        'players_used': len(user.get_used_player_ids()),
    }
