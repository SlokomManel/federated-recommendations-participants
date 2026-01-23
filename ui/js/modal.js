/**
 * Modal Module
 * Handles the detail modal for show information
 */

// Current item being displayed in modal
let currentModalItem = null;

/**
 * Open the detail modal with show information
 * @param {Object} item - The recommendation item to display
 */
function openModal(item) {
    currentModalItem = item;
    const modal = document.getElementById('detail-modal');
    const overlay = document.getElementById('modal-overlay');
    
    if (!modal || !overlay) return;
    
    // Get current settings
    const settings = Settings.get();
    
    // Populate modal content
    populateModalContent(item, settings);
    
    // Show modal
    overlay.classList.remove('hidden');
    modal.classList.remove('hidden');
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
}

/**
 * Close the detail modal
 */
function closeModal() {
    const modal = document.getElementById('detail-modal');
    const overlay = document.getElementById('modal-overlay');
    
    if (modal) modal.classList.add('hidden');
    if (overlay) overlay.classList.add('hidden');
    
    // Restore body scroll
    document.body.style.overflow = '';
    
    currentModalItem = null;
}

/**
 * Populate modal content based on item and settings
 * @param {Object} item - The recommendation item
 * @param {Object} settings - Current user settings
 */
function populateModalContent(item, settings) {
    // Poster
    const posterEl = document.getElementById('modal-poster');
    if (posterEl) {
        posterEl.src = item.img || '';
        posterEl.alt = item.name || '';
        posterEl.onerror = () => {
            posterEl.src = 'https://via.placeholder.com/300x450?text=No+Image';
        };
    }
    
    // Title
    const titleEl = document.getElementById('modal-title');
    if (titleEl) titleEl.textContent = item.name || 'Unknown Title';
    
    // Meta info (rating, year, content rating)
    const metaEl = document.getElementById('modal-meta');
    if (metaEl) {
        const metaParts = [];
        
        // IMDB rating with stars
        if (item.imdb && item.imdb !== 'N/A') {
            const rating = parseFloat(item.imdb);
            if (!isNaN(rating)) {
                metaParts.push(`<span class="flex items-center gap-1"><i data-lucide="star" class="w-4 h-4 text-yellow-500 fill-yellow-500"></i> ${rating.toFixed(1)}</span>`);
            }
        }
        
        // Year
        if (item.release_year) {
            metaParts.push(`<span>${item.release_year}</span>`);
        }
        
        // Content rating
        if (item.rating) {
            metaParts.push(`<span class="px-2 py-0.5 bg-gray-700 rounded text-xs">${item.rating}</span>`);
        }
        
        // Duration
        if (item.duration) {
            metaParts.push(`<span>${item.duration}</span>`);
        }
        
        metaEl.innerHTML = metaParts.join('<span class="text-gray-500">|</span>');
    }
    
    // Genres
    const genresEl = document.getElementById('modal-genres');
    if (genresEl) {
        if (item.genres) {
            genresEl.textContent = item.genres;
            genresEl.classList.remove('hidden');
        } else {
            genresEl.classList.add('hidden');
        }
    }
    
    // Type (Movie/TV Show)
    const typeEl = document.getElementById('modal-type');
    if (typeEl) {
        if (item.type) {
            typeEl.textContent = item.type;
            typeEl.classList.remove('hidden');
        } else {
            typeEl.classList.add('hidden');
        }
    }
    
    // Description
    const descEl = document.getElementById('modal-description');
    if (descEl) {
        descEl.textContent = item.description || 'No description available.';
    }
    
    // Cast
    const castEl = document.getElementById('modal-cast');
    const castSection = document.getElementById('modal-cast-section');
    if (castEl && castSection) {
        if (item.cast) {
            castEl.textContent = item.cast;
            castSection.classList.remove('hidden');
        } else {
            castSection.classList.add('hidden');
        }
    }
    
    // Director
    const directorEl = document.getElementById('modal-director');
    const directorSection = document.getElementById('modal-director-section');
    if (directorEl && directorSection) {
        if (item.director) {
            directorEl.textContent = item.director;
            directorSection.classList.remove('hidden');
        } else {
            directorSection.classList.add('hidden');
        }
    }
    
    // Why Recommended section
    const whySection = document.getElementById('modal-why-section');
    if (whySection) {
        if (settings.showWhyRecommended) {
            whySection.classList.remove('hidden');
            const whyText = document.getElementById('modal-why-text');
            if (whyText) {
                // Generate a simple explanation based on score
                const score = item.raw_score || 0;
                const percentage = Math.min(100, Math.round(score * 100));
                whyText.textContent = `This show has a ${percentage}% match score based on your viewing history and preferences. The recommendation is generated using federated learning from community patterns while keeping your data private.`;
            }
        } else {
            whySection.classList.add('hidden');
        }
    }
    
    // Watchlist buttons
    const watchlistSection = document.getElementById('modal-watchlist-section');
    if (watchlistSection) {
        if (settings.enableWatchlist) {
            watchlistSection.classList.remove('hidden');
        } else {
            watchlistSection.classList.add('hidden');
        }
    }
    
    // Re-initialize Lucide icons in modal
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Handle "Will Watch" button click
 */
async function handleWillWatch() {
    if (!currentModalItem) return;
    
    try {
        const settings = Settings.get();
        
        // Get current page and visible items from AppState (exposed globally)
        const page = window.AppState?.currentPage || 1;
        const visibleItems = window.getCurrentPageItems ? window.getCurrentPageItems().map(i => i.name) : [];
        
        const result = await NetflixAPI.submitWatchlistAction(
            currentModalItem.id,
            currentModalItem.name,
            'will_watch',
            settings.useReranked,
            page,
            visibleItems
        );
        showModalToast('Added to your watchlist!', 'success');
        closeModal();
    } catch (error) {
        console.error('Error submitting will watch:', error);
        showModalToast('Failed to save. Please try again.', 'error');
    }
}

/**
 * Handle "Won't Watch" button click
 */
async function handleWontWatch() {
    if (!currentModalItem) return;
    
    try {
        const settings = Settings.get();
        
        // Get current page and visible items from AppState (exposed globally)
        const page = window.AppState?.currentPage || 1;
        const visibleItems = window.getCurrentPageItems ? window.getCurrentPageItems().map(i => i.name) : [];
        
        const result = await NetflixAPI.submitWatchlistAction(
            currentModalItem.id,
            currentModalItem.name,
            'wont_watch',
            settings.useReranked,
            page,
            visibleItems
        );
        showModalToast('Marked as not interested.', 'success');
        closeModal();
    } catch (error) {
        console.error('Error submitting wont watch:', error);
        showModalToast('Failed to save. Please try again.', 'error');
    }
}

/**
 * Show a toast message from modal actions
 */
function showModalToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-[60] transform transition-all duration-300 ${
        type === 'success' ? 'bg-green-600' : 'bg-red-600'
    } text-white`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('opacity-100'), 10);
    
    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Setup modal event listeners
 */
function setupModalListeners() {
    // Close button
    const closeBtn = document.getElementById('modal-close-btn');
    closeBtn?.addEventListener('click', closeModal);
    
    // Overlay click to close
    const overlay = document.getElementById('modal-overlay');
    overlay?.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
    
    // Escape key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('detail-modal');
            if (modal && !modal.classList.contains('hidden')) {
                closeModal();
            }
        }
    });
    
    // Watchlist buttons
    const willWatchBtn = document.getElementById('will-watch-btn');
    const wontWatchBtn = document.getElementById('wont-watch-btn');
    
    willWatchBtn?.addEventListener('click', handleWillWatch);
    wontWatchBtn?.addEventListener('click', handleWontWatch);
}

// Export for use in other modules
window.Modal = {
    open: openModal,
    close: closeModal,
    setupListeners: setupModalListeners,
    getCurrentItem: () => currentModalItem
};
