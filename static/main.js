// Content Protection Demo
document.addEventListener('DOMContentLoaded', function() {
    // Disable right-click on protected content
    const protectedElements = document.querySelectorAll('.protected-content, .course-module, .content-item');

    protectedElements.forEach(element => {
        element.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showToast('Right-click is disabled to protect content');
            return false;
        });

        // Disable text selection
        element.style.userSelect = 'none';
        element.style.webkitUserSelect = 'none';
    });

    // Disable print/save shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'p':
                case 's':
                    if (document.querySelector('.protected-content')) {
                        e.preventDefault();
                        showToast('Printing/saving is disabled for protected content');
                    }
                    break;
            }
        }
    });

    // Video player protection
    const videoPlayers = document.querySelectorAll('video');
    videoPlayers.forEach(video => {
        video.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        });

        // Prevent downloading via developer tools
        Object.defineProperty(video, 'src', {
            writable: false
        });
    });
});

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#ef4444' : '#10b981'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 5px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Progress tracking
function updateProgress(contentId) {
    fetch(`/api/progress/${contentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${data.progress}%`;
            progressBar.textContent = `${data.progress}%`;
        }
    });
}

// Video playback tracking
function trackVideoPlayback(videoId, currentTime) {
    if (currentTime % 30 < 0.1) { // Every 30 seconds
        fetch('/api/track-playback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                videoId: videoId,
                timestamp: currentTime
            })
        });
    }
}

// Watermark overlay
function addWatermarkOverlay() {
    const watermark = document.createElement('div');
    watermark.id = 'dynamic-watermark';
    watermark.textContent = `Licensed to: ${document.body.dataset.userEmail || 'User'} | ${new Date().toLocaleDateString()}`;
    watermark.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: 40px;
        color: rgba(0,0,0,0.1);
        pointer-events: none;
        z-index: 9999;
        white-space: nowrap;
        user-select: none;
    `;

    const protectedArea = document.querySelector('.protected-content');
    if (protectedArea) {
        protectedArea.style.position = 'relative';
        protectedArea.appendChild(watermark);
    }
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize watermark on protected pages
if (document.querySelector('.protected-content')) {
    addWatermarkOverlay();
}