// Burn List search — filters table rows by normalized golfer name.
// Mirrors the make-pick picker: strip punctuation/spaces so "jj" matches "J.J."
(function () {
    'use strict';

    var input = document.getElementById('burn-search');
    var table = document.querySelector('[data-burn-table]');
    if (!input || !table) return;  // empty state: nothing to wire

    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    var count = document.querySelector('[data-burn-count]');
    var miss = document.querySelector('[data-burn-miss]');

    function normalize(s) {
        return (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    }

    input.addEventListener('input', function () {
        var q = normalize(input.value);
        var shown = 0;
        rows.forEach(function (row) {
            var hit = !q || normalize(row.cells[0].textContent).indexOf(q) !== -1;
            row.hidden = !hit;
            if (hit) shown += 1;
        });
        if (count) {
            count.textContent = shown + (shown === 1 ? ' golfer burned' : ' golfers burned');
        }
        if (miss) miss.hidden = shown !== 0;
        table.hidden = shown === 0;
    });
})();
