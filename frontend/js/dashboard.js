// dashboard.js
const Dashboard = {
    async load() {
        try {
            const res = await fetch('/api/dashboard/stats', {
                headers: Auth.getHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('overview-total-events').textContent = data.total_events;
                document.getElementById('overview-today-events').textContent = data.events_today;
                document.getElementById('overview-active-threats').textContent = data.active_threats;
            }

            // Fetch recent events
            const evRes = await fetch('/api/events?limit=5', {
                headers: Auth.getHeaders()
            });
            if (evRes.ok) {
                const events = await evRes.json();
                this.renderTable(events);
            }
        } catch (e) {
            console.error('Error loading dashboard stats:', e);
        }
    },

    renderTable(events) {
        const tbody = document.querySelector('#overview-events-table tbody');
        tbody.innerHTML = '';
        if (events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No recent events found.</td></tr>';
            return;
        }

        events.forEach(ev => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${ev.id.substring(0,8)}...</td>
                <td>${new Date(ev.timestamp).toLocaleString()}</td>
                <td style="color:var(--danger); font-weight:bold;">${ev.weapon_type}</td>
                <td>${(ev.weapon_confidence * 100).toFixed(1)}%</td>
                <td>${ev.camera_source}</td>
                <td>${ev.status}</td>
            `;
            tbody.appendChild(tr);
        });
    }
};

window.Dashboard = Dashboard;
