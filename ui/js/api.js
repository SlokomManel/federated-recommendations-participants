/**
 * API Communication Layer for Netflix Recommendations
 */

const API_BASE_URL = '';

/**
 * Check the status of recommendations
 * @returns {Promise<Object>} Status object with status, has_recommendations, message
 */
async function getStatus() {
    const response = await fetch(`${API_BASE_URL}/api/status`);
    if (!response.ok) {
        throw new Error(`Status check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch recommendations if available
 * @returns {Promise<Object>} Recommendations object with raw and reranked lists
 */
async function getRecommendations() {
    const response = await fetch(`${API_BASE_URL}/api/recommendations`);
    if (!response.ok) {
        if (response.status === 404) {
            return { error: 'No recommendations available', status: 'pending' };
        }
        throw new Error(`Failed to fetch recommendations: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Check if viewing history data exists
 * @returns {Promise<Object>} Data status object with has_data, source, path
 */
async function getDataStatus() {
    const response = await fetch(`${API_BASE_URL}/api/data/status`);
    if (!response.ok) {
        throw new Error(`Data status check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Upload Netflix viewing history CSV file
 * @param {File} file - CSV file to upload
 * @returns {Promise<Object>} Upload result
 */
async function uploadHistory(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/api/data/upload`, {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || 'Upload failed');
    }
    return result;
}

/**
 * Submit user's choice/feedback
 * @param {number} id - The ID of the chosen item
 * @param {number} column - Which column (1 = raw, 2 = reranked)
 * @param {number|null} rank - 1-based rank in the full list (pre-filters)
 * @param {number} page - Current page number
 * @param {Array} visibleItems - List of item names currently visible on screen
 * @returns {Promise<Object>} Server response
 */
async function submitChoice(id, column, rank = null, page = 1, visibleItems = []) {
    const response = await fetch(`${API_BASE_URL}/api/choice`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id, column, rank, page, visible_items: visibleItems })
    });
    if (!response.ok) {
        throw new Error(`Failed to submit choice: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Health check endpoint
 * @returns {Promise<Object>} Health status
 */
async function healthCheck() {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) {
        throw new Error(`Health check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Submit watchlist action (will watch / won't watch)
 * @param {number} id - The ID of the item
 * @param {string} title - The title of the item
 * @param {string} action - Either "will_watch" or "wont_watch"
 * @param {boolean} useReranked - Whether user is viewing re-ranked list
 * @param {number|null} rank - 1-based rank in the full list (pre-filters)
 * @param {number} page - Current page number
 * @param {Array} visibleItems - List of item names currently visible on screen
 * @returns {Promise<Object>} Server response
 */
async function submitWatchlistAction(id, title, action, useReranked = false, rank = null, page = 1, visibleItems = []) {
    const response = await fetch(`${API_BASE_URL}/api/watchlist`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id, title, action, useReranked, rank, page, visible_items: visibleItems })
    });
    if (!response.ok) {
        throw new Error(`Failed to submit watchlist action: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get current user information
 * @returns {Promise<Object>} User info with email
 */
async function getUser() {
    const response = await fetch(`${API_BASE_URL}/api/user`);
    if (!response.ok) {
        throw new Error(`Failed to get user info: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get federated learning status
 * @returns {Promise<Object>} FL status object
 */
async function getFLStatus() {
    const response = await fetch(`${API_BASE_URL}/api/fl/status`);
    if (!response.ok) {
        throw new Error(`FL status check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get global model (global_V.npy) information
 * Used to detect when the aggregator has updated the global model
 * @returns {Promise<Object>} Global V info with exists, last_modified, path
 */
async function getGlobalVInfo() {
    const response = await fetch(`${API_BASE_URL}/api/fl/global-v-info`);
    if (!response.ok) {
        throw new Error(`Global V info check failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Submit opt-out interaction log (reason + optional user message).
 * @param {string} reason - Selected reason label (optional)
 * @param {string} userMessage - Optional freeform user message
 * @param {string} timestamp - ISO timestamp
 * @returns {Promise<Object>} Server response
 */
async function submitOptOut(reason = '', userMessage = '', timestamp = new Date().toISOString()) {
    const response = await fetch(`${API_BASE_URL}/api/opt-out`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason, user_message: userMessage, timestamp })
    });
    if (!response.ok) {
        throw new Error(`Failed to submit opt-out: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get movie details by ID
 * @param {number} movieId - The ID of the movie to fetch details for
 * @returns {Promise<Object>} Enriched movie details
 */
async function getMovieDetails(movieId) {
    const response = await fetch(`${API_BASE_URL}/api/movie/${movieId}`);
    if (!response.ok) {
        if (response.status === 404) {
            return { error: 'Movie not found', status: 'not_found' };
        }
        throw new Error(`Failed to fetch movie details: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Recompute recommendations using existing model (no fine-tuning)
 * This just regenerates recommendations without retraining the model
 * @returns {Promise<Object>} Result of starting computation
 */
async function recomputeRecommendations() {
    const response = await fetch(`${API_BASE_URL}/api/recommendations/compute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    });
    
    if (!response.ok) {
        throw new Error(`Failed to recompute recommendations: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Trigger full refresh (FL workflow: fine-tune model + compute recommendations)
 * This uses click history to augment training data before fine-tuning
 * @param {Array} clickHistory - Array of clicked items to enhance training
 * @returns {Promise<Object>} Result of starting FL workflow
 * @throws {Error} With 'no_viewing_history' in message if viewing history not found
 */
async function triggerRefresh(clickHistory = null) {
    const body = {
        profile: 'profile_0',
        epsilon: 1.0
    };
    
    // Include click history to augment training data
    if (clickHistory && clickHistory.length > 0) {
        body.click_history = clickHistory.map(item => ({
            name: item.name,
            id: item.id,
            clicked_at: item.clickedAt
        }));
    }
    
    const response = await fetch(`${API_BASE_URL}/api/fl/run`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });
    
    // Parse the response body to get status information
    const result = await response.json();
    
    // Check for no_viewing_history error (400 status code)
    if (!response.ok) {
        if (result.status === 'no_viewing_history') {
            const error = new Error('no_viewing_history: ' + result.message);
            error.status = 'no_viewing_history';
            throw error;
        }
        throw new Error(result.message || `Failed to trigger refresh: ${response.statusText}`);
    }
    
    return result;
}

// Export for use in other modules
window.NetflixAPI = {
    getStatus,
    getRecommendations,
    getDataStatus,
    uploadHistory,
    triggerRefresh,
    recomputeRecommendations,
    getMovieDetails,
    submitChoice,
    healthCheck,
    submitWatchlistAction,
    getUser,
    getFLStatus,
    getGlobalVInfo,
    submitOptOut
};
