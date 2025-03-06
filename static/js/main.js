// BirthdayBuddy - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animations to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.classList.add('fade-in');
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Check for birthdays today
    checkBirthdaysToday();
});

// Check if there are birthdays today and show notification
function checkBirthdaysToday() {
    const birthdayElements = document.querySelectorAll('.badge.bg-success');
    
    if (birthdayElements.length > 0) {
        // Check if browser notifications are supported and enabled
        if ("Notification" in window && Notification.permission === "granted") {
            birthdayElements.forEach(element => {
                const name = element.closest('tr').querySelector('td:first-child').textContent.trim();
                new Notification("Birthday Today!", {
                    body: `Today is ${name}'s birthday! Don't forget to send your wishes.`,
                    icon: "/static/images/cake-icon.png"
                });
            });
        }
    }
}

// Format date for display
function formatDate(dateString) {
    const options = { month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Success
        showToast('Copied to clipboard!');
    }, function() {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        try {
            document.execCommand('copy');
            showToast('Copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
        
        document.body.removeChild(textarea);
    });
}

// Show toast notification
function showToast(message) {
    // Create toast element if it doesn't exist
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '5';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">BirthdayBuddy</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.getElementById('toast-container').insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 3000 });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Request notification permission
function requestNotificationPermission() {
    if ("Notification" in window) {
        Notification.requestPermission().then(function(permission) {
            if (permission === "granted") {
                showToast("Notifications enabled!");
            }
        });
    }
} 