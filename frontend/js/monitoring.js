// monitoring.js
const Monitoring = {
    ws: null,
    localStream: null,
    captureInterval: null,
    isMonitoring: false,
    targetImgId: 'monitoring-feed', // Default for live monitoring

    init() {
        const sourceSelect = document.getElementById('monitoring-source');
        const urlGroup = document.getElementById('monitoring-url-group');
        
        sourceSelect.addEventListener('change', (e) => {
            if (e.target.value === 'browser_webcam') {
                urlGroup.classList.add('hidden');
            } else {
                urlGroup.classList.remove('hidden');
                document.getElementById('monitoring-url-label').textContent = 
                    e.target.value === 'rtsp' ? 'RTSP URL' : 'Camera URL';
            }
        });

        document.getElementById('start-monitoring-btn').addEventListener('click', () => this.startLiveSession());
        document.getElementById('stop-monitoring-btn').addEventListener('click', () => this.stop());
    },

    async startLiveSession() {
        const source = document.getElementById('monitoring-source').value;
        const url = document.getElementById('monitoring-url').value;
        this.targetImgId = 'monitoring-feed';

        if (source !== 'browser_webcam' && !url) {
            alert('Please enter a valid URL.');
            return;
        }

        document.getElementById('start-monitoring-btn').disabled = true;
        document.getElementById('stop-monitoring-btn').disabled = false;
        
        this.connectWebSocket(source, url);
    },

    startVideoSession(path, targetImgId) {
        this.targetImgId = targetImgId;
        this.connectWebSocket('video', path);
    },

    connectWebSocket(source, urlOrPath) {
        if (this.ws) {
            this.ws.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/monitoring`);

        this.ws.onopen = async () => {
            this.isMonitoring = true;
            this.ws.send(JSON.stringify({ type: 'start', source: source, url: urlOrPath, path: urlOrPath }));

            if (source === 'browser_webcam') {
                await this.startLocalWebcam();
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'frame') {
                    this.updateUI(data);
                }
            } catch (e) {
                console.error("Error parsing WS message", e);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
            this.stop();
        };

        this.ws.onclose = () => {
            if (this.isMonitoring) {
                this.stop();
            }
        };
    },

    async startLocalWebcam() {
        const video = document.getElementById('local-webcam');
        const canvas = document.getElementById('capture-canvas');
        const ctx = canvas.getContext('2d');

        if (!window.isSecureContext) {
            alert("Camera requires a secure context (HTTPS or localhost).");
            this.stop();
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Browser does not support camera access.");
            this.stop();
            return;
        }

        try {
            // Check devices first
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoInputs = devices.filter(device => device.kind === 'videoinput');
            if (videoInputs.length === 0) {
                alert("No camera device detected.");
                this.stop();
                return;
            }

            // Fallback constraint logic
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } } 
                });
            } catch (err) {
                console.warn("Ideal constraints failed, trying fallback...", err);
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
            }

            this.localStream = stream;
            video.srcObject = this.localStream;
            
            // Wait for video to actually be ready
            video.onloadedmetadata = () => {
                video.play().then(() => {
                    // Capture loop
                    this.captureInterval = setInterval(() => {
                        if (this.ws && this.ws.readyState === WebSocket.OPEN && video.readyState >= 2) {
                            canvas.width = video.videoWidth;
                            canvas.height = video.videoHeight;
                            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                            
                            // Send binary JPEG to websocket
                            canvas.toBlob((blob) => {
                                if (blob && this.ws.readyState === WebSocket.OPEN) {
                                    this.ws.send(blob);
                                }
                            }, 'image/jpeg', 0.7);
                        }
                    }, 100); // ~10 FPS capture
                }).catch(e => {
                    console.error("Video play failed:", e);
                    this.stop();
                });
            };
            
        } catch (err) {
            console.error("Camera Error:", err);
            const errName = err.name || "UnknownError";
            const errMsg = err.message || String(err);
            
            // Show the exact error instead of mapping everything to permission denied
            alert(`Camera access failed.\nError Name: ${errName}\nError Message: ${errMsg}\n\nPlease check browser permissions, OS privacy settings, and ensure no other app is using the camera.`);
            
            this.stop();
        }
    },

    updateUI(data) {
        const img = document.getElementById(this.targetImgId);
        if (img) img.src = `data:image/jpeg;base64,${data.image}`;

        // Determine prefix based on target
        const pfx = this.targetImgId === 'video-feed' ? 'vid' : 'mon';
        
        const banner = document.getElementById(pfx === 'vid' ? 'video-status-banner' : 'monitoring-status-banner');

        const elFps = document.getElementById(`${pfx}-fps`);
        const elPersons = document.getElementById(`${pfx}-persons`);
        const elWeapons = document.getElementById(`${pfx}-weapons`);

        if (elFps) elFps.textContent = data.fps || 0;
        if (elPersons) elPersons.textContent = data.persons || 0;
        if (elWeapons) elWeapons.textContent = data.weapons || 0;

        if (banner) {
            if (data.threat_status) {
                banner.className = 'status-banner danger';
                banner.textContent = '🔴 ACTIVE THREAT DETECTED';
            } else {
                banner.className = 'status-banner safe';
                banner.textContent = '🟢 NO ACTIVE THREAT';
            }
        }
    },

    stop() {
        this.isMonitoring = false;
        if (this.ws) {
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'stop' }));
            }
            this.ws.close();
            this.ws = null;
        }

        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        // Reset UI
        document.getElementById('start-monitoring-btn').disabled = false;
        document.getElementById('stop-monitoring-btn').disabled = true;
        
        const bannerMon = document.getElementById('monitoring-status-banner');
        if(bannerMon) {
            bannerMon.className = 'status-banner safe';
            bannerMon.textContent = '🟢 NO ACTIVE THREAT';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Monitoring.init());
window.Monitoring = Monitoring;
