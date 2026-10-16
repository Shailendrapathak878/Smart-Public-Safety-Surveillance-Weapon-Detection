// frontend/js/analytics.js
const Analytics = {
    charts: {},
    timer: null,

    async load() {
        this.startAutoRefresh();
        await this.fetchAndRender();
    },

    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    },

    startAutoRefresh() {
        this.stop();
        this.timer = setInterval(() => {
            const section = document.getElementById('analytics-section');
            if (section && section.classList.contains('active')) {
                this.fetchAndRender(true);
            }
        }, 30000); // 30 seconds
    },

    async fetchAndRender(isSilent = false) {
        if (!isSilent) {
            document.getElementById('analytics-last-updated').textContent = 'Updating...';
        }

        const range = document.getElementById('analytics-filter-range').value;
        const weapon = document.getElementById('analytics-filter-weapon').value;
        const source = document.getElementById('analytics-filter-source').value;
        const minConf = document.getElementById('analytics-filter-conf').value;

        try {
            const res = await fetch(`/api/analytics/summary?range=${range}&weapon=${weapon}&source=${source}&min_confidence=${minConf}`, {
                headers: Auth.getHeaders()
            });

            if (res.ok) {
                const data = await res.json();
                this.render(data);
                
                const now = new Date();
                document.getElementById('analytics-last-updated').textContent = 
                    now.getHours().toString().padStart(2, '0') + ':' + 
                    now.getMinutes().toString().padStart(2, '0') + ':' + 
                    now.getSeconds().toString().padStart(2, '0');
            } else {
                if (!isSilent) App.showToast('Analytics unavailable', 'Unable to load security analytics. Please try again.', 'error');
            }
        } catch (e) {
            console.error('Error fetching analytics:', e);
            if (!isSilent) App.showToast('Analytics unavailable', 'Unable to load security analytics. Please try again.', 'error');
        }
    },

    render(data) {
        // Toggle empty state vs dashboard
        const dashboard = document.getElementById('analytics-dashboard-content');
        const emptyState = document.getElementById('analytics-empty-state');
        
        if (data.kpis.total_threats === 0) {
            dashboard.classList.add('hidden');
            emptyState.classList.remove('hidden');
            this.renderKPIs(data.kpis); // Render zeros
            return;
        } else {
            dashboard.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }

        this.renderKPIs(data.kpis);
        
        if (typeof Chart !== 'undefined') {
            this.renderTimeline(data.timeline);
            this.renderWeaponDistribution(data.weapon_distribution);
            this.renderSourceDistribution(data.source_distribution);
            this.renderHourlyActivity(data.hourly_activity);
        } else {
            console.warn('Chart.js not loaded. Skipping chart rendering.');
        }

        this.renderHeatmap(data.heatmap);
        this.renderInsights(data.insights);
        this.renderRecentEvents(data.recent_events);
    },

    renderKPIs(kpis) {
        document.getElementById('kpi-total').textContent = kpis.total_threats;
        document.getElementById('kpi-evidence').textContent = kpis.evidence_captured;
        document.getElementById('kpi-weapon').textContent = kpis.most_detected_weapon;
        document.getElementById('kpi-source').textContent = kpis.most_active_source;
        document.getElementById('kpi-conf').textContent = kpis.average_confidence + '%';
    },

    destroyChart(id) {
        if (this.charts[id]) {
            this.charts[id].destroy();
        }
    },

    renderTimeline(timeline) {
        this.destroyChart('chart-timeline');
        const ctx = document.getElementById('chart-timeline').getContext('2d');
        
        this.charts['chart-timeline'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeline.map(t => t.time),
                datasets: [{
                    label: 'Validated Threats',
                    data: timeline.map(t => t.count),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                    x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    },

    renderWeaponDistribution(data) {
        this.destroyChart('chart-weapon');
        const ctx = document.getElementById('chart-weapon').getContext('2d');
        
        const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#a855f7'];
        
        this.charts['chart-weapon'] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 1,
                    borderColor: '#1e293b'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'right', labels: { color: '#f8fafc' } }
                }
            }
        });
    },

    renderSourceDistribution(data) {
        this.destroyChart('chart-source');
        const ctx = document.getElementById('chart-source').getContext('2d');
        
        this.charts['chart-source'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: 'Threats',
                    data: data.map(d => d.count),
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                    y: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    },

    renderHourlyActivity(data) {
        this.destroyChart('chart-hourly');
        const ctx = document.getElementById('chart-hourly').getContext('2d');
        
        this.charts['chart-hourly'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.hour + ':00'),
                datasets: [{
                    label: 'Threats',
                    data: data.map(d => d.count),
                    backgroundColor: '#10b981',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    },

    renderHeatmap(data) {
        const container = document.getElementById('heatmap-grid');
        container.innerHTML = '';
        
        if (data.length === 0) return;

        // Find max count for normalization
        const maxCount = Math.max(...data.map(d => d.count), 1); // Avoid div by 0

        const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
        
        // Add Header Row (Hours)
        container.appendChild(document.createElement('div')); // Empty corner
        for (let h = 0; h < 24; h++) {
            const hDiv = document.createElement('div');
            hDiv.className = 'hm-label';
            hDiv.textContent = h.toString().padStart(2, '0');
            container.appendChild(hDiv);
        }

        // Add Grid Rows
        days.forEach(day => {
            const dayLabel = document.createElement('div');
            dayLabel.className = 'hm-label';
            dayLabel.textContent = day.substring(0,3);
            container.appendChild(dayLabel);
            
            for (let h = 0; h < 24; h++) {
                const hourStr = h.toString().padStart(2, '0');
                const cellData = data.find(d => d.day === day && d.hour === hourStr);
                const count = cellData ? cellData.count : 0;
                
                const cell = document.createElement('div');
                cell.className = 'hm-cell';
                
                if (count > 0) {
                    const intensity = Math.max(0.2, count / maxCount); // min 0.2 opacity so it's visible
                    cell.style.backgroundColor = `rgba(239, 68, 68, ${intensity})`; // Danger red based
                } else {
                    cell.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                }
                
                cell.title = `${day} ${hourStr}:00 - ${count} threats`;
                container.appendChild(cell);
            }
        });
    },

    renderInsights(insights) {
        if (!insights) return;
        document.getElementById('insight-weapon').textContent = insights.most_detected;
        document.getElementById('insight-source').textContent = insights.most_active_source;
        document.getElementById('insight-conf').textContent = insights.average_confidence;
        document.getElementById('insight-peak').textContent = insights.peak_activity;
    },

    renderRecentEvents(events) {
        const tbody = document.querySelector('#analytics-recent-table tbody');
        tbody.innerHTML = '';
        
        if (events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No recent events.</td></tr>';
            return;
        }

        events.forEach(ev => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${new Date(ev.timestamp).toLocaleTimeString()}</td>
                <td style="color:var(--danger); font-weight:bold;">${ev.weapon_type}</td>
                <td>${(ev.weapon_confidence * 100).toFixed(1)}%</td>
                <td>${ev.camera_source}</td>
                <td><button class="btn secondary-btn small-btn view-ev-btn" data-url="${ev.evidence_url || ''}">View</button></td>
            `;
            tbody.appendChild(tr);
        });

        document.querySelectorAll('#analytics-recent-table .view-ev-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = e.target.getAttribute('data-url');
                App.showEvidence(url);
            });
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Event listeners for filters
    document.getElementById('analytics-filter-range').addEventListener('change', () => Analytics.fetchAndRender());
    document.getElementById('analytics-filter-weapon').addEventListener('change', () => Analytics.fetchAndRender());
    document.getElementById('analytics-filter-source').addEventListener('change', () => Analytics.fetchAndRender());
    document.getElementById('analytics-filter-conf').addEventListener('input', (e) => {
        document.getElementById('analytics-conf-val').textContent = e.target.value + '%';
    });
    document.getElementById('analytics-filter-conf').addEventListener('change', () => Analytics.fetchAndRender());
    document.getElementById('refresh-analytics-btn').addEventListener('click', () => Analytics.fetchAndRender());
    
    // Wire range buttons to select
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.time-range-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            document.getElementById('analytics-filter-range').value = e.target.getAttribute('data-val');
            Analytics.fetchAndRender();
        });
    });
});

window.Analytics = Analytics;
