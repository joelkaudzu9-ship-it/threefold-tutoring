// Content Protection Demo - Mobile Optimized
document.addEventListener('DOMContentLoaded', function() {
    // Disable right-click on protected content
    const protectedElements = document.querySelectorAll('.protected-content, .course-module, .content-item');

    protectedElements.forEach(element => {
        element.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showToast('Right-click is disabled to protect content', 'warning');
            return false;
        });

        // Disable text selection
        element.style.userSelect = 'none';
        element.style.webkitUserSelect = 'none';
        element.style.msUserSelect = 'none';
        
        // Prevent drag and drop
        element.setAttribute('draggable', 'false');
        
        // Add touch event protection
        element.addEventListener('touchstart', function(e) {
            // Prevent long-press text selection on mobile
            if (e.touches.length > 1) {
                e.preventDefault();
                showToast('Selection disabled to protect content', 'warning');
            }
        }, { passive: false });
    });

    // Disable print/save shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'p':
                case 's':
                    if (document.querySelector('.protected-content')) {
                        e.preventDefault();
                        showToast('Printing/saving is disabled for protected content', 'warning');
                    }
                    break;
            }
        }
    });

    // Mobile-specific protection
    if ('ontouchstart' in window) {
        // Prevent screenshot on mobile (as much as possible)
        document.addEventListener('visibilitychange', function() {
            if (document.hidden && document.querySelector('.protected-content')) {
                showToast('Content protected from screenshots', 'info');
            }
        });
        
        // Prevent text selection via long press
        document.addEventListener('selectionchange', function() {
            if (document.querySelector('.protected-content')) {
                const selection = window.getSelection();
                if (!selection.isCollapsed) {
                    selection.removeAllRanges();
                    showToast('Text selection disabled', 'warning');
                }
            }
        });
    }

    // Video player protection
    const videoPlayers = document.querySelectorAll('video');
    videoPlayers.forEach(video => {
        video.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showToast('Video controls disabled', 'warning');
            return false;
        });

        // Prevent downloading via developer tools
        Object.defineProperty(video, 'src', {
            writable: false
        });
        
        // Mobile video protection
        video.setAttribute('controlslist', 'nodownload');
        video.setAttribute('disablepictureinpicture', '');
        
        // Prevent AirPlay on iOS
        video.setAttribute('x-webkit-airplay', 'deny');
        
        video.addEventListener('play', function() {
            // Track video playback
            trackVideoPlayback(this.id || 'unknown-video', this.currentTime);
        });
    });

    // Initialize watermark on protected pages
    if (document.querySelector('.protected-content')) {
        addWatermarkOverlay();
    }
});

// Mobile-optimized Toast notifications
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Mobile-optimized styles
    const isMobile = window.innerWidth <= 768;
    
    toast.style.cssText = `
        position: fixed;
        ${isMobile ? 'bottom: 20px; left: 20px; right: 20px;' : 'top: 20px; right: 20px;'}
        background: ${getToastColor(type)};
        color: white;
        padding: ${isMobile ? '1rem' : '1rem 1.5rem'};
        border-radius: 8px;
        z-index: 10000;
        animation: ${isMobile ? 'slideUpMobile' : 'slideIn'} 0.3s ease;
        font-size: ${isMobile ? '0.9rem' : '1rem'};
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        word-wrap: break-word;
        max-width: ${isMobile ? 'calc(100vw - 40px)' : '300px'};
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = `${isMobile ? 'slideDownMobile' : 'slideOut'} 0.3s ease`;
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getToastColor(type) {
    const colors = {
        'info': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444'
    };
    return colors[type] || colors.info;
}

// Progress tracking - Mobile optimized
function updateProgress(contentId) {
    // Show loading state on mobile
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        showToast('Updating progress...', 'info');
    }
    
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
        
        if (isMobile && data.progress === 100) {
            showToast('Progress completed!', 'success');
        }
    })
    .catch(error => {
        console.error('Progress update failed:', error);
        if (isMobile) {
            showToast('Failed to update progress', 'error');
        }
    });
}

// Video playback tracking with mobile optimization
function trackVideoPlayback(videoId, currentTime) {
    // Only track every 30 seconds to reduce network requests on mobile
    if (currentTime % 30 < 0.1) {
        const data = {
            videoId: videoId,
            timestamp: currentTime,
            isMobile: window.innerWidth <= 768
        };
        
        fetch('/api/track-playback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .catch(error => {
            console.error('Playback tracking failed:', error);
        });
    }
}

// Mobile-optimized Watermark overlay
function addWatermarkOverlay() {
    // Remove existing watermark
    const existingWatermark = document.getElementById('dynamic-watermark');
    if (existingWatermark) existingWatermark.remove();
    
    const watermark = document.createElement('div');
    watermark.id = 'dynamic-watermark';
    
    const userEmail = document.body.dataset.userEmail || 'User';
    const userName = document.body.dataset.userName || 'Student';
    const today = new Date();
    const dateStr = today.toLocaleDateString();
    const timeStr = today.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    watermark.textContent = `${userName} | ${userEmail} | ${dateStr} ${timeStr}`;
    
    const isMobile = window.innerWidth <= 768;
    
    watermark.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: ${isMobile ? '20px' : '40px'};
        color: rgba(0,0,0,0.1);
        pointer-events: none;
        z-index: 9999;
        white-space: nowrap;
        user-select: none;
        font-weight: bold;
        opacity: 0.7;
        text-align: center;
        max-width: ${isMobile ? '200%' : '100%'};
        overflow: hidden;
        text-overflow: ellipsis;
    `;

    const protectedArea = document.querySelector('.protected-content');
    if (protectedArea) {
        protectedArea.style.position = 'relative';
        protectedArea.appendChild(watermark);
    }
}

// Add mobile animation keyframes
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
    
    @keyframes slideUpMobile {
        from { transform: translateY(100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes slideDownMobile {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(100%); opacity: 0; }
    }
    
    /* Mobile touch feedback */
    .touch-active {
        opacity: 0.8 !important;
        transform: scale(0.98) !important;
        transition: all 0.1s ease !important;
    }
    
    /* Prevent text selection on protected content */
    .protected-content * {
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }
    
    /* Allow selection in input fields */
    .protected-content input,
    .protected-content textarea {
        -webkit-user-select: text !important;
        user-select: text !important;
    }
    
    /* Loading overlay for protected content */
    .content-loading {
        position: relative;
    }
    
    .content-loading::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        color: #1e40af;
        z-index: 1000;
    }
`;
document.head.appendChild(style);

// Update watermark on resize (for responsive design)
window.addEventListener('resize', function() {
    if (document.querySelector('.protected-content')) {
        addWatermarkOverlay();
    }
});

// Initialize on page load
window.addEventListener('load', function() {
    // Add touch feedback to all interactive elements
    const touchElements = document.querySelectorAll('button, a, .clickable, .interactive');
    touchElements.forEach(element => {
        element.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        }, { passive: true });
        
        element.addEventListener('touchend', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
        
        element.addEventListener('touchcancel', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
    });
    
    // Protect against iframe embedding
    if (window !== window.top) {
        showToast('This content cannot be embedded', 'error');
        // Optionally redirect or hide content
    }
});

// Export functions for module use (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showToast,
        updateProgress,
        trackVideoPlayback,
        addWatermarkOverlay
    };
}
