// settings.js
const Settings = {
    async load() {
        try {
            const res = await fetch('/api/settings', {
                headers: Auth.getHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                document.getElementById('setting-iow').value = data.iow_threshold;
                document.getElementById('setting-weapon-conf').value = data.weapon_confidence;
                document.getElementById('setting-cooldown').value = data.cooldown_seconds;
            }
        } catch (e) {
            console.error('Error loading settings:', e);
        }
    },

    async save() {
        const iow = parseFloat(document.getElementById('setting-iow').value);
        const weapon_conf = parseFloat(document.getElementById('setting-weapon-conf').value);
        const cooldown = parseInt(document.getElementById('setting-cooldown').value);
        
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    ...Auth.getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ iow_threshold: iow, weapon_confidence: weapon_conf, cooldown_seconds: cooldown })
            });
            
            if (res.ok) {
                alert('Settings saved successfully!');
            }
        } catch (e) {
            alert('Failed to save settings.');
        }
    }
};

document.getElementById('save-settings-btn').addEventListener('click', () => Settings.save());
window.Settings = Settings;
