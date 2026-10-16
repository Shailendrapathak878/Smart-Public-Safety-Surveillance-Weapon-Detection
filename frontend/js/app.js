// app.js
const App = {
    currentSection: 'overview-section',

    init() {
        this.setupNavigation();
        
        // Close modal
        const modal = document.getElementById('evidence-modal');
        document.getElementById('close-modal').addEventListener('click', () => {
            modal.classList.add('hidden');
        });
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
        
        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                modal.classList.add('hidden');
            }
        });
    },

    onAppLoad() {
        // Called by Auth when login succeeds
        this.navigateTo(this.currentSection);
    },

    setupNavigation() {
        const navItems = document.querySelectorAll('#nav-menu li');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const targetId = e.target.getAttribute('data-target');
                if (targetId) {
                    this.navigateTo(targetId);
                }
            });
        });
    },

    navigateTo(targetId) {
        // Update nav UI
        document.querySelectorAll('#nav-menu li').forEach(li => li.classList.remove('active'));
        document.querySelector(`[data-target="${targetId}"]`).classList.add('active');

        // Update sections
        document.querySelectorAll('.app-section').forEach(sec => sec.classList.add('hidden'));
        document.getElementById(targetId).classList.remove('hidden');

        this.currentSection = targetId;

        // Trigger section-specific logic
        if (targetId === 'overview-section' && window.Dashboard) window.Dashboard.load();
        if (targetId === 'events-section' && window.Events) window.Events.load();
        if (targetId === 'settings-section' && window.Settings) window.Settings.load();
        if (targetId === 'analytics-section' && window.Analytics) window.Analytics.load();
        
        // Stop monitoring if navigating away
        if (targetId !== 'monitoring-section' && window.Monitoring) {
            window.Monitoring.stop();
        }

        // Stop analytics polling if navigating away
        if (targetId !== 'analytics-section' && window.Analytics) {
            window.Analytics.stop();
        }
    },
    
    showEvidence(url) {
        if (!url) {
            this.showToast('Error', 'Evidence image is unavailable.', 'error');
            return;
        }
        
        const modal = document.getElementById('evidence-modal');
        const img = document.getElementById('evidence-img-display');
        
        img.onerror = () => {
            this.showToast('Error', 'Evidence image is unavailable.', 'error');
            modal.classList.add('hidden');
            img.src = ''; // reset
        };
        
        img.src = url;
        modal.classList.remove('hidden');
    },

    showToast(title, message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
        `;

        container.appendChild(toast);

        const closeBtn = toast.querySelector('.toast-close');
        
        const closeToast = () => {
            toast.classList.add('toast-out');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300); // match animation duration
        };

        closeBtn.addEventListener('click', closeToast);

        // Auto close after 5 seconds
        setTimeout(closeToast, 5000);
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
