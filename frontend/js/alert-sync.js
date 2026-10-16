const AlertSync = {
    ws: null,
    state: 'DISCONNECTED',

    start() {
        if (this.ws || !window.Auth || !Auth.token) return;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/alerts?token=${encodeURIComponent(Auth.token)}`);
        this.ws.onmessage = (message) => {
            const data = JSON.parse(message.data);
            this.state = data.type === 'CONNECTION_STATE' ? data.state : this.state;
            window.dispatchEvent(new CustomEvent('security-alert-state', { detail: data }));
        };
        this.ws.onclose = () => {
            this.ws = null;
            this.state = 'DISCONNECTED';
        };
    },

    stop() {
        if (this.ws) this.ws.close();
        this.ws = null;
        this.state = 'DISCONNECTED';
    }
};

window.AlertSync = AlertSync;