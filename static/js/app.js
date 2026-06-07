console.log('app.js v20260606');
// ─── MODALS ───
function showKegModal(tapNumber) {
    document.getElementById('modalTapNumber').textContent = '#' + tapNumber;
    document.getElementById('kegForm').action = '/keg/' + tapNumber + '/install';
    document.getElementById('kegModal').classList.add('active');
}

function showLevelModal(tapNumber) {
    document.getElementById('levelTapNumber').textContent = '#' + tapNumber;
    document.getElementById('levelForm').action = '/keg/' + tapNumber + '/update';
    document.getElementById('levelModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Close modal on backdrop click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// Close on Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    }
});

// ─── KEG INTERACTIVITY ───
document.querySelectorAll('.keg-card').forEach(card => {
    card.addEventListener('click', function(e) {
        // Don't trigger if clicking action buttons
        if (e.target.closest('.btn-keg-action')) return;

        const tap = this.dataset.tap;
        // Could show detailed keg info panel
        console.log('Keg ' + tap + ' clicked');
    });
});

// ─── LIVE UPDATES ───

// Update every 30 seconds
setInterval(updateDashboardStats, 30000);

// ─── KEG LEVEL UPDATE VIA AJAX ───
document.getElementById('levelForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch(this.action, {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            closeModal('levelModal');
            // Refresh page to show updated keg
            location.reload();
        }
    })
    .catch(e => console.error('Update failed:', e));
});

// ─── SEARCH ───
document.getElementById('globalSearch').addEventListener('input', function(e) {
    const query = e.target.value.trim();
    if (query.length < 2) return;

    // Could implement live search
    console.log('Search:', query);
});

// ─── KEG ANIMATIONS ───
// Add random bubble animation delays
document.querySelectorAll('.keg-bubbles').forEach((bubbles, i) => {
    bubbles.style.setProperty('--delay', (i * 0.3) + 's');
});

// ─── NOTIFICATIONS ───
function showNotification(title, message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// ─── CONFIRM ACTIONS ───
document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function(e) {
        const message = this.dataset.confirm;
        if (!confirm(message)) {
            e.preventDefault();
        }
    });
});

console.log('Bar Management System loaded 🍺');

// Auto-run on page load
document.addEventListener('DOMContentLoaded', updateDashboardStats);

function updateDashboardStats() {
    fetch('/api/dashboard/stats_v2')
        .then(r => r.json())
        .then(data => {
            const $ = (id) => document.getElementById(id);
            if ($('v2_kegs_total')) $('v2_kegs_total').textContent = data.kegs?.total ?? '—';
            if ($('v2_kegs_active')) $('v2_kegs_active').textContent = data.kegs?.active ?? '—';
            if ($('v2_kegs_empty')) $('v2_kegs_empty').textContent = data.kegs?.empty ?? '—';

            if ($('v2_recipes_total')) $('v2_recipes_total').textContent = data.recipes?.total ?? '—';
            if ($('v2_recipes_profitable')) $('v2_recipes_profitable').textContent = data.recipes?.profitable ?? '—';
            if ($('v2_recipes_unprofitable')) $('v2_recipes_unprofitable').textContent = data.recipes?.unprofitable ?? '—';

            if ($('v2_suppliers_total')) $('v2_suppliers_total').textContent = data.suppliers?.total ?? '—';
            if ($('v2_suppliers_with_offers')) $('v2_suppliers_with_offers').textContent = data.suppliers?.with_offers ?? '—';

            if ($('v2_prices_active_alerts')) $('v2_prices_active_alerts').textContent = data.prices?.active_alerts ?? '—';
            if ($('v2_prices_alerts_status')) {
                const n = data.prices?.active_alerts || 0;
                $('v2_prices_alerts_status').textContent = n>0 ? 'Требуют внимания' : 'Всё в порядке';
                $('v2_prices_alerts_status').className = 'stat-change' + (n>0 ? ' danger' : '');
            }

            if ($('v2_sbis_last_sync')) $('v2_sbis_last_sync').textContent = data.sbis?.last_sync ?? '—';
            if ($('v2_sbis_documents_today')) $('v2_sbis_documents_today').textContent = data.sbis?.documents_today ?? '—';
        })
        .catch(e => console.error('Stats update failed:', e));
}


document.addEventListener('DOMContentLoaded', () => {
  const fill = (d) => {
    const m = {
      kegs_total: d.get?.kegs?.total ?? d.kegs?.total ?? '—',
      kegs_active: d.get?.kegs?.active ?? d.kegs?.active ?? '—',
      kegs_empty: d.get?.kegs?.empty ?? d.kegs?.empty ?? '—',
      recipes_total: d.get?.recipes?.total ?? d.recipes?.total ?? '—',
      recipes_profitable: d.get?.recipes?.profitable ?? d.recipes?.profitable ?? '—',
      recipes_unprofitable: d.get?.recipes?.unprofitable ?? d.recipes?.unprofitable ?? '—',
      suppliers_total: d.get?.suppliers?.total ?? d.suppliers?.total ?? '—',
      suppliers_with_offers: d.get?.suppliers?.with_offers ?? d.suppliers?.with_offers ?? '—',
      prices_active_alerts: d.get?.prices?.active_alerts ?? d.prices?.active_alerts ?? '—',
      sbis_last_sync: d.get?.sbis?.last_sync ?? d.sbis?.last_sync ?? '—',
      sbis_documents_today: d.get?.sbis?.documents_today ?? d.sbis?.documents_today ?? '—',
    };
    for (const [id,v] of Object.entries(m)) { const el=document.getElementById(id); if(el) el.textContent = v; }
  };
  const load = () => fetch('/api/dashboard/stats_v2',{cache:'no-store'}).then(r=>r.json()).then(fill).catch(e=>console.warn('stats_v2 fetch failed',e));
  load(); setInterval(load, 30000);
});

