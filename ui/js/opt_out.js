/**
 * Opt-Out Module
 * Adds an opt-out flow (reason + optional details) and clears localStorage after goodbye.
 */
const OPT_OUT_REASON_OPTIONS = [
    'Prefer not to say',
    'Privacy concerns',
    'Not finding recommendations useful',
    'Too much effort / time',
    'Technical issues',
    'Other...'
];

function getOptOutEls() {
    return {
        btn: document.getElementById('opt-out-btn'),
        overlay: document.getElementById('opt-out-overlay'),
        modal: document.getElementById('opt-out-modal'),
        closeX: document.getElementById('opt-out-close'),
        cancel: document.getElementById('opt-out-cancel'),
        submit: document.getElementById('opt-out-submit'),
        reason: document.getElementById('opt-out-reason'),
        userMessage: document.getElementById('opt-out-user-message')
    };
}

function openOptOutModal() {
    const { overlay } = getOptOutEls();
    if (!overlay) return;
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons();
}

function closeOptOutModal() {
    const { overlay } = getOptOutEls();
    if (!overlay) return;
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
}

function resetOptOutModalContent() {
    const { modal, reason, userMessage, submit } = getOptOutEls();
    if (!modal || !reason || !userMessage || !submit) return;

    // Reset inputs
    reason.value = '';
    userMessage.value = '';

    // Reset submit button
    submit.disabled = false;
    submit.innerHTML = '<i data-lucide="log-out" class="w-4 h-4"></i> Delete local data';
    if (window.lucide) lucide.createIcons();
}

function showGoodbyeModal() {
    const { modal } = getOptOutEls();
    if (!modal) return;

    modal.innerHTML = `
        <div class="p-6 sm:p-8 text-center">
            <div class="w-14 h-14 bg-netflix-gray rounded-full flex items-center justify-center mx-auto mb-4">
                <i data-lucide="heart-handshake" class="w-7 h-7 text-gray-200"></i>
            </div>
            <h3 class="text-white font-semibold text-xl mb-2">Thank you.</h3>
            <p class="text-gray-400 text-sm leading-relaxed mb-6">
                We appreciate your time and contributions. When you continue, this app will delete the study data stored in your browser.
            </p>
            <button id="opt-out-finish" class="w-full px-4 py-2.5 bg-netflix-gray hover:bg-gray-600 text-white rounded-lg transition-colors text-sm font-medium">
                Finish
            </button>
        </div>
    `;

    const finishBtn = document.getElementById('opt-out-finish');
    finishBtn?.addEventListener('click', () => {
        try {
            localStorage.clear();
        } catch (e) {
            console.error('Failed to clear localStorage:', e);
        }
        closeOptOutModal();
        // Bring them back to the start of the app.
        window.location.href = 'index.html';
    });

    if (window.lucide) lucide.createIcons();
}

async function submitOptOut() {
    const { reason, userMessage, submit } = getOptOutEls();
    if (!submit) return;

    const selectedReasonLabel = reason?.selectedOptions?.[0]?.textContent?.trim() || '';
    const userMessageText = userMessage?.value || '';

    submit.disabled = true;
    submit.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Submitting...';
    if (window.lucide) lucide.createIcons();

    try {
        if (!window.NetflixAPI?.submitOptOut) {
            throw new Error('submitOptOut API not available');
        }

        await NetflixAPI.submitOptOut(
            selectedReasonLabel,
            userMessageText,
            new Date().toISOString()
        );

        showGoodbyeModal();
    } catch (error) {
        console.error('Opt-out error:', error);
        submit.disabled = false;
        submit.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4"></i> Error — Try Again';
        submit.classList.add('bg-red-600');
        submit.classList.remove('bg-red-900');
        if (window.lucide) lucide.createIcons();
    }
}

function initOptOut() {
    const { btn, closeX, cancel, submit, overlay, reason } = getOptOutEls();

    // Populate reasons list if empty (defensive)
    if (reason && reason.options.length <= 1) {
        OPT_OUT_REASON_OPTIONS.forEach(label => {
            const opt = document.createElement('option');
            opt.value = label;
            opt.textContent = label;
            reason.appendChild(opt);
        });
    }

    btn?.addEventListener('click', () => {
        resetOptOutModalContent();
        openOptOutModal();
    });

    closeX?.addEventListener('click', closeOptOutModal);
    cancel?.addEventListener('click', closeOptOutModal);

    overlay?.addEventListener('click', (e) => {
        // Click outside modal closes.
        if (e.target === overlay) closeOptOutModal();
    });

    document.addEventListener('keydown', (e) => {
        const { overlay } = getOptOutEls();
        if (e.key === 'Escape' && overlay && !overlay.classList.contains('hidden')) {
            closeOptOutModal();
        }
    });

    submit?.addEventListener('click', submitOptOut);
}

document.addEventListener('DOMContentLoaded', initOptOut);

// Export (optional)
window.OptOut = {
    init: initOptOut,
    open: openOptOutModal,
    close: closeOptOutModal
};

