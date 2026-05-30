/* ============================================================================
 * The Replay — "Play the season" for the Stats Hub race chart.
 *
 * Progressive enhancement only. The server renders the finished race (full
 * lines, final standings); this script reveals the controls and lets a member
 * play or scrub the season week by week. A vertical playhead sweeps the chart,
 * the lines reveal up to it (SVG clip), gold/green batons ride the leader and
 * "you" lines, and the standings list below re-orders (FLIP) so the lead
 * changing hands is something you watch happen.
 *
 * No data island, no JS, or a single-event season => nothing runs and the
 * static chart stands on its own.
 * ========================================================================== */
(function () {
  'use strict';

  function init() {
    var figure = document.querySelector('[data-race-replay]');
    var dataEl = document.querySelector('[data-race-replay-data]');
    if (!figure || !dataEl) return;

    var data;
    try {
      data = JSON.parse(dataEl.textContent);
    } catch (e) {
      return; // malformed payload: leave the static chart untouched
    }
    if (!data || !data.count || data.count < 2) return;

    var count = data.count;
    var width = data.width;
    var events = data.events;
    var lines = data.lines;
    var lastIndex = count - 1;

    var reduceMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- elements -----------------------------------------------------------
    var plot = figure.querySelector('.season-race__plot');
    var clipRect = figure.querySelector('[data-race-clip]');
    var playhead = figure.querySelector('[data-race-playhead]');
    var readout = figure.querySelector('[data-race-readout]');
    var readoutEvent = figure.querySelector('[data-race-readout-event]');
    var controls = figure.querySelector('[data-race-controls]');
    var playBtn = figure.querySelector('[data-race-play]');
    var playText = playBtn && playBtn.querySelector('.season-race__play-text');
    var scrubWrap = figure.querySelector('[data-race-scrub-wrap]');
    var scrub = figure.querySelector('[data-race-scrub]');
    var standings = document.querySelector('[data-race-standings]');
    var batons = {};
    Array.prototype.forEach.call(figure.querySelectorAll('[data-race-baton]'), function (el) {
      batons[el.getAttribute('data-race-baton')] = el;
    });

    if (!clipRect || !playhead || !standings) return;

    // role -> line (for the batons). 'leader'/'you' may be absent.
    var lineByRole = {};
    lines.forEach(function (l) { lineByRole[l.role] = l; });

    // user_id -> standings row + its mutable spans.
    var rows = {};
    var rowEls = Array.prototype.slice.call(standings.querySelectorAll('[data-race-row]'));
    rowEls.forEach(function (row) {
      var id = row.getAttribute('data-user-id');
      rows[id] = {
        row: row,
        rank: row.querySelector('[data-race-rank]'),
        value: row.querySelector('[data-race-value]'),
        move: row.querySelector('[data-race-move]')
      };
    });

    // --- helpers ------------------------------------------------------------
    function money(n) { return '$' + Math.round(n).toLocaleString('en-US'); }
    function easeOutQuart(t) { return 1 - Math.pow(1 - t, 4); }
    function lerp(a, b, f) { return a + (b - a) * f; }

    // Ranked ordering of members at event k: by cumulative desc, then name.
    function orderingAt(k) {
      var arr = lines.map(function (l) {
        return { id: String(l.user_id), value: l.cumulative[k], name: l.name };
      });
      arr.sort(function (a, b) {
        return b.value - a.value || a.name.localeCompare(b.name);
      });
      return arr;
    }
    function rankMap(order) {
      var m = {};
      order.forEach(function (o, i) { m[o.id] = i + 1; });
      return m;
    }

    function animateValue(el, from, to, dur) {
      if (el._raf) { cancelAnimationFrame(el._raf); el._raf = null; }
      if (reduceMotion || dur <= 0 || from === to) { el.textContent = money(to); return; }
      var start = performance.now();
      function tick(now) {
        var t = Math.min(1, (now - start) / dur);
        el.textContent = money(from + (to - from) * easeOutQuart(t));
        el._raf = t < 1 ? requestAnimationFrame(tick) : null;
      }
      el._raf = requestAnimationFrame(tick);
    }

    // --- standings re-order (FLIP) -----------------------------------------
    var displayed = lastIndex; // event the standings currently reflect

    function applyStandings(k, fromK, animate) {
      var order = orderingAt(k);
      var ranks = rankMap(order);
      var weekAgo = k > 0 ? rankMap(orderingAt(k - 1)) : null;

      // FLIP: First (capture current positions).
      var firstTop = {};
      order.forEach(function (o) {
        firstTop[o.id] = rows[o.id].row.getBoundingClientRect().top;
      });

      // Reorder the DOM.
      order.forEach(function (o) { standings.appendChild(rows[o.id].row); });

      // Last + Invert + Play, plus content updates.
      order.forEach(function (o) {
        var entry = rows[o.id];
        var rank = ranks[o.id];

        if (animate && !reduceMotion) {
          var dy = firstTop[o.id] - entry.row.getBoundingClientRect().top;
          if (dy) {
            entry.row.style.transition = 'none';
            entry.row.style.transform = 'translateY(' + dy + 'px)';
            entry.row.getBoundingClientRect();           // force reflow
            entry.row.style.transition = '';
            entry.row.style.transform = '';
          }
        } else {
          entry.row.style.transform = '';
        }

        entry.rank.textContent = rank;
        animateValue(entry.value, fromK != null ? lines2cum(o.id, fromK) : o.value,
                     o.value, animate ? 420 : 0);

        // Movement vs the previous event (this week vs last), not scrub history.
        var cls = 'race-standings__move';
        var glyph = '';
        if (weekAgo && weekAgo[o.id] != null) {
          if (rank < weekAgo[o.id]) { cls += ' race-standings__move--up'; glyph = '▲'; }
          else if (rank > weekAgo[o.id]) { cls += ' race-standings__move--down'; glyph = '▼'; }
        }
        entry.move.className = cls;
        entry.move.textContent = glyph;

        entry.row.classList.toggle('race-standings__row--leader', rank === 1);
      });
    }

    var cumById = {};
    lines.forEach(function (l) { cumById[String(l.user_id)] = l.cumulative; });
    function lines2cum(id, k) { return cumById[id][k]; }

    // --- frame render -------------------------------------------------------
    function render(p, animateStandings) {
      var k0 = Math.floor(p);
      var k1 = Math.min(k0 + 1, lastIndex);
      var f = p - k0;
      var x = lerp(events[k0].x, events[k1].x, f);
      var atFinal = p >= lastIndex - 1e-6 && !playing;

      // Reveal lines up to the playhead (full width once we settle at the end).
      clipRect.setAttribute('width', (p >= lastIndex - 1e-6 ? width : x).toFixed(1));
      playhead.setAttribute('x1', x.toFixed(1));
      playhead.setAttribute('x2', x.toFixed(1));

      ['leader', 'you'].forEach(function (role) {
        var baton = batons[role];
        var line = lineByRole[role];
        if (!baton || !line) return;
        var y = lerp(line.coords[k0][1], line.coords[k1][1], f);
        baton.setAttribute('cx', x.toFixed(1));
        baton.setAttribute('cy', y.toFixed(1));
      });

      var idx = Math.round(p);
      if (plot) plot.style.setProperty('--ph', x / width);
      if (readoutEvent) readoutEvent.textContent = events[idx].name;
      if (scrub) scrub.value = idx;

      figure.classList.toggle('season-race--scrubbing', !atFinal);

      if (idx !== displayed) {
        applyStandings(idx, displayed, animateStandings);
        displayed = idx;
      }
    }

    // --- autoplay timeline --------------------------------------------------
    var SEG = 520, HOLD = 220;                 // glide + dwell per event (ms)
    var STRIDE = SEG + HOLD;
    var total = lastIndex * STRIDE + HOLD;
    var playing = false;
    var rafId = null;
    var startTime = 0;

    function progressAt(t) {
      var e = Math.floor(t / STRIDE);
      if (e >= lastIndex) return lastIndex;
      var local = t - e * STRIDE;
      if (local <= HOLD) return e;
      return e + easeOutQuart((local - HOLD) / SEG);
    }

    function frame(now) {
      var t = now - startTime;
      // Stop first so the final render sees playing=false and settles to the
      // idle state (playhead/readout hidden, end labels back, lines full).
      if (t >= total) { stopPlay(); render(lastIndex, true); return; }
      render(progressAt(t), true);
      rafId = requestAnimationFrame(frame);
    }

    function setPlayLabel(isPlaying) {
      if (!playBtn) return;
      playBtn.classList.toggle('is-playing', isPlaying);
      var label = isPlaying ? 'Pause' : 'Play the season';
      if (playText) playText.textContent = label;
      playBtn.setAttribute('aria-label', label);
    }

    function startPlay() {
      playing = true;
      setPlayLabel(true);
      render(0, false);                        // snap to the starting grid
      startTime = performance.now();
      rafId = requestAnimationFrame(frame);
    }

    function stopPlay() {
      playing = false;
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
      setPlayLabel(false);
    }

    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (playing) { stopPlay(); render(displayed, false); }
        else { startPlay(); }
      });
    }

    if (scrub) {
      scrub.addEventListener('input', function () {
        if (playing) stopPlay();
        var k = parseInt(scrub.value, 10) || 0;
        scrub.setAttribute('aria-valuetext', events[k].name);
        render(k, false);                      // direct manipulation: snappy
      });
    }

    // --- reveal + idle state ------------------------------------------------
    if (scrub && scrubWrap) {
      // Align the track to the chart's plotted area so the thumb lands on events.
      scrubWrap.style.paddingLeft = (data.pad_left / width * 100) + '%';
      scrubWrap.style.paddingRight = (data.pad_right / width * 100) + '%';
      scrubWrap.removeAttribute('hidden');
    }
    if (readout) readout.removeAttribute('hidden');
    // Auto-motion is opt-in for reduced-motion users; the scrubber stays.
    if (controls && !reduceMotion) controls.removeAttribute('hidden');

    render(lastIndex, false);                  // matches the server-rendered final state
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
