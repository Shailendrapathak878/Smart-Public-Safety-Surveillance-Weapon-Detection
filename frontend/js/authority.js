const Authority = {
    token: localStorage.getItem('token') || null,
    ws: null,
    currentEvent: null,
    events: [],
    evidenceUrl: null,
    reconnectTimer: null,
    reconnectDelay: 1000,

    init() {
        document.getElementById('login-form').addEventListener('submit', (event) => this.login(event));
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        document.getElementById('acknowledge-btn').addEventListener('click', () => this.acknowledge());
        document.getElementById('mute-alarm-btn').addEventListener('click', () => this.muteAlarm());
        document.getElementById('view-evidence').addEventListener('click', () => this.openEvidence());
        document.getElementById('close-modal').addEventListener('click', () => this.closeEvidence());
        document.getElementById('evidence-modal').addEventListener('click', (event) => {
            if (event.target.id === 'evidence-modal') this.closeEvidence();
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') this.closeEvidence();
        });
        this.startClock();
        this.checkAuth();
    },

    async checkAuth() {
        if (!this.token) return this.showLogin();
        try {
            console.info('[AUTHORITY] dashboard startup');
            const response = await fetch('/api/auth/me', { headers: this.headers() });
            if (!response.ok) throw new Error('Session expired');
            const user = await response.json();
            document.getElementById('current-user').textContent = user.username || '-';
            this.showApp();
            this.connectWebSocket();
            await this.synchronize();
        } catch (error) {
            this.logout(false);
        }
    },

    async login(event) {
        event.preventDefault();
        const error = document.getElementById('login-error');
        error.textContent = '';
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('login-username').value,
                    password: document.getElementById('login-password').value
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Invalid credentials');
            this.token = data.token;
            localStorage.setItem('token', this.token);
            await this.checkAuth();
        } catch (loginError) {
            error.textContent = loginError.message || 'Unable to sign in.';
        }
    },

    logout(notify = true) {
        if (this.ws) this.ws.close();
        this.ws = null;
        this.token = null;
        localStorage.removeItem('token');
        this.showLogin();
        if (notify) this.toast('Signed out');
    },

    headers() { return { Authorization: `Bearer ${this.token}` }; },
    showLogin() { document.getElementById('login-view').classList.remove('hidden'); document.getElementById('app-view').classList.add('hidden'); },
    showApp() { document.getElementById('login-view').classList.add('hidden'); document.getElementById('app-view').classList.remove('hidden'); },

    startClock() {
        const update = () => document.getElementById('current-time').textContent = new Date().toLocaleString();
        update();
        setInterval(update, 1000);
    },

    setConnection(state) {
        const element = document.getElementById('connection-status');
        const labels = { CONNECTED: '● CONNECTED', CONNECTING: '● CONNECTING', RECONNECTING: '● RECONNECTING', DISCONNECTED: '● DISCONNECTED' };
        element.textContent = labels[state] || `● ${state}`;
        element.className = `status ${state === 'CONNECTED' ? 'online' : state === 'DISCONNECTED' ? 'offline' : 'warning'}`;
    },

    connectWebSocket() {
        if (!this.token) return;
        this.setConnection(this.ws ? 'RECONNECTING' : 'CONNECTING');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/alerts?token=${encodeURIComponent(this.token)}`);
        this.ws.onopen = () => { this.reconnectDelay = 1000; this.setConnection('CONNECTED'); };
        this.ws.onmessage = (message) => {
            const data = JSON.parse(message.data);
            if (data.event_id) console.info(`[TIMING] T5_RECEIVED event_id=${data.event_id} perf_ms=${performance.now().toFixed(3)}`);
            this.handleMessage(data);
        };
        this.ws.onerror = () => this.setConnection('DISCONNECTED');
        this.ws.onclose = () => {
            this.setConnection('RECONNECTING');
            if (this.token) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = setTimeout(() => this.reconnect(), this.reconnectDelay);
                this.reconnectDelay = Math.min(this.reconnectDelay * 2, 15000);
            }
        };
    },

    async reconnect() {
        this.connectWebSocket();
        await this.synchronize();
    },

    async synchronize() {
        try {
            const [activeResponse, recentResponse] = await Promise.all([
                fetch('/api/alerts/active', { headers: this.headers() }),
                fetch('/api/events?limit=50', { headers: this.headers() })
            ]);
            if (!activeResponse.ok || !recentResponse.ok) throw new Error('Synchronization failed');
            const active = await activeResponse.json();
            this.events = await recentResponse.json();
            this.renderRecent();
            const latest = active.alerts && active.alerts[0];
            if (latest) await this.selectEvent(latest);
            else this.clearActive();
            this.setAlarmState(active.alarm_state);
            document.getElementById('sync-state').textContent = `Synchronized ${new Date().toLocaleTimeString()}`;
        } catch (error) {
            this.toast('Synchronization unavailable');
        }
    },

    handleMessage(message) {
        if (message.type === 'CONNECTION_STATE') {
            this.setConnection(message.state);
            this.setAlarmState(message.alarm_state);
            return;
        }
        if (message.type === 'THREAT_DETECTED') {
            this.upsertEvent(message);
            this.selectEvent(message);
            this.setAlarmState(message.alarm_state);
        }
        if (message.type === 'ALERT_STATE_CHANGED') {
            this.upsertEvent(message);
            if (this.currentEvent && this.currentEvent.event_id === message.event_id) this.selectEvent(message);
            this.setAlarmState(message.alarm_state);
        }
        if (message.type === 'EVIDENCE_READY') {
            this.upsertEvent(message);
            if (this.currentEvent && this.currentEvent.event_id === message.event_id) this.selectEvent(message);
        }
    },

    upsertEvent(event) {
        const normalized = { ...event, id: event.event_id || event.id, weapon_type: event.weapon || event.weapon_type, weapon_confidence: event.confidence ?? event.weapon_confidence, camera_source: event.source || event.camera_source };
        const index = this.events.findIndex((item) => item.id === normalized.id);
        if (index >= 0) this.events[index] = { ...this.events[index], ...normalized };
        else this.events.unshift(normalized);
        this.renderRecent();
    },

    async selectEvent(event) {
        this.currentEvent = { ...event, event_id: event.event_id || event.id };
        this.renderActive();
        console.info(`[TIMING] T6_RENDER event_id=${this.currentEvent.event_id} perf_ms=${performance.now().toFixed(3)}`);
        if (this.currentEvent.evidence_url) await this.loadEvidence(this.currentEvent.evidence_url);
        else this.setEvidenceUnavailable('Evidence unavailable');
    },

    renderActive() {
        const event = this.currentEvent;
        if (!event) return;
        const active = event.alert_state === 'ACTIVE' && (event.status === 'NEW' || event.status === 'ACTIVE');
        const panel = document.getElementById('active-alert');
        panel.className = `active-alert ${active ? 'active' : ''}`;
        document.getElementById('alert-title').textContent = active ? 'VALIDATED SECURITY THREAT' : 'ALERT ACKNOWLEDGED';
        document.getElementById('alert-subtitle').textContent = active ? 'Immediate authority attention required' : 'Backend confirmation received.';
        document.getElementById('alert-workspace').classList.remove('hidden');
        document.getElementById('detail-weapon').textContent = event.weapon || event.weapon_type || '-';
        document.getElementById('detail-confidence').textContent = this.percent(event.confidence ?? event.weapon_confidence);
        document.getElementById('detail-iow').textContent = event.iow == null ? '-' : Number(event.iow).toFixed(2);
        document.getElementById('detail-source').textContent = event.source || event.camera_source || '-';
        document.getElementById('detail-time').textContent = event.timestamp ? new Date(event.timestamp).toLocaleString() : '-';
        document.getElementById('detail-id').textContent = event.event_id || event.id || '-';
        const status = document.getElementById('event-status');
        status.textContent = event.status || 'UNKNOWN';
        status.className = `badge ${(event.status || '').toLowerCase()}`;
        const acknowledge = document.getElementById('acknowledge-btn');
        acknowledge.disabled = !active;
        acknowledge.textContent = active ? 'Acknowledge Alert' : 'Alert Acknowledged';
    },

    clearActive() {
        this.currentEvent = null;
        document.getElementById('active-alert').className = 'active-alert empty-state';
        document.getElementById('alert-title').textContent = 'NO ACTIVE THREATS';
        document.getElementById('alert-subtitle').textContent = 'Monitoring connected sources...';
        document.getElementById('alert-workspace').classList.add('hidden');
        this.setAlarmState('STOPPED');
    },

    async acknowledge() {
        if (!this.currentEvent || document.getElementById('acknowledge-btn').disabled) return;
        const button = document.getElementById('acknowledge-btn');
        button.disabled = true;
        button.textContent = 'Acknowledging...';
        try {
            const response = await fetch(`/api/alerts/events/${this.currentEvent.event_id}/acknowledge`, {
                method: 'POST', headers: { ...this.headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ command_id: `CMD-${crypto.randomUUID()}` })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Acknowledgment failed');
            this.handleMessage({ type: 'ALERT_STATE_CHANGED', ...this.currentEvent, status: data.event_status, alarm_state: data.alarm_state });
            this.toast('Alert acknowledged');
        } catch (error) {
            button.disabled = false;
            button.textContent = 'Acknowledge Alert';
            this.toast(error.message || 'Acknowledgment failed');
        }
    },

    async muteAlarm() {
        if (!this.currentEvent || this.currentEvent.alert_state !== 'ACTIVE') return;
        const button = document.getElementById('mute-alarm-btn');
        if (button.disabled) return;
        button.disabled = true;
        button.textContent = 'Turning Off...';
        try {
            const response = await fetch(`/api/alerts/events/${this.currentEvent.event_id}/mute`, {
                method: 'POST', headers: { ...this.headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: 'MUTE_ALARM', command_id: `CMD-${crypto.randomUUID()}` })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Unable to mute alarm');
            this.handleMessage({ type: 'ALERT_STATE_CHANGED', ...this.currentEvent, alarm_state: data.alarm_state });
            this.toast('Alarm muted');
        } catch (error) {
            button.disabled = false;
            button.textContent = 'TURN OFF ALARM';
            this.toast(error.message || 'Unable to mute alarm');
        }
    },

    async loadEvidence(url) {
        const state = document.getElementById('evidence-state');
        state.textContent = 'Loading...';
        try {
            const response = await fetch(url, { headers: this.headers() });
            if (!response.ok) throw new Error('Evidence unavailable');
            const blob = await response.blob();
            if (this.evidenceUrl) URL.revokeObjectURL(this.evidenceUrl);
            this.evidenceUrl = URL.createObjectURL(blob);
            document.getElementById('evidence-image').src = this.evidenceUrl;
            state.textContent = 'Evidence captured';
        } catch (error) {
            this.setEvidenceUnavailable(error.message);
        }
    },

    setEvidenceUnavailable(message) {
        document.getElementById('evidence-image').removeAttribute('src');
        document.getElementById('evidence-state').textContent = message;
    },

    openEvidence() {
        if (!this.evidenceUrl) return this.toast('Evidence unavailable');
        document.getElementById('modal-image').src = this.evidenceUrl;
        document.getElementById('evidence-modal').classList.remove('hidden');
    },

    closeEvidence() { document.getElementById('evidence-modal').classList.add('hidden'); },
    setAlarmState(state) {
        const label = state === 'ACTIVE' ? 'ALARM ACTIVE' : state === 'MUTED' ? 'ALARM MUTED' : 'ALARM OFF';
        document.getElementById('alarm-state').textContent = label;
        const button = document.getElementById('mute-alarm-btn');
        button.disabled = state !== 'ACTIVE';
        button.textContent = state === 'MUTED' ? 'ALARM MUTED' : 'TURN OFF ALARM';
    },
    percent(value) { return value == null ? '-' : `${(Number(value) * 100).toFixed(1)}%`; },

    renderRecent() {
        const body = document.getElementById('recent-alerts-body');
        if (!this.events.length) { body.innerHTML = '<tr><td colspan="8" class="empty-row">No security alerts recorded.</td></tr>'; return; }
        body.innerHTML = this.events.map((event) => {
            const id = event.id || event.event_id;
            const status = event.status || 'UNKNOWN';
            return `<tr><td>${String(id).slice(0, 8)}...</td><td>${event.weapon_type || event.weapon || '-'}</td><td>${this.percent(event.weapon_confidence ?? event.confidence)}</td><td>${event.iow == null ? '-' : Number(event.iow).toFixed(2)}</td><td>${event.camera_source || event.source || '-'}</td><td>${event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '-'}</td><td><span class="badge ${status.toLowerCase()}">${status}</span></td><td><button class="button quiet view-event" data-event-id="${id}" type="button">View</button></td></tr>`;
        }).join('');
        body.querySelectorAll('.view-event').forEach((button) => button.addEventListener('click', () => {
            const event = this.events.find((item) => (item.id || item.event_id) === button.dataset.eventId);
            if (event) this.selectEvent(event);
        }));
    },

    toast(message) {
        const element = document.createElement('div');
        element.className = 'toast';
        element.textContent = message;
        document.getElementById('toast-container').appendChild(element);
        setTimeout(() => element.remove(), 4500);
    }
};

document.addEventListener('DOMContentLoaded', () => Authority.init());
