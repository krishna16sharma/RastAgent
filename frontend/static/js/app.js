/**
 * RoadSense Frontend — Main Application
 *
 * Handles: video playback with annotation overlays, Google Maps hazard view,
 * video-map synchronization, voice alerts, and route summary display.
 */

// ==================== State ====================

let reportData = null;     // Current loaded report
let hazards = [];          // Hazard list
let gpsTrack = [];         // Full GPS trace
let map = null;            // Google Maps instance
let routePath = null;      // Polyline on map
let hazardMarkers = [];    // Map markers/circles
let positionMarker = null; // Current position marker
let voiceQueue = [];       // TTS queue
let isSpeaking = false;
let spokenHazards = new Set();
let showAnnotations = true;

// Severity colors matching CSS vars
const SEVERITY_COLORS = {
    1: '#3fb950',  // LOW - green
    2: '#d29922',  // MODERATE - yellow
    3: '#db6d28',  // HIGH - orange
    4: '#f85149',  // SEVERE - red
    5: '#da3633',  // CRITICAL - dark red
};

const SEVERITY_LABELS = {1: 'LOW', 2: 'MODERATE', 3: 'HIGH', 4: 'SEVERE', 5: 'CRITICAL'};

// ==================== Init ====================

document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await loadReportList();
    setupEventListeners();
});

async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        if (config.google_maps_api_key) {
            const script = document.getElementById('gmaps-script');
            script.onerror = () => {
                console.warn('Google Maps script failed to load, using fallback');
                initMap();
            };
            // Fallback if Google Maps fails to call initMap (e.g. invalid key)
            setTimeout(() => {
                if (!map) initMap();
            }, 5000);
            script.src = `https://maps.googleapis.com/maps/api/js?key=${config.google_maps_api_key}&callback=initMap`;
            window.initMap = initMap;
        } else {
            initMap();
        }
    } catch (e) {
        console.warn('Config load failed, initializing map without API key');
        initMap();
    }
}

function initMap() {
    const mapEl = document.getElementById('map');
    if (typeof google !== 'undefined' && google.maps) {
        map = new google.maps.Map(mapEl, {
            center: { lat: 12.9716, lng: 77.5946 }, // Bangalore default
            zoom: 13,
            styles: darkMapStyle(),
            disableDefaultUI: true,
            zoomControl: true,
        });
    } else {
        mapEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#8b949e;font-size:14px;">Google Maps API key required for map view</div>';
    }
}

async function loadReportList() {
    try {
        const res = await fetch('/api/reports');
        const reports = await res.json();
        const select = document.getElementById('report-select');
        reports.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.file;
            opt.textContent = `${r.name} (${r.total_hazards} hazards, score: ${r.quality_score || '?'}/10)`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load reports:', e);
    }
}

function setupEventListeners() {
    document.getElementById('report-select').addEventListener('change', (e) => {
        if (e.target.value) loadReport(e.target.value);
    });

    document.getElementById('toggle-raw').addEventListener('click', toggleAnnotations);

    const video = document.getElementById('video-player');
    video.addEventListener('timeupdate', onVideoTimeUpdate);
    video.addEventListener('loadedmetadata', onVideoLoaded);

    // Resize canvas with video
    window.addEventListener('resize', resizeCanvas);
}

// ==================== Report Loading ====================

async function loadReport(filename) {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('hidden');

    try {
        const res = await fetch(`/api/report/${filename}`);
        reportData = await res.json();
        hazards = reportData.hazards || [];
        gpsTrack = reportData.gps_track || [];

        // Load video if available — prefer video_filename, fall back to path basename
        const videoName = reportData.video_filename
            || (reportData.video ? reportData.video.split('/').pop() : null);
        if (videoName) {
            const video = document.getElementById('video-player');
            video.src = `/api/video/${videoName}`;

            // Auto-seek to GPS start if available
            const gpsStartSec = reportData.gps_start_sec || 0;
            if (gpsStartSec > 0) {
                video.addEventListener('loadedmetadata', () => {
                    video.currentTime = gpsStartSec;
                }, { once: true });
            }
        }

        // Update map
        updateMap();

        // Update summary
        updateSummary(reportData.summary || {});

        // Show controls
        document.getElementById('toggle-raw').style.display = 'inline-block';
        document.getElementById('summary-panel').style.display = 'block';

        // Reset voice tracking
        spokenHazards.clear();

    } catch (e) {
        console.error('Failed to load report:', e);
    } finally {
        overlay.classList.add('hidden');
    }
}

// ==================== Video Annotations ====================

function onVideoLoaded() {
    resizeCanvas();
}

function resizeCanvas() {
    const video = document.getElementById('video-player');
    const canvas = document.getElementById('annotation-canvas');
    const container = document.getElementById('video-container');

    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}

function onVideoTimeUpdate() {
    const video = document.getElementById('video-player');
    const currentTime = video.currentTime;

    if (showAnnotations) {
        drawAnnotations(currentTime);
        showAdvisory(currentTime);
    }

    updateMapPosition(currentTime);
    checkVoiceAlerts(currentTime);
}

function drawAnnotations(currentTime) {
    const canvas = document.getElementById('annotation-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!hazards.length) return;

    // Find hazards visible at current time (within 3s window)
    const visible = hazards.filter(h => {
        const t = h.timestamp_sec || 0;
        return currentTime >= t - 0.5 && currentTime <= t + 3;
    });

    visible.forEach(h => {
        const bb = h.bounding_box;
        if (!bb) return;

        const color = SEVERITY_COLORS[h.severity] || '#fff';
        const x = bb.x_min * canvas.width;
        const y = bb.y_min * canvas.height;
        const w = (bb.x_max - bb.x_min) * canvas.width;
        const hh = (bb.y_max - bb.y_min) * canvas.height;

        // Draw bounding box
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, hh);

        // Semi-transparent fill
        ctx.fillStyle = color + '20';
        ctx.fillRect(x, y, w, hh);

        // Label background
        const label = `${h.category} (${h.severity})`;
        ctx.font = 'bold 12px sans-serif';
        const metrics = ctx.measureText(label);
        const labelH = 18;
        ctx.fillStyle = color;
        ctx.fillRect(x, y - labelH, metrics.width + 8, labelH);

        // Label text
        ctx.fillStyle = '#000';
        ctx.fillText(label, x + 4, y - 4);
    });
}

function showAdvisory(currentTime) {
    const banner = document.getElementById('advisory-banner');

    const active = hazards.find(h => {
        const t = h.timestamp_sec || 0;
        return currentTime >= t - 1 && currentTime <= t + 3;
    });

    if (active && active.driver_action) {
        banner.textContent = active.driver_action;
        banner.style.borderLeftColor = SEVERITY_COLORS[active.severity] || '#db6d28';
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

function toggleAnnotations() {
    showAnnotations = !showAnnotations;
    const btn = document.getElementById('toggle-raw');
    btn.textContent = showAnnotations ? 'Show Raw Video' : 'Show Annotations';

    if (!showAnnotations) {
        const canvas = document.getElementById('annotation-canvas');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        document.getElementById('advisory-banner').classList.add('hidden');
    }
}

// ==================== Google Maps ====================

function updateMap() {
    if (!map) return;

    // Clear existing
    hazardMarkers.forEach(m => m.setMap(null));
    hazardMarkers = [];
    if (routePath) routePath.setMap(null);
    if (positionMarker) positionMarker.setMap(null);

    // Draw GPS track as polyline
    if (gpsTrack.length > 0) {
        const path = gpsTrack
            .filter((_, i) => i % 5 === 0) // subsample for perf
            .map(p => ({ lat: p.lat, lng: p.lon || p.lng }));

        routePath = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: '#58a6ff',
            strokeOpacity: 0.6,
            strokeWeight: 4,
            map: map,
        });

        // Fit map bounds
        const bounds = new google.maps.LatLngBounds();
        path.forEach(p => bounds.extend(p));
        map.fitBounds(bounds, 50);
    }

    // Draw hazard circles
    hazards.forEach((h, i) => {
        if (!h.gps) return;

        const color = SEVERITY_COLORS[h.severity] || '#fff';
        const circle = new google.maps.Circle({
            center: { lat: h.gps.lat, lng: h.gps.lng },
            radius: 30 + (h.severity * 15), // Scale by severity
            fillColor: color,
            fillOpacity: 0.35,
            strokeColor: color,
            strokeOpacity: 0.8,
            strokeWeight: 2,
            map: map,
        });

        // Info window on click
        const info = new google.maps.InfoWindow({
            content: `
                <div style="color:#000;max-width:200px;">
                    <strong>${h.category}</strong> (Severity ${h.severity})<br>
                    <em>${h.description || ''}</em><br>
                    <span style="color:#666;">${h.driver_action || ''}</span>
                </div>
            `,
        });

        circle.addListener('click', () => {
            info.setPosition({ lat: h.gps.lat, lng: h.gps.lng });
            info.open(map);
        });

        circle._hazardIndex = i;
        circle._severity = h.severity;
        hazardMarkers.push(circle);
    });

    // Position marker (current video position)
    if (gpsTrack.length > 0) {
        const first = gpsTrack[0];
        positionMarker = new google.maps.Marker({
            position: { lat: first.lat, lng: first.lon || first.lng },
            map: map,
            icon: {
                path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                scale: 5,
                fillColor: '#58a6ff',
                fillOpacity: 1,
                strokeColor: '#fff',
                strokeWeight: 2,
                rotation: 0,
            },
            zIndex: 999,
        });
    }
}

function updateMapPosition(currentTime) {
    if (!map || !gpsTrack.length || !positionMarker) return;

    // Find the GPS sample closest to current video time
    // GPS cts is in ms, video time is in sec
    const targetMs = currentTime * 1000;
    let closest = gpsTrack[0];
    let minDiff = Infinity;

    for (const p of gpsTrack) {
        const diff = Math.abs(p.cts - targetMs);
        if (diff < minDiff) {
            minDiff = diff;
            closest = p;
        }
        if (p.cts > targetMs + 5000) break; // early exit
    }

    const pos = { lat: closest.lat, lng: closest.lon || closest.lng };
    positionMarker.setPosition(pos);

    // Update hazard circle opacity — upcoming pulse, past fade
    hazardMarkers.forEach(circle => {
        const h = hazards[circle._hazardIndex];
        if (!h || !h.timestamp_sec) return;

        const dt = h.timestamp_sec - currentTime;
        if (dt > 0 && dt < 10) {
            // Upcoming — pulse
            circle.setOptions({ fillOpacity: 0.5 + 0.2 * Math.sin(Date.now() / 300) });
        } else if (dt < 0) {
            // Past — fade
            circle.setOptions({ fillOpacity: 0.15 });
        } else {
            circle.setOptions({ fillOpacity: 0.35 });
        }
    });
}

// ==================== Voice Alerts ====================

function checkVoiceAlerts(currentTime) {
    if (!('speechSynthesis' in window)) return;

    hazards.forEach((h, i) => {
        if (!h.driver_action || !h.timestamp_sec) return;

        const alertTime = h.timestamp_sec - 2; // Alert 2s before
        if (currentTime >= alertTime && currentTime < alertTime + 1 && !spokenHazards.has(i)) {
            spokenHazards.add(i);
            speak(h.driver_action);
        }
    });
}

function speak(text) {
    if (!('speechSynthesis' in window)) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.1;
    utterance.pitch = 1;
    utterance.volume = 0.8;

    // Cancel overlapping speech
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }

    speechSynthesis.speak(utterance);
}

// ==================== Summary Panel ====================

function updateSummary(summary) {
    document.getElementById('quality-score').textContent = summary.route_quality_score || '-';
    document.getElementById('total-hazards').textContent = summary.total_hazards || 0;

    // Quality score color
    const score = summary.route_quality_score || 0;
    const scoreEl = document.getElementById('quality-score');
    if (score >= 7) scoreEl.style.color = '#3fb950';
    else if (score >= 4) scoreEl.style.color = '#d29922';
    else scoreEl.style.color = '#f85149';

    // Severity distribution
    const sevBars = document.getElementById('severity-bars');
    sevBars.innerHTML = '';
    const sevDist = summary.severity_distribution || {};
    const maxSev = Math.max(1, ...Object.values(sevDist));

    ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'CRITICAL'].forEach((label, i) => {
        const count = sevDist[label] || 0;
        const bar = document.createElement('div');
        bar.className = 'severity-bar';
        bar.style.height = `${Math.max(4, (count / maxSev) * 40)}px`;
        bar.style.background = SEVERITY_COLORS[i + 1];
        bar.setAttribute('data-count', count);
        bar.title = `${label}: ${count}`;
        sevBars.appendChild(bar);
    });

    // Category breakdown
    const catList = document.getElementById('category-list');
    catList.innerHTML = '';
    const catBreakdown = summary.hazard_breakdown || {};
    Object.entries(catBreakdown).forEach(([cat, count]) => {
        if (count === 0) return;
        const tag = document.createElement('span');
        tag.className = 'category-tag';
        tag.innerHTML = `${cat.replace('_', ' ')}<span class="count">${count}</span>`;
        catList.appendChild(tag);
    });

    // Route briefing
    const briefing = document.getElementById('route-briefing');
    briefing.textContent = summary.route_briefing || '';

    // Worst segment
    const worst = summary.worst_segment;
    if (worst && worst.description) {
        document.getElementById('worst-segment').style.display = 'block';
        document.getElementById('worst-segment-text').textContent =
            `${worst.description} — ${worst.reason || ''}`;
    }
}

// ==================== Map Dark Style ====================

function darkMapStyle() {
    return [
        { elementType: 'geometry', stylers: [{ color: '#1d2c4d' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#8ec3b9' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#1a3646' }] },
        { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#304a7d' }] },
        { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#255763' }] },
        { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#2c6675' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#17263c' }] },
        { featureType: 'poi', stylers: [{ visibility: 'off' }] },
        { featureType: 'transit', stylers: [{ visibility: 'off' }] },
    ];
}
