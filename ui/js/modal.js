/**
 * Modal Module
 * Handles the detail modal for show information
 */

// Current item being displayed in modal
let currentModalItem = null;

/**
 * Show loading state in modal
 */
function showModalLoading() {
    const modal = document.getElementById('detail-modal');
    const overlay = document.getElementById('modal-overlay');
    
    if (!modal || !overlay) return;
    
    // Show modal with loading state
    overlay.classList.remove('hidden');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Set loading placeholders
    const titleEl = document.getElementById('modal-title');
    if (titleEl) titleEl.textContent = 'Loading...';
    
    // Show image-off icon for loading state
    const posterContainer = document.getElementById('modal-poster-container');
    if (posterContainer) {
        posterContainer.innerHTML = `
            <div class="w-40 sm:w-44 aspect-[2/3] bg-netflix-gray rounded-lg shadow-lg flex items-center justify-center">
                <i data-lucide="loader" class="w-8 h-8 text-gray-500 animate-spin"></i>
            </div>
        `;
    }
    
    const metaEl = document.getElementById('modal-meta');
    if (metaEl) metaEl.innerHTML = '';
    
    const descEl = document.getElementById('modal-description');
    if (descEl) descEl.textContent = 'Loading details...';
    
    const genresEl = document.getElementById('modal-genres');
    if (genresEl) genresEl.classList.add('hidden');
    
    const typeEl = document.getElementById('modal-type');
    if (typeEl) typeEl.classList.add('hidden');
    
    const castSection = document.getElementById('modal-cast-section');
    if (castSection) castSection.classList.add('hidden');
    
    const directorSection = document.getElementById('modal-director-section');
    if (directorSection) directorSection.classList.add('hidden');
    
    const whySection = document.getElementById('modal-why-section');
    if (whySection) whySection.classList.add('hidden');
    
    const watchlistSection = document.getElementById('modal-watchlist-section');
    if (watchlistSection) watchlistSection.classList.add('hidden');
}

/**
 * Open the detail modal with show information
 * Fetches full details from server if item only has basic info (e.g., from history)
 * @param {Object} item - The recommendation item to display (must have at least id)
 */
async function openModal(item) {
    const modal = document.getElementById('detail-modal');
    const overlay = document.getElementById('modal-overlay');
    
    if (!modal || !overlay) return;
    
    // Check if item needs enrichment (missing description indicates incomplete data)
    const needsEnrichment = !item.description || item.description === '';
    
    if (needsEnrichment && item.id !== undefined) {
        // Show loading state first
        showModalLoading();
        
        try {
            // Fetch full details from server
            const result = await NetflixAPI.getMovieDetails(item.id);
            
            if (result.status === 'success' && result.item) {
                // Merge with original item to preserve any local data (like rank, clickedAt)
                currentModalItem = { ...item, ...result.item };
            } else {
                // Fallback to original item if fetch fails
                console.warn('Could not fetch movie details, using local data');
                currentModalItem = item;
            }
        } catch (error) {
            console.error('Error fetching movie details:', error);
            currentModalItem = item;
        }
    } else {
        currentModalItem = item;
    }
    
    // Get current settings
    const settings = Settings.get();
    
    // Populate modal content with full data
    populateModalContent(currentModalItem, settings);
    
    // Ensure modal is visible (may already be from loading state)
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
    // Poster - show image or image-off icon
    const posterContainer = document.getElementById('modal-poster-container');
    if (posterContainer) {
        if (item.img) {
            posterContainer.innerHTML = `
                <img 
                    id="modal-poster" 
                    src="${item.img}" 
                    alt="${item.name || ''}" 
                    class="w-40 sm:w-44 rounded-lg shadow-lg"
                />
            `;
        } else {
            posterContainer.innerHTML = `
                <div class="w-40 sm:w-44 aspect-[2/3] bg-netflix-gray rounded-lg shadow-lg flex items-center justify-center">
                    <i data-lucide="image-off" class="w-12 h-12 text-gray-600"></i>
                </div>
            `;
        }
    }
    
    // Title
    const titleEl = document.getElementById('modal-title');
    if (titleEl) {
        const hasRank = typeof item.rank === 'number' && !Number.isNaN(item.rank);
        // When "view details" is enabled, show rank in the modal header (e.g., "#44 Title")
        if (settings.showMoreDetails && hasRank) {
            titleEl.textContent = `#${item.rank} ${item.name || 'Unknown Title'}`;
        } else {
            titleEl.textContent = item.name || 'Unknown Title';
        }
    }
    
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
                // Debug: log item to console to inspect incoming item and counts
                console.debug('Modal item debug', item);

                // Prefer 'count' (0-100) if present; otherwise fall back to raw_score scaling
                let percentage = 0;
                if (typeof item.count === 'number' && !isNaN(item.count)) {
                    percentage = Math.max(0, Math.min(100, Math.round(item.count)));
                } else {
                    const score = (item.raw_score || 0);
                    if (score <= 1) {
                        percentage = Math.max(0, Math.min(100, Math.round(score * 100)));
                    } else {
                        percentage = Math.max(0, Math.min(100, Math.round(score)));
                    }
                }
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
 * Update click history with watchlist status
 * @param {string} itemId - The item ID
 * @param {string} status - 'will_watch' or 'wont_watch'
 */
function updateClickHistoryStatus(itemId, status) {
    try {
        const history = JSON.parse(localStorage.getItem('netflix_click_history') || '[]');
        const idx = history.findIndex(h => h.id === itemId);
        if (idx >= 0) {
            history[idx].status = status;
            history[idx].statusUpdatedAt = new Date().toISOString();
            localStorage.setItem('netflix_click_history', JSON.stringify(history));
            // Dispatch event for UI updates
            window.dispatchEvent(new CustomEvent('watchlistStatusChanged', { 
                detail: { id: itemId, status } 
            }));
        }
    } catch (error) {
        console.error('Error updating click history status:', error);
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
        const rank = (typeof currentModalItem.rank === 'number' && !Number.isNaN(currentModalItem.rank)) ? currentModalItem.rank : null;
        
        const result = await NetflixAPI.submitWatchlistAction(
            currentModalItem.id,
            currentModalItem.name,
            'will_watch',
            settings.useReranked,
            rank,
            page,
            visibleItems
        );
        
        // Update localStorage click history with status
        updateClickHistoryStatus(currentModalItem.id, 'will_watch');
        
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
        const rank = (typeof currentModalItem.rank === 'number' && !Number.isNaN(currentModalItem.rank)) ? currentModalItem.rank : null;
        
        const result = await NetflixAPI.submitWatchlistAction(
            currentModalItem.id,
            currentModalItem.name,
            'wont_watch',
            settings.useReranked,
            rank,
            page,
            visibleItems
        );
        
        // Update localStorage click history with status
        updateClickHistoryStatus(currentModalItem.id, 'wont_watch');
        
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
    getCurrentItem: () => currentModalItem,
    updateClickHistoryStatus: updateClickHistoryStatus
};
