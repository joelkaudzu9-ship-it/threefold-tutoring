// ===========================================
// UNIVERSAL MOBILE BASE SCRIPT
// Applies to ALL templates
// ===========================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile navigation
    initMobileNavigation();
    
    // Initialize touch-friendly elements
    initTouchFriendlyElements();
    
    // Initialize responsive tables
    initResponsiveTables();
    
    // Initialize form handling for mobile
    initMobileForms();
    
    // Initialize flash messages
    initFlashMessages();
    
    // Initialize image lazy loading
    initLazyLoading();
    
    // Detect device and add appropriate classes
    detectDevice();
    
    // Handle orientation changes
    initOrientationHandler();
    
    // Initialize service worker for offline support
    initServiceWorker();
});

// ===========================================
// MOBILE NAVIGATION
// ===========================================

function initMobileNavigation() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileNav = document.getElementById('mobileNav');
    const mobileNavOverlay = document.getElementById('mobileNavOverlay');
    const mobileNavClose = document.getElementById('mobileNavClose');
    
    if (mobileMenuToggle && mobileNav) {
        // Toggle mobile menu
        mobileMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            mobileNav.classList.add('active');
            mobileNavOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
        
        // Close mobile menu
        const closeMobileMenu = function() {
            mobileNav.classList.remove('active');
            mobileNavOverlay.classList.remove('active');
            document.body.style.overflow = '';
        };
        
        if (mobileNavClose) {
            mobileNavClose.addEventListener('click', closeMobileMenu);
        }
        
        if (mobileNavOverlay) {
            mobileNavOverlay.addEventListener('click', closeMobileMenu);
        }
        
        // Close menu when clicking on a link (except external links)
        mobileNav.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                const link = e.target.tagName === 'A' ? e.target : e.target.closest('a');
                if (link.href && !link.target && !link.hasAttribute('download')) {
                    setTimeout(closeMobileMenu, 300);
                }
            }
        });
        
        // Close menu with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && mobileNav.classList.contains('active')) {
                closeMobileMenu();
            }
        });
        
        // Handle swipe to close on mobile
        let touchStartX = 0;
        let touchEndX = 0;
        
        mobileNav.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        mobileNav.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            const swipeDistance = touchStartX - touchEndX;
            
            // If swiped right (closing direction)
            if (swipeDistance > 50) {
                closeMobileMenu();
            }
        }, { passive: true });
    }
}

// ===========================================
// TOUCH-FRIENDLY ELEMENTS
// ===========================================

function initTouchFriendlyElements() {
    // All interactive elements that should be touch-friendly
    const touchElements = document.querySelectorAll(
        'button, .btn, a[href], input[type="submit"], input[type="button"], ' +
        'select, .clickable, .interactive, .nav-links a, .sidebar-nav a'
    );
    
    touchElements.forEach(element => {
        // Ensure minimum touch target size (44x44px)
        const rect = element.getBoundingClientRect();
        if (rect.width < 44 || rect.height < 44) {
            element.style.minWidth = '44px';
            element.style.minHeight = '44px';
            element.style.padding = '12px 16px';
        }
        
        // Add touch feedback
        element.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        }, { passive: true });
        
        element.addEventListener('touchend', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
        
        element.addEventListener('touchcancel', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
        
        // Prevent zoom on double-tap for buttons
        element.addEventListener('touchstart', function(e) {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });
    });
    
    // Make links in tables touch-friendly on mobile
    if (window.innerWidth <= 768) {
        const tableLinks = document.querySelectorAll('table a');
        tableLinks.forEach(link => {
            link.style.display = 'inline-block';
            link.style.minHeight = '44px';
            link.style.lineHeight = '44px';
            link.style.padding = '0 12px';
        });
    }
}

// ===========================================
// RESPONSIVE TABLES
// ===========================================

function initResponsiveTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Wrap tables for responsive scrolling
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
        
        // Make table headers sticky on mobile
        if (window.innerWidth <= 768) {
            const headers = table.querySelectorAll('th');
            headers.forEach(header => {
                header.style.position = 'sticky';
                header.style.top = '0';
                header.style.background = '#f9fafb';
                header.style.zIndex = '1';
            });
        }
    });
}

// ===========================================
// MOBILE FORM HANDLING
// ===========================================

function initMobileForms() {
    // Prevent iOS zoom on input focus
    const inputs = document.querySelectorAll(
        'input[type="text"], input[type="email"], input[type="password"], ' +
        'input[type="tel"], input[type="number"], textarea'
    );
    
    inputs.forEach(input => {
        // Set font size to 16px to prevent zoom on iOS
        input.style.fontSize = '16px';
        
        // Handle focus on mobile
        input.addEventListener('focus', function() {
            // Scroll input into view on mobile
            if (window.innerWidth <= 768) {
                setTimeout(() => {
                    this.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            }
        });
        
        // Handle file inputs on mobile
        if (input.type === 'file') {
            input.addEventListener('change', function() {
                if (this.files.length > 0) {
                    showToast(`File selected: ${this.files[0].name}`, 'success');
                }
            });
        }
    });
    
    // Handle form submission on mobile
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add loading state
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.disabled = true;
                
                // Restore button after 10 seconds (in case of error)
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 10000);
            }
            
            // Validate required fields
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#ef4444';
                    field.addEventListener('input', function() {
                        this.style.borderColor = '#d1d5db';
                    }, { once: true });
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showToast('Please fill in all required fields', 'error');
                
                // Re-enable button if validation fails
                if (submitBtn) {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            }
        });
    });
}

// ===========================================
// FLASH MESSAGES
// ===========================================

function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            dismissFlashMessage(message);
        }, 5000);
        
        // Add close button functionality
        const closeBtn = message.querySelector('.flash-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                dismissFlashMessage(message);
            });
        }
    });
    
    function dismissFlashMessage(message) {
        message.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 300);
    }
}

// ===========================================
// LAZY LOADING IMAGES
// ===========================================

function initLazyLoading() {
    // Only on mobile to save data
    if (window.innerWidth <= 768) {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
}

// ===========================================
// DEVICE DETECTION
// ===========================================

function detectDevice() {
    const userAgent = navigator.userAgent.toLowerCase();
    
    // Add device classes to body
    if (/mobile|android|iphone|ipad|ipod/.test(userAgent)) {
        document.body.classList.add('is-mobile');
        
        if (/iphone|ipad|ipod/.test(userAgent)) {
            document.body.classList.add('is-ios');
        } else if (/android/.test(userAgent)) {
            document.body.classList.add('is-android');
        }
    } else {
        document.body.classList.add('is-desktop');
    }
    
    // Add touch capability class
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        document.body.classList.add('has-touch');
    } else {
        document.body.classList.add('no-touch');
    }
    
    // Add orientation class
    updateOrientationClass();
}

// ===========================================
// ORIENTATION HANDLER
// ===========================================

function initOrientationHandler() {
    // Update on orientation change
    window.addEventListener('orientationchange', function() {
        setTimeout(updateOrientationClass, 100);
        setTimeout(initTouchFriendlyElements, 200);
    });
    
    // Update on resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            updateOrientationClass();
            initTouchFriendlyElements();
            initResponsiveTables();
        }, 250);
    });
}

function updateOrientationClass() {
    document.body.classList.remove('portrait', 'landscape');
    
    if (window.innerHeight > window.innerWidth) {
        document.body.classList.add('portrait');
    } else {
        document.body.classList.add('landscape');
    }
}

// ===========================================
// SERVICE WORKER FOR OFFLINE SUPPORT
// ===========================================

function initServiceWorker() {
    if ('serviceWorker' in navigator && window.innerWidth <= 768) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful');
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    }
}

// ===========================================
// UTILITY FUNCTIONS
// ===========================================

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.custom-toast');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${type}`;
    toast.textContent = message;
    
    // Position based on device
    const isMobile = window.innerWidth <= 768;
    
    toast.style.cssText = `
        position: fixed;
        ${isMobile ? 'bottom: 20px; left: 20px; right: 20px;' : 'top: 20px; right: 20px;'}
        background: ${getToastColor(type)};
        color: white;
        padding: ${isMobile ? '1rem' : '1rem 1.5rem'};
        border-radius: 8px;
        z-index: 9999;
        animation: ${isMobile ? 'slideUpMobile 0.3s ease' : 'slideIn 0.3s ease'};
        font-size: ${isMobile ? '0.9rem' : '1rem'};
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        word-wrap: break-word;
        max-width: ${isMobile ? 'calc(100vw - 40px)' : '300px'};
    `;
    
    document.body.appendChild(toast);
    
    // Auto dismiss
    setTimeout(() => {
        toast.style.animation = `${isMobile ? 'slideDownMobile 0.3s ease' : 'slideOut 0.3s ease'}`;
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
    
    // Add close button for longer toasts
    if (duration > 5000) {
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0 0.5rem;
            margin-left: 1rem;
        `;
        closeBtn.addEventListener('click', () => {
            toast.style.animation = `${isMobile ? 'slideDownMobile 0.3s ease' : 'slideOut 0.3s ease'}`;
            setTimeout(() => toast.remove(), 300);
        });
        toast.appendChild(closeBtn);
    }
}

function getToastColor(type) {
    const colors = {
        'success': '#10b981',
        'error': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6'
    };
    return colors[type] || colors.info;
}

// Copy to clipboard utility
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
            .then(() => showToast('Copied to clipboard', 'success'))
            .catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('Copied to clipboard', 'success');
    } catch (err) {
        showToast('Failed to copy', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Form validation helper
function validateForm(form) {
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;
    const errors = [];
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');
            errors.push(`${input.name || input.id} is required`);
        } else {
            input.classList.remove('error');
            
            // Email validation
            if (input.type === 'email') {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(input.value)) {
                    isValid = false;
                    input.classList.add('error');
                    errors.push('Please enter a valid email address');
                }
            }
            
            // Password length validation
            if (input.type === 'password' && input.value.length < 6) {
                isValid = false;
                input.classList.add('error');
                errors.push('Password must be at least 6 characters');
            }
        }
    });
    
    return { isValid, errors };
}

// Add CSS animations for toasts
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes slideUpMobile {
        from { transform: translateY(100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes slideDownMobile {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(100%); opacity: 0; }
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .touch-active {
        opacity: 0.8;
        transform: scale(0.98);
        transition: all 0.1s ease;
    }
    
    .error {
        border-color: #ef4444 !important;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
    }
`;
document.head.appendChild(toastStyles);

// Export functions for use in other scripts
window.mobileUtils = {
    showToast,
    copyToClipboard,
    validateForm,
    detectDevice
};

// Add this to handle page transitions
window.addEventListener('beforeunload', function() {
    document.body.classList.add('page-transition');
});

window.addEventListener('load', function() {
    document.body.classList.remove('page-transition');
});
