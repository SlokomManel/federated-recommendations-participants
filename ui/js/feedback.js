/**
 * Feedback Module
 * Handles star rating and text feedback submission
 */

let currentRating = 0;

const RATING_LABELS = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Very Good',
    5: 'Excellent!'
};

/**
 * Initialize feedback component
 */
function initFeedback() {
    const trigger = document.getElementById('feedback-trigger');
    const modal = document.getElementById('feedback-modal');
    const closeBtn = document.getElementById('close-feedback');
    const starButtons = document.querySelectorAll('.star-btn');
    const submitBtn = document.getElementById('submit-feedback');
    
    // Toggle modal
    trigger?.addEventListener('click', () => {
        const isHidden = modal.classList.contains('hidden');
        if (isHidden) {
            modal.classList.remove('hidden');
            setTimeout(() => {
                modal.classList.remove('scale-95', 'opacity-0');
                modal.classList.add('scale-100', 'opacity-100');
            }, 10);
        } else {
            closeFeedbackModal();
        }
        if (window.lucide) lucide.createIcons();
    });
    
    // Close button
    closeBtn?.addEventListener('click', closeFeedbackModal);
    
    // Star rating clicks
    starButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const rating = parseInt(btn.dataset.rating);
            setRating(rating);
        });
        
        // Hover effect
        btn.addEventListener('mouseenter', () => {
            highlightStars(parseInt(btn.dataset.rating));
        });
    });
    
    // Reset stars on mouse leave from container
    document.getElementById('star-rating')?.addEventListener('mouseleave', () => {
        highlightStars(currentRating);
    });
    
    // Submit feedback
    submitBtn?.addEventListener('click', submitFeedback);
}

/**
 * Close feedback modal
 */
function closeFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    if (modal) {
        modal.classList.add('scale-95', 'opacity-0');
        modal.classList.remove('scale-100', 'opacity-100');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 200);
    }
}

/**
 * Set the current rating
 */
function setRating(rating) {
    currentRating = rating;
    highlightStars(rating);
    
    const label = document.getElementById('rating-label');
    if (label) {
        label.textContent = RATING_LABELS[rating] || '';
    }
    
    // Enable submit button
    const submitBtn = document.getElementById('submit-feedback');
    if (submitBtn) {
        submitBtn.disabled = rating === 0;
    }
}

/**
 * Highlight stars up to the given rating
 */
function highlightStars(rating) {
    const buttons = document.querySelectorAll('.star-btn');
    buttons.forEach(btn => {
        const btnRating = parseInt(btn.dataset.rating);
        const icon = btn.querySelector('.star-icon');
        if (icon) {
            if (btnRating <= rating) {
                icon.classList.remove('text-gray-600');
                icon.classList.add('text-yellow-500', 'fill-yellow-500');
            } else {
                icon.classList.add('text-gray-600');
                icon.classList.remove('text-yellow-500', 'fill-yellow-500');
            }
        }
    });
}

/**
 * Submit feedback
 */
async function submitFeedback() {
    const submitBtn = document.getElementById('submit-feedback');
    const feedbackText = document.getElementById('feedback-text')?.value || '';
    
    if (currentRating === 0) {
        return;
    }
    
    // Disable button and show loading
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Sending...';
        if (window.lucide) lucide.createIcons();
    }
    
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rating: currentRating,
                feedback: feedbackText,
                timestamp: new Date().toISOString()
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit feedback');
        }
        
        // Show success
        showFeedbackSuccess();
        
    } catch (error) {
        console.error('Feedback error:', error);
        showFeedbackError();
    }
}

/**
 * Show success message after submission
 */
function showFeedbackSuccess() {
    const modal = document.getElementById('feedback-modal');
    if (modal) {
        modal.innerHTML = `
            <div class="p-6 text-center">
                <div class="w-16 h-16 bg-green-600/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i data-lucide="check-circle" class="w-8 h-8 text-green-500"></i>
                </div>
                <h3 class="text-white font-semibold text-lg mb-2">Thank You!</h3>
                <p class="text-gray-400 text-sm mb-4">Your feedback helps us improve.</p>
                <button onclick="closeFeedbackModal(); location.reload();" class="px-4 py-2 bg-netflix-gray hover:bg-gray-600 text-white rounded-lg transition-colors text-sm">
                    Close
                </button>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    }
}

/**
 * Show error message
 */
function showFeedbackError() {
    const submitBtn = document.getElementById('submit-feedback');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4"></i> Error - Try Again';
        submitBtn.classList.add('bg-red-600');
        submitBtn.classList.remove('bg-netflix-red');
        if (window.lucide) lucide.createIcons();
        
        // Reset after 3 seconds
        setTimeout(() => {
            submitBtn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Submit Feedback';
            submitBtn.classList.remove('bg-red-600');
            submitBtn.classList.add('bg-netflix-red');
            if (window.lucide) lucide.createIcons();
        }, 3000);
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initFeedback);

// Export for use in other modules
window.Feedback = {
    init: initFeedback,
    close: closeFeedbackModal
};
