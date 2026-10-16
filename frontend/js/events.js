// events.js
const Events = {
    eventToDelete: null,

    async load() {
        try {
            const res = await fetch('/api/events?limit=100', {
                headers: Auth.getHeaders()
            });
            if (res.ok) {
                const events = await res.json();
                this.renderTable(events);
            }
        } catch (e) {
            console.error('Error loading events:', e);
        }
    },

    renderTable(events) {
        const tbody = document.querySelector('#full-events-table tbody');
        tbody.innerHTML = '';
        if (events.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 3rem;">
                <div style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 0.5rem;">No security events recorded.</div>
                <div style="color: var(--text-muted); font-size: 0.9rem;">New validated threats will appear here automatically.</div>
            </td></tr>`;
            return;
        }

        events.forEach(ev => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${ev.id.substring(0,8)}</td>
                <td>${new Date(ev.timestamp).toLocaleString()}</td>
                <td style="color:var(--danger); font-weight:bold;">${ev.weapon_type}</td>
                <td>${(ev.weapon_confidence * 100).toFixed(1)}%</td>
                <td>${ev.camera_source}</td>
                <td>${ev.status}</td>
                <td>
                    <div style="display:flex; gap: 5px;">
                        <button class="btn secondary-btn small-btn view-ev-btn" data-url="${ev.evidence_url || ''}">View</button>
                        <button class="btn danger-btn small-btn delete-ev-btn" data-id="${ev.id}">Delete</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('.view-ev-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = e.target.getAttribute('data-url');
                App.showEvidence(url);
            });
        });

        document.querySelectorAll('.delete-ev-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const eventId = e.target.getAttribute('data-id');
                Events.eventToDelete = eventId;
                document.getElementById('delete-event-modal').classList.remove('hidden');
            });
        });
    }
};

document.getElementById('refresh-events-btn').addEventListener('click', () => Events.load());

// Clear All Evidence Logic
document.getElementById('clear-events-btn').addEventListener('click', () => {
    document.getElementById('clear-evidence-modal').classList.remove('hidden');
});

document.getElementById('close-clear-modal').addEventListener('click', () => {
    document.getElementById('clear-evidence-modal').classList.add('hidden');
});

document.getElementById('cancel-clear-btn').addEventListener('click', () => {
    document.getElementById('clear-evidence-modal').classList.add('hidden');
});

document.getElementById('confirm-clear-btn').addEventListener('click', async () => {
    const btn = document.getElementById('confirm-clear-btn');
    btn.disabled = true;
    btn.textContent = "Deleting...";
    
    try {
        const res = await fetch('/api/events/clear', {
            method: 'DELETE',
            headers: Auth.getHeaders()
        });
        
        if (res.ok) {
            const data = await res.json();
            document.getElementById('clear-evidence-modal').classList.add('hidden');
            App.showToast('All evidence cleared successfully', `Deleted ${data.deleted_events} events and ${data.deleted_files} evidence images.`, 'success');
            Events.load();
        } else {
            const err = await res.json();
            App.showToast('Error', `Failed to clear evidence: ${err.detail || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        console.error('Error clearing evidence:', e);
        App.showToast('Error', 'Failed to clear evidence due to a network error.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = "Delete All";
    }
});

// Individual Delete Logic
document.getElementById('close-delete-modal').addEventListener('click', () => {
    document.getElementById('delete-event-modal').classList.add('hidden');
});

document.getElementById('cancel-delete-btn').addEventListener('click', () => {
    document.getElementById('delete-event-modal').classList.add('hidden');
});

document.getElementById('confirm-delete-btn').addEventListener('click', async () => {
    if (!Events.eventToDelete) return;
    const eventId = Events.eventToDelete;
    const btn = document.getElementById('confirm-delete-btn');
    btn.disabled = true;
    btn.textContent = "Deleting...";
    
    try {
        const res = await fetch(`/api/events/${eventId}`, {
            method: 'DELETE',
            headers: Auth.getHeaders()
        });
        
        if (res.ok) {
            const data = await res.json();
            document.getElementById('delete-event-modal').classList.add('hidden');
            App.showToast('Event deleted successfully', `Event and ${data.deleted_file ? 'evidence image' : 'database record'} removed.`, 'success');
            Events.eventToDelete = null;
            Events.load();
        } else {
            const err = await res.json();
            App.showToast('Error', `Failed to delete event: ${err.detail || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        console.error('Error deleting event:', e);
        App.showToast('Error', 'Failed to delete event due to a network error.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = "Delete";
    }
});

window.Events = Events;
