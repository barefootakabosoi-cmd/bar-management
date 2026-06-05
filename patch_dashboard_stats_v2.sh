#!/usr/bin/env bash
set -euo pipefail

TEMPLATE="templates/dashboard.html"
PARTIAL_DIR="templates/partials"
PARTIAL="$PARTIAL_DIR/dashboard_stats_v2.html"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "ERROR: $TEMPLATE not found. Run this from your Flask project root." >&2
  exit 1
fi

mkdir -p "$PARTIAL_DIR"

cat > "$PARTIAL" <<'HTML'
<style>
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin: 12px 0 20px; }
  .stat-card { padding: 12px; border: 1px solid #e3e3e3; border-radius: 8px; background: #fff; }
  .stat-card .label { font-size: 12px; color: #666; margin-bottom: 6px; }
  .stat-card .value { font-size: 20px; font-weight: 600; color: #111; }
</style>
<div id="dashboard-stats-v2" class="stats-grid">
  <div class="stat-card"><div class="label">Кеги всего</div><div class="value" id="kegs_total">—</div></div>
  <div class="stat-card"><div class="label">Кеги активные</div><div class="value" id="kegs_active">—</div></div>
  <div class="stat-card"><div class="label">Кеги пустые</div><div class="value" id="kegs_empty">—</div></div>

  <div class="stat-card"><div class="label">Рецептов всего</div><div class="value" id="recipes_total">—</div></div>
  <div class="stat-card"><div class="label">Рентабельные</div><div class="value" id="recipes_profitable">—</div></div>
  <div class="stat-card"><div class="label">Нерентабельные</div><div class="value" id="recipes_unprofitable">—</div></div>

  <div class="stat-card"><div class="label">Поставщиков</div><div class="value" id="suppliers_total">—</div></div>
  <div class="stat-card"><div class="label">С офертами</div><div class="value" id="suppliers_with_offers">—</div></div>

  <div class="stat-card"><div class="label">Алерты цен</div><div class="value" id="prices_active_alerts">—</div></div>
  <div class="stat-card"><div class="label">Статус цен</div><div class="value" id="prices_alerts_status">—</div></div>

  <div class="stat-card"><div class="label">СБИС: последняя синхронизация</div><div class="value" id="sbis_last_sync">—</div></div>
  <div class="stat-card"><div class="label">СБИС: документов сегодня</div><div class="value" id="sbis_documents_today">—</div></div>
</div>
HTML

echo "Created partial: $PARTIAL"

cp -n "$TEMPLATE" "${TEMPLATE}.bak" || true

python3 - "$TEMPLATE" <<'PY'
import io, sys, re, os
p = sys.argv[1]
snippet = "{% include 'partials/dashboard_stats_v2.html' %}\n"
html = open(p, 'r', encoding='utf-8').read()
if snippet in html:
    print('Partial already included — skipping insert')
else:
    for marker in ('</main>', '{% endblock %}', '</body>'):
        i = html.find(marker)
        if i != -1:
            html = html[:i] + snippet + html[i:]
            open(p, 'w', encoding='utf-8').write(html)
            print('Inserted include before', marker)
            break
    else:
        open(p, 'a', encoding='utf-8').write('\n' + snippet)
        print('Appended include at EOF')

html = open(p, 'r', encoding='utf-8').read()
pattern = r"\{\{\s*url_for\('static',\s*filename=['\"]js/app\\.js['\"](.*?)\)\s*\}\}"

def repl(m):
    inner = m.group(1)
    if 'v=' in inner:
        return m.group(0)
    inner = inner.rstrip()
    if inner == '':
        return "{{ url_for('static', filename='js/app.js', v=6) }}"
    if inner.endswith(','):
        return "{{ url_for('static', filename='js/app.js' " + inner + " v=6) }}"
    else:
        return "{{ url_for('static', filename='js/app.js' " + inner + ", v=6) }}"

new_html, n = re.subn(pattern, repl, html)
if n:
    open(p, 'w', encoding='utf-8').write(new_html)
    print(f'Updated app.js include with cache-bust v=6 (matches: {n})')
else:
    print('Note: app.js include not found or already has v=...')
PY

echo "Making a git commit on a new branch fix/dashboard-stats-html"

if git rev-parse --git-dir >/dev/null 2>&1; then
  git checkout -b fix/dashboard-stats-html || git checkout fix/dashboard-stats-html
  git add "$PARTIAL" "$TEMPLATE"
  git commit -m "feat(dashboard): add stats_v2 HTML partial and include into dashboard.html; add cache-busting for app.js"
  echo "You can now merge to main: git checkout main && git merge --no-ff fix/dashboard-stats-html && git push"
else
  echo "Note: Not a git repo here"
fi

printf "\nDone. Now reload your app (clear cache or open /?v=6) and check DevTools → Network for /api/dashboard/stats_v2 = 200.\n"
