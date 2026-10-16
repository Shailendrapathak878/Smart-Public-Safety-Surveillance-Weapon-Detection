// analysis.js
const Analysis = {
    init() {
        // Image Analysis
        const imgInput = document.getElementById('image-upload');
        const imgBtn = document.getElementById('analyze-image-btn');
        const clearBtn = document.getElementById('clear-image-btn');
        
        imgInput.addEventListener('change', () => {
            const file = imgInput.files[0];
            imgBtn.disabled = !file;
            if (file) {
                const url = URL.createObjectURL(file);
                document.getElementById('image-result-display').src = url;
                document.getElementById('image-results-container').classList.remove('hidden');
                document.getElementById('image-status-banner').classList.add('hidden');
                document.getElementById('img-metrics-row').classList.add('hidden');
            }
        });
        
        imgBtn.addEventListener('click', () => this.analyzeImage());
        clearBtn.addEventListener('click', () => {
            imgInput.value = '';
            imgBtn.disabled = true;
            document.getElementById('image-results-container').classList.add('hidden');
        });

        // Video Analysis
        const vidInput = document.getElementById('video-upload');
        const vidBtn = document.getElementById('analyze-video-btn');
        const stopBtn = document.getElementById('stop-video-btn');

        vidInput.addEventListener('change', () => {
            vidBtn.disabled = !vidInput.files.length;
        });

        vidBtn.addEventListener('click', () => this.analyzeVideo());
        stopBtn.addEventListener('click', () => {
            if (window.Monitoring) window.Monitoring.stop();
            document.getElementById('video-feed-container').classList.add('hidden');
            vidBtn.disabled = false;
            stopBtn.disabled = true;
        });
    },

    async analyzeImage() {
        const file = document.getElementById('image-upload').files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const btn = document.getElementById('analyze-image-btn');
        btn.disabled = true;
        btn.textContent = 'Analyzing...';

        try {
            const res = await fetch('/api/analysis/image', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${Auth.token}` }, // Note: FormData does not need Content-Type header
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                const container = document.getElementById('image-results-container');
                const imgDisplay = document.getElementById('image-result-display');
                const banner = document.getElementById('image-status-banner');
                const badge = document.getElementById('img-event-badge');
                
                imgDisplay.src = `data:image/jpeg;base64,${data.image}`;
                document.getElementById('img-persons').textContent = data.persons;
                document.getElementById('img-weapons').textContent = data.weapons;
                
                if (data.threat_status) {
                    banner.className = 'status-banner danger';
                    banner.textContent = '🔴 ACTIVE THREAT DETECTED';
                    if (data.event) {
                        badge.style.display = 'block';
                    }
                } else {
                    banner.className = 'status-banner safe';
                    banner.textContent = '🟢 NO THREAT DETECTED';
                    badge.style.display = 'none';
                }
                
                banner.classList.remove('hidden');
                document.getElementById('img-metrics-row').classList.remove('hidden');
                container.classList.remove('hidden');
            } else {
                alert('Error analyzing image');
            }
        } catch (e) {
            console.error(e);
            alert('Network error during image analysis.');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Analyze Image';
        }
    },

    async analyzeVideo() {
        const file = document.getElementById('video-upload').files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const btn = document.getElementById('analyze-video-btn');
        const stopBtn = document.getElementById('stop-video-btn');
        btn.disabled = true;
        btn.textContent = 'Uploading...';

        try {
            const res = await fetch('/api/analysis/video', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${Auth.token}` },
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                btn.textContent = 'Analyzing Video';
                stopBtn.disabled = false;
                
                document.getElementById('video-feed-container').classList.remove('hidden');
                
                // Use Monitoring.js logic to connect WS for video
                if (window.Monitoring) {
                    window.Monitoring.startVideoSession(data.path, "video-feed");
                }
            } else {
                alert('Error uploading video');
                btn.disabled = false;
                btn.textContent = 'Analyze Video';
            }
        } catch (e) {
            console.error(e);
            alert('Network error during video upload.');
            btn.disabled = false;
            btn.textContent = 'Analyze Video';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Analysis.init());
window.Analysis = Analysis;
