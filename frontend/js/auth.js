// auth.js
const Auth = {
    token: localStorage.getItem('token') || null,
    
    init() {
        this.checkAuth();
        document.getElementById('login-form').addEventListener('submit', this.handleLogin.bind(this));
        document.getElementById('logout-btn').addEventListener('click', this.handleLogout.bind(this));
    },

    async checkAuth() {
        if (!this.token) {
            this.showLogin();
            return;
        }
        
        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            
            if (res.ok) {
                const data = await res.json();
                document.getElementById('current-user').textContent = data.username;
                this.showApp();
            } else {
                this.handleLogout();
            }
        } catch (e) {
            this.handleLogout();
        }
    },

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');
        errorEl.textContent = '';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();

            if (res.ok) {
                this.token = data.token;
                localStorage.setItem('token', this.token);
                this.checkAuth();
            } else {
                errorEl.textContent = data.detail || 'Invalid credentials';
            }
        } catch (error) {
            errorEl.textContent = 'Network error. Please try again.';
        }
    },

    handleLogout() {
        this.token = null;
        localStorage.removeItem('token');
        fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
        this.showLogin();
        // Clear inputs
        document.getElementById('login-password').value = '';
    },

    showLogin() {
        if (window.AlertSync) window.AlertSync.stop();
        document.getElementById('login-view').classList.remove('hidden');
        document.getElementById('app-view').classList.add('hidden');
    },

    showApp() {
        document.getElementById('login-view').classList.add('hidden');
        document.getElementById('app-view').classList.remove('hidden');
        if (window.AlertSync) window.AlertSync.start();
        // Trigger initial app load
        if(window.App) window.App.onAppLoad();
    },
    
    getHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`
        };
    }
};

document.addEventListener('DOMContentLoaded', () => Auth.init());
