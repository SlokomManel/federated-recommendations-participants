/**
 * Main Application Logic for Federated Recommendations UI
 */

// Application state
const AppState = {
    status: 'loading',
    rawRecommendations: [],
    rerankedRecommendations: [],
    userEmail: '',
    error: null,
    pollingInterval: null,
    currentPage: 1,
    itemsPerPage: 5,
    totalPages: 1,
    allGenres: [],
    genreFilters: {} // { genre: 'required' | 'blocked' | null }
};

// Genre filter storage key
const GENRE_FILTERS_KEY = 'netflix_genre_filters';

// Privacy acceptance key
const PRIVACY_ACCEPTED_KEY = 'netflix_privacy_accepted';

// Global V mtime tracking key (for detecting aggregator updates)
const GLOBAL_V_MTIME_KEY = 'netflix_global_v_mtime';

// DOM Elements
const elements = {
    loadingSection: () => document.getElementById('loading-section'),
    errorSection: () => document.getElementById('error-section'),
    contentSection: () => document.getElementById('content-section'),
    computeSection: () => document.getElementById('compute-section'),
    uploadSection: () => document.getElementById('upload-section'),
    recommendationsContainer: () => document.getElementById('recommendations-container'),
    statusMessage: () => document.getElementById('status-message'),
    errorMessage: () => document.getElementById('error-message'),
    computeBtn: () => document.getElementById('compute-btn'),
    retryBtn: () => document.getElementById('retry-btn'),
    refreshBtn: () => document.getElementById('refresh-btn'),
    dropZone: () => document.getElementById('drop-zone'),
    fileInput: () => document.getElementById('file-input'),
    uploadStatus: () => document.getElementById('upload-status'),
    listTypeBadge: () => document.getElementById('list-type-badge'),
    listTypeText: () => document.getElementById('list-type-text'),
    // Pagination elements
    prevPageBtn: () => document.getElementById('prev-page-btn'),
    nextPageBtn: () => document.getElementById('next-page-btn'),
    currentPageEl: () => document.getElementById('current-page'),
    totalPagesEl: () => document.getElementById('total-pages'),
    paginationControls: () => document.getElementById('pagination-controls')
};

/**
 * Check if privacy policy has been accepted
 */
function isPrivacyAccepted() {
    return localStorage.getItem(PRIVACY_ACCEPTED_KEY) === 'true';
}

/**
 * Show privacy modal
 */
function showPrivacyModal() {
    const overlay = document.getElementById('privacy-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
        if (window.lucide) {
            lucide.createIcons();
        }
    }
}

/**
 * Hide privacy modal
 */
function hidePrivacyModal() {
    const overlay = document.getElementById('privacy-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Handle privacy acceptance
 */
function acceptPrivacy() {
    localStorage.setItem(PRIVACY_ACCEPTED_KEY, 'true');
    hidePrivacyModal();
    continueAppInit();
}

/**
 * Handle privacy decline
 */
function declinePrivacy() {
    // Show a message that the app cannot be used without acceptance
    const overlay = document.getElementById('privacy-overlay');
    if (overlay) {
        overlay.innerHTML = `
            <div class="bg-netflix-dark rounded-xl max-w-md w-full shadow-2xl p-6 text-center">
                <div class="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i data-lucide="lock" class="w-8 h-8 text-gray-400"></i>
                </div>
                <h2 class="text-xl font-bold text-white mb-2">Access Restricted</h2>
                <p class="text-gray-400 mb-6">
                    You need to accept the privacy notice to use this application.
                </p>
                <button onclick="location.reload()" class="px-6 py-3 bg-netflix-gray hover:bg-gray-600 text-white rounded-lg transition-colors">
                    Try Again
                </button>
            </div>
        `;
        if (window.lucide) {
            lucide.createIcons();
        }
    }
}

/**
 * Initialize the application
 */
async function initApp() {
    console.log('Initializing Federated Recommendations App...');
    
    // Check privacy acceptance first
    if (!isPrivacyAccepted()) {
        showPrivacyModal();
        return; // Don't continue until accepted
    }
    
    continueAppInit();
}

/**
 * Continue app initialization after privacy is accepted
 */
async function continueAppInit() {
    showLoading('Checking recommendation status...');
    
    // Initialize settings
    Settings.init();
    Settings.setupListeners();
    
    // Initialize modal
    Modal.setupListeners();
    
    // Load user info
    loadUserInfo();
    
    // Listen for settings changes to re-render
    window.addEventListener('settingsChanged', (e) => {
        if (AppState.status === 'ready') {
            // Reset to page 1 when switching list types
            if (e.detail?.useReranked !== undefined) {
                AppState.currentPage = 1;
            }
            displayRecommendations();
        }
    });
    
    try {
        await checkStatusAndLoad();
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
    
    // Re-initialize icons after any dynamic content
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Load user information
 */
async function loadUserInfo() {
    try {
        const user = await NetflixAPI.getUser();
        AppState.userEmail = user.email;
        Settings.updateUserDisplay(user.email);
    } catch (error) {
        console.error('Failed to load user info:', error);
    }
}

/**
 * Check status and load recommendations if available
 * Shows upload section if no viewing history, auto-triggers FL workflow otherwise
 */
async function checkStatusAndLoad() {
    try {
        const status = await NetflixAPI.getStatus();
        console.log('Status:', status);
        
        // First check if viewing history exists
        if (!status.has_viewing_history) {
            console.log('No viewing history found, showing upload section...');
            showUploadSection();
            return;
        }
        
        // Check if FL workflow is running (training model)
        if (status.status === 'running' || status.status === 'fine_tuning') {
            console.log('FL workflow in progress...');
            showLoading(status.message || 'Fine-tuning your personalized model...');
            startFLPolling();
            return;
        }
        
        // Check if recommendation computation is running
        if (status.status === 'computing') {
            console.log('Computing recommendations...');
            showLoading('Computing recommendations...');
            startPolling();
            return;
        }
        
        // Ready state with recommendations - check for global_V changes first
        if (status.status === 'ready' && status.has_recommendations) {
            // Check if global_V has been updated by aggregator
            const shouldRefresh = await checkGlobalVChanged();
            
            if (shouldRefresh) {
                console.log('Global model updated by aggregator, auto-triggering FL workflow...');
                showLoading('New global model detected! Updating your recommendations...');
                try {
                    const clickHistory = getClickHistory();
                    await NetflixAPI.triggerRefresh(clickHistory);
                    startFLPolling();
                } catch (refreshError) {
                    console.error('Auto-refresh error:', refreshError);
                    // Fall back to showing existing recommendations
                    await loadAndDisplayRecommendations();
                }
                return;
            }
            
            await loadAndDisplayRecommendations();
            return;
        }
        
        // No recommendations and no FL running - auto-trigger FL workflow
        console.log('No recommendations found, auto-triggering FL workflow...');
        showLoading('Fine-tuning your personalized model...');
        try {
            const clickHistory = getClickHistory();
            await NetflixAPI.triggerRefresh(clickHistory);
            startFLPolling();
        } catch (computeError) {
            console.error('Auto-compute error:', computeError);
            showError('Failed to start training. Please try again.');
        }
    } catch (error) {
        console.error('Status check error:', error);
        showError('Failed to check status. Server may be unavailable.');
    }
}

/**
 * Load and display recommendations
 */
async function loadAndDisplayRecommendations() {
    showLoading('Loading recommendations...');
    
    try {
        const data = await NetflixAPI.getRecommendations();
        
        if (data.error) {
            showComputeSection();
            return;
        }
        
        // Attach stable 1-based rank based on full list ordering (pre-filters)
        AppState.rawRecommendations = (data.raw_recommendations || []).map((item, idx) => ({
            ...item,
            rank: idx + 1
        }));
        AppState.rerankedRecommendations = (data.reranked_recommendations || []).map((item, idx) => ({
            ...item,
            rank: idx + 1
        }));
        AppState.userEmail = data.user_email || AppState.userEmail;
        AppState.status = 'ready';
        
        // Extract all genres from both lists for filtering
        const allRecs = [...AppState.rawRecommendations, ...AppState.rerankedRecommendations];
        AppState.allGenres = extractAllGenres(allRecs);
        
        // Load saved genre filters
        loadGenreFilters();
        
        // Update user display if we got it from recommendations
        if (data.user_email) {
            Settings.updateUserDisplay(data.user_email);
        }
        
        // Render genre filter badges
        renderGenreBadges();
        
        displayRecommendations();
    } catch (error) {
        console.error('Load recommendations error:', error);
        showError('Failed to load recommendations.');
    }
}

/**
 * Display recommendations in the UI based on settings and pagination
 */
function displayRecommendations() {
    hideAllSections();
    elements.contentSection().classList.remove('hidden');
    
    const settings = Settings.get();
    
    // Choose which list to display based on settings
    const baseRecommendations = settings.useReranked 
        ? AppState.rerankedRecommendations 
        : AppState.rawRecommendations;
    
    // Apply genre filtering
    let filteredRecommendations = filterByGenres(baseRecommendations);
    
    // Apply blocked items filter if enabled
    if (settings.enableBlockItems) {
        const blockedItems = Settings.getBlockedItems();
        const blockedIds = new Set(blockedItems.map(b => b.id));
        filteredRecommendations = filteredRecommendations.filter(item => !blockedIds.has(item.id));
    }
    
    const allRecommendations = filteredRecommendations;
    
    // Calculate pagination
    AppState.totalPages = Math.max(1, Math.ceil(allRecommendations.length / AppState.itemsPerPage));
    
    // Ensure current page is valid
    if (AppState.currentPage > AppState.totalPages) {
        AppState.currentPage = AppState.totalPages;
    }
    if (AppState.currentPage < 1) {
        AppState.currentPage = 1;
    }
    
    // Get items for current page
    const startIndex = (AppState.currentPage - 1) * AppState.itemsPerPage;
    const endIndex = startIndex + AppState.itemsPerPage;
    const pageRecommendations = allRecommendations.slice(startIndex, endIndex);
    
    // Update list type badge
    const listTypeText = elements.listTypeText();
    if (listTypeText) {
        listTypeText.textContent = settings.useReranked 
            ? 'Diversity-Enhanced' 
            : 'Standard Recommendations';
    }
    
    // Reset refresh button state
    const refreshBtn = elements.refreshBtn();
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i><span>Refresh</span>';
    }
    
    // Render recommendations for current page
    renderRecommendationList(
        elements.recommendationsContainer(),
        pageRecommendations,
        settings
    );
    
    // Update pagination controls
    updatePaginationUI();
    
    // Re-initialize icons
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Update pagination UI elements
 */
function updatePaginationUI() {
    const currentPageEl = elements.currentPageEl();
    const totalPagesEl = elements.totalPagesEl();
    const prevBtn = elements.prevPageBtn();
    const nextBtn = elements.nextPageBtn();
    const paginationControls = elements.paginationControls();
    
    if (currentPageEl) currentPageEl.textContent = AppState.currentPage;
    if (totalPagesEl) totalPagesEl.textContent = AppState.totalPages;
    
    // Update button states
    if (prevBtn) {
        prevBtn.disabled = AppState.currentPage <= 1;
    }
    if (nextBtn) {
        nextBtn.disabled = AppState.currentPage >= AppState.totalPages;
    }
    
    // Hide pagination if only one page
    if (paginationControls) {
        paginationControls.classList.toggle('hidden', AppState.totalPages <= 1);
    }
    
    // Re-initialize icons in pagination
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Go to previous page
 */
function goToPrevPage() {
    if (AppState.currentPage > 1) {
        AppState.currentPage--;
        displayRecommendations();
    }
}

/**
 * Go to next page
 */
function goToNextPage() {
    if (AppState.currentPage < AppState.totalPages) {
        AppState.currentPage++;
        displayRecommendations();
    }
}

// ==============================================================================
// Genre Filtering Functions
// ==============================================================================

/**
 * Load genre filters from localStorage
 */
function loadGenreFilters() {
    try {
        const stored = localStorage.getItem(GENRE_FILTERS_KEY);
        AppState.genreFilters = stored ? JSON.parse(stored) : {};
    } catch (error) {
        console.error('Error loading genre filters:', error);
        AppState.genreFilters = {};
    }
}

/**
 * Save genre filters to localStorage
 */
function saveGenreFilters() {
    try {
        localStorage.setItem(GENRE_FILTERS_KEY, JSON.stringify(AppState.genreFilters));
    } catch (error) {
        console.error('Error saving genre filters:', error);
    }
}

/**
 * Extract all unique genres from recommendations
 */
function extractAllGenres(recommendations) {
    const genreSet = new Set();
    recommendations.forEach(item => {
        if (item.genres) {
            item.genres.split(',').forEach(g => {
                const genre = g.trim();
                if (genre) genreSet.add(genre);
            });
        }
    });
    return Array.from(genreSet).sort();
}

/**
 * Cycle genre filter state: null -> required -> blocked -> null
 */
function cycleGenreFilter(genre) {
    const current = AppState.genreFilters[genre];
    if (!current) {
        AppState.genreFilters[genre] = 'required';
    } else if (current === 'required') {
        AppState.genreFilters[genre] = 'blocked';
    } else {
        delete AppState.genreFilters[genre];
    }
    saveGenreFilters();
    AppState.currentPage = 1; // Reset to first page when filter changes
    renderGenreBadges();
    displayRecommendations();
}

/**
 * Clear all genre filters
 */
function clearGenreFilters() {
    AppState.genreFilters = {};
    saveGenreFilters();
    AppState.currentPage = 1;
    renderGenreBadges();
    displayRecommendations();
}

/**
 * Filter recommendations based on genre preferences
 */
function filterByGenres(recommendations) {
    const requiredGenres = Object.entries(AppState.genreFilters)
        .filter(([_, status]) => status === 'required')
        .map(([genre, _]) => genre);
    
    const blockedGenres = Object.entries(AppState.genreFilters)
        .filter(([_, status]) => status === 'blocked')
        .map(([genre, _]) => genre);
    
    if (requiredGenres.length === 0 && blockedGenres.length === 0) {
        return recommendations;
    }
    
    return recommendations.filter(item => {
        if (!item.genres) return requiredGenres.length === 0;
        
        const itemGenres = item.genres.split(',').map(g => g.trim());
        
        // Filter out if ANY blocked genre is present
        if (blockedGenres.some(blocked => itemGenres.includes(blocked))) {
            return false;
        }
        
        // If required genres exist, must have at least one
        if (requiredGenres.length > 0) {
            return requiredGenres.some(required => itemGenres.includes(required));
        }
        
        return true;
    });
}

/**
 * Render genre filter badges
 */
function renderGenreBadges() {
    const container = document.getElementById('genre-badges');
    const clearBtn = document.getElementById('clear-genre-filters');
    
    if (!container) return;
    
    // Show/hide clear button based on active filters
    const hasFilters = Object.keys(AppState.genreFilters).length > 0;
    if (clearBtn) {
        clearBtn.classList.toggle('hidden', !hasFilters);
    }
    
    container.innerHTML = AppState.allGenres.map(genre => {
        const status = AppState.genreFilters[genre];
        let classes = 'px-3 py-1.5 rounded-full text-sm cursor-pointer transition-all duration-200 select-none ';
        let icon = '';
        
        if (status === 'required') {
            classes += 'bg-green-600/30 text-green-400 border border-green-500 hover:bg-green-600/40';
            icon = '<i data-lucide="check" class="w-3 h-3 inline mr-1"></i>';
        } else if (status === 'blocked') {
            classes += 'bg-red-600/30 text-red-400 border border-red-500 hover:bg-red-600/40';
            icon = '<i data-lucide="x" class="w-3 h-3 inline mr-1"></i>';
        } else {
            classes += 'bg-netflix-gray text-gray-400 border border-transparent hover:bg-gray-600 hover:text-gray-300';
        }
        
        return `<span class="${classes}" data-genre="${genre}" onclick="cycleGenreFilter('${genre.replace(/'/g, "\\'")}')">${icon}${genre}</span>`;
    }).join('');
    
    // Re-initialize icons
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Render a list of recommendations
 */
function renderRecommendationList(container, recommendations, settings) {
    container.innerHTML = '';
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-10">
                <i data-lucide="inbox" class="w-16 h-16 text-gray-600 mx-auto mb-4"></i>
                <p class="text-gray-400">No recommendations available</p>
            </div>
        `;
        return;
    }
    
    recommendations.forEach((item, index) => {
        const card = createRecommendationCard(item, settings, index);
        container.appendChild(card);
    });
}

/**
 * Create a recommendation card element
 */
function createRecommendationCard(item, settings, index) {
    const card = document.createElement('div');
    const wasClicked = wasItemClicked(item.id);
    const clickedClass = wasClicked ? 'ring-2 ring-green-500 ring-offset-2 ring-offset-netflix-black' : '';
    
    // Check if any modal feature is enabled (determines if we show View Details button)
    const hasModalFeatures = settings.showMoreDetails || settings.showWhyRecommended || settings.enableWatchlist;
    
    // Card is clickable (with pointer cursor) only when no modal features are enabled
    const cursorClass = hasModalFeatures ? '' : 'cursor-pointer';
    
    card.className = `recommendation-card group relative bg-netflix-gray rounded-xl overflow-hidden shadow-lg transition-all duration-300 ${clickedClass} ${cursorClass}`;
    card.dataset.id = item.id;
    card.dataset.clicked = wasClicked ? 'true' : 'false';
    
    // Build card HTML - either show image or image-off icon
    const imageContent = item.img 
        ? `<img 
                src="${item.img}" 
                alt="${item.name || ''}" 
                class="w-full h-full object-cover"
                loading="lazy"
            />`
        : `<div class="w-full h-full bg-netflix-gray flex items-center justify-center">
                <i data-lucide="image-off" class="w-12 h-12 text-gray-600"></i>
            </div>`;
    
    let cardHTML = `
        <div class="relative aspect-[2/3]">
            ${imageContent}
            <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
            
            <!-- Action buttons overlay (visible on hover) -->
            <div class="absolute inset-0 flex flex-col items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/60">
    `;
    
    // Show View Details button only if modal features are enabled
    if (hasModalFeatures) {
        cardHTML += `
                <button class="view-details-btn px-4 py-2 bg-white text-black rounded-lg font-medium flex items-center gap-2 hover:bg-gray-200 transition-colors text-sm">
                    <i data-lucide="info" class="w-4 h-4"></i>
                    View Details
                </button>
        `;
    }
    
    // Show Don't Recommend button if enabled
    if (settings.enableBlockItems) {
        cardHTML += `
                <button class="dont-recommend-btn px-4 py-2 bg-red-600/80 hover:bg-red-600 text-white rounded-lg font-medium flex items-center gap-2 transition-colors text-sm">
                    <i data-lucide="eye-off" class="w-4 h-4"></i>
                    Don't Recommend
                </button>
        `;
    }
    
    cardHTML += `
            </div>
            
            <div class="absolute bottom-0 left-0 right-0 p-4">
                <h3 class="text-white font-bold text-lg line-clamp-2 mb-1">${item.name || 'Unknown'}</h3>
    `;
    
    // Add extra details if enabled
    if (settings.showMoreDetails) {
        const detailParts = [];
        
        // Star rating
        if (item.imdb && item.imdb !== 'N/A') {
            const rating = parseFloat(item.imdb);
            if (!isNaN(rating)) {
                detailParts.push(`<span class="flex items-center gap-1"><i data-lucide="star" class="w-4 h-4 text-yellow-500 fill-yellow-500"></i>${rating.toFixed(1)}</span>`);
            }
        }
        
        // Year
        if (item.release_year) {
            detailParts.push(`<span>${item.release_year}</span>`);
        }
        
        // First genre
        if (item.genres) {
            const firstGenre = item.genres.split(',')[0].trim();
            if (firstGenre) {
                detailParts.push(`<span>${firstGenre}</span>`);
            }
        }
        
        if (detailParts.length > 0) {
            cardHTML += `
                <div class="flex items-center gap-2 mt-1 text-sm text-gray-300">
                    ${detailParts.join('<span class="text-gray-500">•</span>')}
                </div>
            `;
        }
    }
    
    cardHTML += `
            </div>
        </div>
    `;
    
    card.innerHTML = cardHTML;
    
    // If modal features are enabled, View Details button opens modal
    if (hasModalFeatures) {
        const viewDetailsBtn = card.querySelector('.view-details-btn');
        if (viewDetailsBtn) {
            viewDetailsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleViewDetailsClick(item);
            });
        }
    } else {
        // If no modal features, entire card is clickable (just records click, no modal)
        card.addEventListener('click', () => {
            handleSimpleCardClick(item);
        });
    }
    
    // Add click handler for Don't Recommend button - does NOT record click
    const dontRecommendBtn = card.querySelector('.dont-recommend-btn');
    if (dontRecommendBtn) {
        dontRecommendBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleDontRecommendClick(item);
        });
    }
    
    return card;
}

/**
 * Handle View Details button click - records the click and opens modal
 */
function handleViewDetailsClick(item) {
    // Record the click
    submitChoiceForItem(item);
    
    // Save to local click history for highlighting and history page
    saveToClickHistory(item);
    
    // Open modal
    Modal.open(item);
    
    // Re-initialize icons in modal
    if (window.lucide) {
        setTimeout(() => lucide.createIcons(), 50);
    }
}

/**
 * Handle simple card click (when no modal features enabled) - just records click
 */
function handleSimpleCardClick(item) {
    // Record the click
    submitChoiceForItem(item);
    
    // Save to local click history for highlighting and history page
    saveToClickHistory(item);
    
    // Show brief confirmation
    showToast('Choice recorded!', 'success');
}

/**
 * Handle Don't Recommend button click - does NOT record a click
 */
function handleDontRecommendClick(item) {
    // Block the item without recording as a click
    Settings.blockItem(item);
    showToast(`"${item.name}" will be hidden from recommendations.`, 'success');
}

/**
 * Submit choice for an item (to server)
 */
async function submitChoiceForItem(item) {
    try {
        const settings = Settings.get();
        const column = settings.useReranked ? 2 : 1;
        const page = AppState.currentPage;
        const rank = (typeof item.rank === 'number' && !Number.isNaN(item.rank)) ? item.rank : null;
        
        // Get currently visible items on screen
        const visibleItems = getCurrentPageItems().map(i => i.name);
        
        await NetflixAPI.submitChoice(item.id, column, rank, page, visibleItems);
    } catch (error) {
        console.error('Submit choice error:', error);
    }
}

/**
 * Get the items currently displayed on the current page
 */
function getCurrentPageItems() {
    const settings = Settings.get();
    
    // Get the base recommendations
    const baseRecommendations = settings.useReranked 
        ? AppState.rerankedRecommendations 
        : AppState.rawRecommendations;
    
    // Apply genre filtering
    let filteredRecommendations = filterByGenres(baseRecommendations);
    
    // Apply blocked items filter if enabled
    if (settings.enableBlockItems) {
        const blockedItems = Settings.getBlockedItems();
        const blockedIds = new Set(blockedItems.map(b => b.id));
        filteredRecommendations = filteredRecommendations.filter(item => !blockedIds.has(item.id));
    }
    
    // Get items for current page
    const startIndex = (AppState.currentPage - 1) * AppState.itemsPerPage;
    const endIndex = startIndex + AppState.itemsPerPage;
    
    return filteredRecommendations.slice(startIndex, endIndex);
}

/**
 * Save item to local click history (localStorage)
 */
function saveToClickHistory(item) {
    try {
        const history = getClickHistory();
        const existingIndex = history.findIndex(h => h.id === item.id);
        
        const historyEntry = {
            id: item.id,
            name: item.name,
            img: item.img,
            genres: item.genres,
            type: item.type,
            clickedAt: new Date().toISOString(),
            clickCount: 1
        };
        
        if (existingIndex >= 0) {
            // Update existing entry with new timestamp and increment count
            historyEntry.clickCount = (history[existingIndex].clickCount || 1) + 1;
            history.splice(existingIndex, 1);
        }
        
        // Add to beginning (most recent first)
        history.unshift(historyEntry);
        
        // Keep only last 100 entries
        const trimmedHistory = history.slice(0, 100);
        
        localStorage.setItem('netflix_click_history', JSON.stringify(trimmedHistory));
        
        // Dispatch event for UI updates (like adding green border)
        window.dispatchEvent(new CustomEvent('clickHistoryUpdated', { detail: historyEntry }));
    } catch (error) {
        console.error('Error saving to click history:', error);
    }
}

/**
 * Get click history from localStorage
 */
function getClickHistory() {
    try {
        const stored = localStorage.getItem('netflix_click_history');
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Error loading click history:', error);
        return [];
    }
}

/**
 * Check if an item was previously clicked
 */
function wasItemClicked(itemId) {
    const history = getClickHistory();
    return history.some(h => h.id === itemId);
}

/**
 * Get stored global_V mtime from localStorage
 */
function getStoredGlobalVMtime() {
    return localStorage.getItem(GLOBAL_V_MTIME_KEY);
}

/**
 * Update stored global_V mtime in localStorage
 * @param {string} mtime - ISO timestamp of global_V last modified time
 */
function updateStoredGlobalVMtime(mtime) {
    if (mtime) {
        localStorage.setItem(GLOBAL_V_MTIME_KEY, mtime);
        console.log('Updated stored global_V mtime:', mtime);
    }
}

/**
 * Check if global_V has been updated by the aggregator
 * Returns true if we should trigger a refresh, false otherwise
 * IMPORTANT: Updates the stored mtime BEFORE returning to prevent duplicate triggers
 */
async function checkGlobalVChanged() {
    try {
        const globalVInfo = await NetflixAPI.getGlobalVInfo();
        
        if (!globalVInfo.exists) {
            console.log('Global model does not exist yet');
            return false;
        }
        
        const currentMtime = globalVInfo.last_modified;
        const storedMtime = getStoredGlobalVMtime();
        
        console.log('Global V check:', { current: currentMtime, stored: storedMtime });
        
        // If no stored mtime, this is first time - store it and don't trigger refresh
        if (!storedMtime) {
            console.log('First time seeing global_V, storing mtime');
            updateStoredGlobalVMtime(currentMtime);
            return false;
        }
        
        // Compare mtimes
        if (currentMtime !== storedMtime) {
            console.log('Global model has been updated!');
            // Update stored mtime FIRST to prevent duplicate triggers
            updateStoredGlobalVMtime(currentMtime);
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error checking global_V:', error);
        return false;
    }
}

/**
 * Start polling for computation status
 */
function startPolling() {
    stopPolling();
    
    AppState.pollingInterval = setInterval(async () => {
        try {
            const status = await NetflixAPI.getStatus();
            
            if (status.status === 'ready' && status.has_recommendations) {
                stopPolling();
                await loadAndDisplayRecommendations();
            } else if (status.status === 'error') {
                stopPolling();
                const errorType = status.error_type;
                showError(status.message || 'Computation failed.', errorType);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 3000);
}

/**
 * Start polling for FL workflow status
 */
function startFLPolling() {
    stopPolling();
    
    AppState.pollingInterval = setInterval(async () => {
        try {
            const flStatus = await NetflixAPI.getFLStatus();
            console.log('FL Status:', flStatus);
            
            // Update loading message based on FL status
            if (flStatus.status === 'fine_tuning') {
                elements.statusMessage().textContent = 'Fine-tuning your personalized model...';
            } else if (flStatus.status === 'running') {
                elements.statusMessage().textContent = 'Preparing your data...';
            }
            
            if (flStatus.status === 'ready') {
                // FL training done - now wait for recommendations to compute
                elements.statusMessage().textContent = 'Computing recommendations...';
                // Switch to regular polling for recommendation status
                stopPolling();
                startPolling();
            } else if (flStatus.status === 'no_viewing_history') {
                // No viewing history - redirect to upload section
                stopPolling();
                resetRefreshButton();
                showUploadSection();
                showToast('Please upload your Netflix viewing history first.', 'error');
            } else if (flStatus.status === 'aggregator_wait') {
                stopPolling();
                resetRefreshButton();
                showError(flStatus.message || 'Waiting for aggregator to publish model files.', flStatus.error_type);
            } else if (flStatus.status === 'error') {
                stopPolling();
                resetRefreshButton();
                
                const errorType = flStatus.error_type;
                const errorMessage = flStatus.message;
                
                // Handle no-title-match errors first (includes empty CSV)
                if (errorType === 'no_title_matches') {
                    showUploadSection();
                    showToast(
                        'No titles found in your CSV. Please try to re-download from Netflix and try again.',
                        'error'
                    );
                } else if (errorMessage && errorMessage.toLowerCase().includes('viewing history')) {
                    showUploadSection();
                    showToast('Please upload your Netflix viewing history.', 'error');
                } else {
                    // Show error with user-friendly message based on error type
                    showError(errorMessage || 'Training failed. Please try again.', errorType);
                }
            }
            
            if (window.lucide) {
                lucide.createIcons();
            }
        } catch (error) {
            console.error('FL Polling error:', error);
        }
    }, 3000);
}

/**
 * Stop polling
 */
function stopPolling() {
    if (AppState.pollingInterval) {
        clearInterval(AppState.pollingInterval);
        AppState.pollingInterval = null;
    }
}

/**
 * Reset refresh button to default state
 */
function resetRefreshButton() {
    const refreshBtn = elements.refreshBtn();
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i><span>Refresh</span>';
    }
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * UI Helper Functions
 */
function hideAllSections() {
    elements.loadingSection()?.classList.add('hidden');
    elements.errorSection()?.classList.add('hidden');
    elements.contentSection()?.classList.add('hidden');
    elements.computeSection()?.classList.add('hidden');
    elements.uploadSection()?.classList.add('hidden');
}

function showLoading(message) {
    hideAllSections();
    elements.loadingSection().classList.remove('hidden');
    elements.statusMessage().textContent = message;
}

/**
 * Get user-friendly error message based on error type
 * @param {string} errorType - Error type from backend
 * @param {string} originalMessage - Original error message
 * @returns {string} User-friendly error message
 */
function getFriendlyErrorMessage(errorType, originalMessage) {
    const errorMessages = {
        'syftbox_not_running': 'Could not connect to SyftBox. Please ensure SyftBox is running on your machine and try again.',
        'aggregator_not_initialized': 'The aggregator hasn\'t published model files yet. Please wait for the aggregator to initialize and try again.',
        'aggregator_not_ready': 'The aggregator hasn\'t processed any data yet. Please wait for the aggregator to run and try again.',
        'no_title_matches': 'No titles found in your CSV. Please try to re-download from Netflix and try again.',
        'vocabulary_error': 'Could not load the recommendation model vocabulary. Please try again later.',
    };
    
    return errorMessages[errorType] || originalMessage || 'An unexpected error occurred. Please try again.';
}

function showError(message, errorType = null) {
    hideAllSections();
    elements.errorSection().classList.remove('hidden');
    
    // Get user-friendly message if error type is provided
    const displayMessage = errorType ? getFriendlyErrorMessage(errorType, message) : message;
    elements.errorMessage().textContent = displayMessage;
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

function showUploadSection() {
    hideAllSections();
    elements.uploadSection().classList.remove('hidden');
    if (window.lucide) {
        lucide.createIcons();
    }
}

function showComputeSection() {
    hideAllSections();
    elements.computeSection().classList.remove('hidden');
    const btn = elements.computeBtn();
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="zap" class="w-5 h-5"></i> Compute Recommendations';
    if (window.lucide) {
        lucide.createIcons();
    }
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 z-50 max-w-sm w-auto whitespace-normal ${
        type === 'success' ? 'bg-green-600' : 'bg-red-600'
    } text-white flex items-center gap-2`;
    
    const icon = type === 'success' ? 'check-circle' : 'alert-circle';
    toast.innerHTML = `<i data-lucide="${icon}" class="w-5 h-5"></i> ${message}`;
    
    document.body.appendChild(toast);
    
    if (window.lucide) {
        lucide.createIcons();
    }
    
    setTimeout(() => toast.classList.add('opacity-100'), 10);
    
    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * File Upload Handlers
 */
function setupUploadHandlers() {
    const dropZone = elements.dropZone();
    const fileInput = elements.fileInput();
    
    if (!dropZone || !fileInput) return;
    
    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());
    
    // File selected via input
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });
    
    // Drag and drop events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-netflix-red', 'bg-netflix-red/10');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-netflix-red', 'bg-netflix-red/10');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-netflix-red', 'bg-netflix-red/10');
        
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });
}

async function handleFileUpload(file) {
    const uploadStatus = elements.uploadStatus();
    
    // Validate file type
    if (!file.name.endsWith('.csv')) {
        uploadStatus.textContent = 'Please upload a CSV file';
        uploadStatus.className = 'text-sm text-red-400';
        return;
    }
    
    uploadStatus.textContent = 'Uploading...';
    uploadStatus.className = 'text-sm text-gray-400';
    
    try {
        const result = await NetflixAPI.uploadHistory(file);
        
        uploadStatus.textContent = result.message;
        uploadStatus.className = 'text-sm text-green-400';
        
        showToast('File uploaded successfully!', 'success');
        
        // Immediately start training after successful upload
        showLoading('Fine-tuning your personalized model...');
        try {
            await NetflixAPI.triggerRefresh();
            startFLPolling();
        } catch (error) {
            console.error('Error starting FL workflow:', error);
            showError('Failed to start training. Please try again.');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        uploadStatus.textContent = error.message || 'Upload failed';
        uploadStatus.className = 'text-sm text-red-400';
    }
}

/**
 * Trigger refresh (recompute recommendations using existing model - no fine-tuning)
 */
async function triggerRefresh() {
    const btn = elements.refreshBtn();
    if (!btn) return;
    
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Refreshing...';
    
    try {
        // Just recompute recommendations using existing model (no fine-tuning)
        const result = await NetflixAPI.recomputeRecommendations();
        
        if (result.status === 'already_computing') {
            showToast('Computation is already in progress.', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i> Refresh';
            return;
        }
        
        showLoading('Recomputing recommendations...');
        startPolling();
    } catch (error) {
        console.error('Refresh error:', error);
        showToast('Failed to refresh. Please try again.', 'error');
        
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="refresh-cw" class="w-4 h-4"></i> Refresh';
    }
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    
    // Setup upload handlers
    setupUploadHandlers();
    
    // Compute button (still kept for backwards compatibility)
    elements.computeBtn()?.addEventListener('click', triggerRefresh);
    
    // Retry button
    elements.retryBtn()?.addEventListener('click', () => {
        initApp();
    });
    
    // Refresh button (single consolidated button)
    elements.refreshBtn()?.addEventListener('click', triggerRefresh);
    
    // Pagination buttons
    elements.prevPageBtn()?.addEventListener('click', goToPrevPage);
    elements.nextPageBtn()?.addEventListener('click', goToNextPage);
    
    // Clear genre filters button
    document.getElementById('clear-genre-filters')?.addEventListener('click', clearGenreFilters);
    
    // Privacy modal buttons
    document.getElementById('privacy-accept-btn')?.addEventListener('click', acceptPrivacy);
    document.getElementById('privacy-decline-btn')?.addEventListener('click', declinePrivacy);
    
    // Listen for click history updates to immediately highlight cards
    window.addEventListener('clickHistoryUpdated', (e) => {
        const itemId = e.detail?.id;
        if (itemId) {
            const card = document.querySelector(`.recommendation-card[data-id="${itemId}"]`);
            if (card && card.dataset.clicked !== 'true') {
                card.classList.add('ring-2', 'ring-green-500', 'ring-offset-2', 'ring-offset-netflix-black');
                card.dataset.clicked = 'true';
            }
        }
    });
    
    // Listen for blocked items changes to re-render
    window.addEventListener('blockedItemsChanged', () => {
        if (AppState.status === 'ready') {
            displayRecommendations();
        }
    });
});

// Export click history functions for use in other modules
window.ClickHistory = {
    get: getClickHistory,
    save: saveToClickHistory,
    wasClicked: wasItemClicked
};

// Export global_V mtime functions for use in other modules (e.g., history.html)
window.GlobalVTracker = {
    getMtime: getStoredGlobalVMtime,
    updateMtime: updateStoredGlobalVMtime,
    checkChanged: checkGlobalVChanged
};

// Export AppState and getCurrentPageItems for use by modal.js
window.AppState = AppState;
window.getCurrentPageItems = getCurrentPageItems;
