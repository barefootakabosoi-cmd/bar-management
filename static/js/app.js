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
function updateDashboardStats() {
    fetch('/api/dashboard/stats')
        .then(r => r.json())
        .then(data => {
            // Update stats cards if elements exist
            console.log('Stats updated:', data);
        })
        .catch(e => console.error('Stats update failed:', e));
}

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
