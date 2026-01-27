/**
 * Settings Management Module
 * Handles user preferences stored in localStorage
 */

const SETTINGS_KEY = 'netflix_recommendations_settings';

// Default settings
const DEFAULT_SETTINGS = {
    showMoreDetails: true,       // Show rating, year, genre under cards
    useReranked: false,          // Use re-ranked recommendations instead of raw
    showWhyRecommended: true,    // Show "why recommended" in modal
    enableWatchlist: true,       // Enable will/won't watch buttons
    enableBlockItems: true,      // Enable "don't recommend again" feature
    showActivityCharts: true,    // Show charts on profile page
    showWatchlistStatus: true    // Show will/won't watch badges on history items
};

// Blocked items storage key
const BLOCKED_ITEMS_KEY = 'netflix_blocked_items';

/**
 * Load settings from localStorage
 * @returns {Object} Current settings with defaults applied
 */
function loadSettings() {
    try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            // Merge with defaults to ensure all keys exist
            return { ...DEFAULT_SETTINGS, ...parsed };
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
    return { ...DEFAULT_SETTINGS };
}

/**
 * Save settings to localStorage
 * @param {Object} settings - Settings object to save
 */
function saveSettings(settings) {
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
        // Dispatch custom event for other modules to react
        window.dispatchEvent(new CustomEvent('settingsChanged', { detail: settings }));
    } catch (e) {
        console.error('Error saving settings:', e);
    }
}

/**
 * Get current settings
 * @returns {Object} Current settings
 */
function getSettings() {
    return loadSettings();
}

/**
 * Log settings to server for aggregator analytics
 * Called when user toggles any setting (not on page load)
 * @param {Object} settings - Current settings state
 */
async function logSettingsToServer(settings) {
    try {
        const response = await fetch('/api/settings/log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            console.warn('Failed to log settings to server:', response.statusText);
        } else {
            console.log('Settings logged to server');
        }
    } catch (error) {
        // Silently fail - settings logging is not critical
        console.warn('Error logging settings to server:', error);
    }
}

/**
 * Update a single setting
 * @param {string} key - Setting key
 * @param {any} value - Setting value
 */
function updateSetting(key, value) {
    const settings = loadSettings();
    settings[key] = value;
    saveSettings(settings);
    
    // Log the updated settings to the server for aggregator analytics
    // This is only called on actual toggle, not on page load
    logSettingsToServer(settings);
    
    return settings;
}

/**
 * Check if any feature that requires the modal is enabled
 * @returns {boolean}
 */
function isModalFeatureEnabled() {
    const settings = loadSettings();
    return settings.showMoreDetails || settings.showWhyRecommended || settings.enableWatchlist || settings.enableBlockItems;
}

/**
 * Reset settings to defaults
 */
function resetSettings() {
    saveSettings({ ...DEFAULT_SETTINGS });
    return DEFAULT_SETTINGS;
}

/**
 * Get blocked items from localStorage
 */
function getBlockedItems() {
    try {
        const stored = localStorage.getItem(BLOCKED_ITEMS_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.error('Error loading blocked items:', e);
        return [];
    }
}

/**
 * Save blocked items to localStorage
 */
function saveBlockedItems(items) {
    try {
        localStorage.setItem(BLOCKED_ITEMS_KEY, JSON.stringify(items));
    } catch (e) {
        console.error('Error saving blocked items:', e);
    }
}

/**
 * Add item to blocked list
 */
function blockItem(item) {
    const blocked = getBlockedItems();
    if (!blocked.find(b => b.id === item.id)) {
        blocked.push({
            id: item.id,
            name: item.name,
            blockedAt: new Date().toISOString()
        });
        saveBlockedItems(blocked);
        updateBlockedItemsUI();
        window.dispatchEvent(new CustomEvent('blockedItemsChanged'));
    }
}

/**
 * Remove item from blocked list
 */
function unblockItem(itemId) {
    const blocked = getBlockedItems();
    const filtered = blocked.filter(b => b.id !== itemId);
    saveBlockedItems(filtered);
    updateBlockedItemsUI();
    window.dispatchEvent(new CustomEvent('blockedItemsChanged'));
}

/**
 * Clear all blocked items
 */
function clearBlockedItems() {
    if (confirm('Are you sure you want to unhide all items?')) {
        saveBlockedItems([]);
        updateBlockedItemsUI();
        window.dispatchEvent(new CustomEvent('blockedItemsChanged'));
    }
}

/**
 * Check if item is blocked
 */
function isItemBlocked(itemId) {
    return getBlockedItems().some(b => b.id === itemId);
}

/**
 * Update blocked items UI in settings panel
 */
function updateBlockedItemsUI() {
    const settings = loadSettings();
    const section = document.getElementById('blocked-items-section');
    const list = document.getElementById('blocked-items-list');
    const clearBtn = document.getElementById('clear-blocked-items');
    
    if (!section || !list) return;
    
    // Show/hide section based on setting
    if (settings.enableBlockItems) {
        section.classList.remove('hidden');
    } else {
        section.classList.add('hidden');
        return;
    }
    
    const blocked = getBlockedItems();
    
    if (blocked.length === 0) {
        list.innerHTML = '<p class="text-gray-500 text-sm">No items hidden yet</p>';
        if (clearBtn) clearBtn.classList.add('hidden');
    } else {
        list.innerHTML = blocked.map(item => `
            <div class="flex items-center justify-between p-2 bg-netflix-black rounded text-sm">
                <span class="text-gray-300 truncate flex-1">${item.name}</span>
                <button onclick="Settings.unblockItem(${item.id})" class="ml-2 text-gray-500 hover:text-white transition-colors" title="Unhide">
                    <i data-lucide="eye" class="w-4 h-4"></i>
                </button>
            </div>
        `).join('');
        if (clearBtn) clearBtn.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
    }
}

/**
 * Initialize settings panel UI
 */
function initSettingsPanel() {
    const settings = loadSettings();
    
    // Update all toggle states
    const toggles = {
        'toggle-more-details': 'showMoreDetails',
        'toggle-reranked': 'useReranked',
        'toggle-why-recommended': 'showWhyRecommended',
        'toggle-watchlist': 'enableWatchlist',
        'toggle-block-items': 'enableBlockItems',
        'toggle-activity-charts': 'showActivityCharts',
        'toggle-watchlist-status': 'showWatchlistStatus'
    };
    
    Object.entries(toggles).forEach(([elementId, settingKey]) => {
        const toggle = document.getElementById(elementId);
        if (toggle) {
            toggle.checked = settings[settingKey];
        }
    });
    
    // Update blocked items UI
    updateBlockedItemsUI();
}

/**
 * Setup event listeners for settings panel
 */
function setupSettingsListeners() {
    const toggles = {
        'toggle-more-details': 'showMoreDetails',
        'toggle-reranked': 'useReranked',
        'toggle-why-recommended': 'showWhyRecommended',
        'toggle-watchlist': 'enableWatchlist',
        'toggle-block-items': 'enableBlockItems',
        'toggle-activity-charts': 'showActivityCharts',
        'toggle-watchlist-status': 'showWatchlistStatus'
    };
    
    Object.entries(toggles).forEach(([elementId, settingKey]) => {
        const toggle = document.getElementById(elementId);
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                updateSetting(settingKey, e.target.checked);
                console.log(`Setting '${settingKey}' changed to:`, e.target.checked);
                
                // Special handling for block items toggle
                if (settingKey === 'enableBlockItems') {
                    updateBlockedItemsUI();
                }
            });
        }
    });
    
    // Clear blocked items button
    const clearBlockedBtn = document.getElementById('clear-blocked-items');
    if (clearBlockedBtn) {
        clearBlockedBtn.addEventListener('click', clearBlockedItems);
    }
    
    // Settings panel open/close
    const settingsBtn = document.getElementById('settings-btn');
    const settingsPanel = document.getElementById('settings-panel');
    const settingsOverlay = document.getElementById('settings-overlay');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    
    if (settingsBtn && settingsPanel) {
        settingsBtn.addEventListener('click', () => {
            settingsPanel.classList.remove('translate-x-full');
            settingsOverlay?.classList.remove('hidden');
        });
    }
    
    const closeSettings = () => {
        settingsPanel?.classList.add('translate-x-full');
        settingsOverlay?.classList.add('hidden');
    };
    
    closeSettingsBtn?.addEventListener('click', closeSettings);
    settingsOverlay?.addEventListener('click', closeSettings);
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !settingsPanel?.classList.contains('translate-x-full')) {
            closeSettings();
        }
    });
}

/**
 * Update user email display in settings panel
 * @param {string} email - User email to display
 */
function updateUserDisplay(email) {
    const userEmailEl = document.getElementById('user-email');
    if (userEmailEl) {
        userEmailEl.textContent = email || 'Unknown';
    }
}

// Export for use in other modules
window.Settings = {
    load: loadSettings,
    save: saveSettings,
    get: getSettings,
    update: updateSetting,
    reset: resetSettings,
    isModalFeatureEnabled,
    init: initSettingsPanel,
    setupListeners: setupSettingsListeners,
    updateUserDisplay,
    DEFAULT: DEFAULT_SETTINGS,
    // Blocked items functions
    getBlockedItems,
    blockItem,
    unblockItem,
    isItemBlocked,
    clearBlockedItems,
    updateBlockedItemsUI
};
