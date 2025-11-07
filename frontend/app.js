// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// State Management
const state = {
    currentScreen: 'deck-selection',
    decks: [],
    currentDeck: null,
    sessionId: null,
    currentCard: null,
    sessionStats: {
        cardsReviewed: 0,
        totalScore: 0,
        grades: { perfect: 0, good: 0, partial: 0, wrong: 0 }
    },
    showEmptyDecks: false // Filter state for empty decks
};

// Utility Functions
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
    state.currentScreen = screenId;
}

function showLoading(show = true) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// Custom Notification System
let notificationId = 0;
const notificationIcons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
};

function showNotification(message, type = 'info', title = '', duration = 5000) {
    const container = document.getElementById('notification-container');
    const id = ++notificationId;

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.id = `notification-${id}`;

    const icon = notificationIcons[type] || notificationIcons.info;

    notification.innerHTML = `
        <div class="notification-icon">${icon}</div>
        <div class="notification-content">
            ${title ? `<div class="notification-title">${title}</div>` : ''}
            <p class="notification-message">${message}</p>
        </div>
        <button class="notification-close" onclick="closeNotification(${id})">&times;</button>
    `;

    // Add to container
    container.appendChild(notification);

    // Trigger animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto-hide after duration
    if (duration > 0) {
        setTimeout(() => {
            closeNotification(id);
        }, duration);
    }

    return id;
}

function closeNotification(id) {
    const notification = document.getElementById(`notification-${id}`);
    if (notification) {
        notification.classList.add('hide');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
}

// Notification helper functions
function showSuccess(message, title = 'Success') {
    return showNotification(message, 'success', title);
}

function showError(message, title = 'Error') {
    return showNotification(message, 'error', title);
}

function showWarning(message, title = 'Warning') {
    return showNotification(message, 'warning', title);
}

function showInfo(message, title = 'Information') {
    return showNotification(message, 'info', title);
}

// Custom Confirmation System
function showConfirmation(message, title = 'Confirm Action', options = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmation-modal');
        const titleEl = document.getElementById('confirmation-title');
        const messageEl = document.getElementById('confirmation-message');
        const iconEl = document.getElementById('confirmation-icon');
        const yesBtn = document.getElementById('confirm-yes-btn');
        const noBtn = document.getElementById('confirm-no-btn');

        // Set content
        titleEl.textContent = title;
        messageEl.textContent = message;

        // Set icon and colors based on options
        if (options.danger) {
            iconEl.textContent = '⚠️';
            yesBtn.className = 'btn btn-danger';
            yesBtn.textContent = options.confirmText || 'Delete';
        } else {
            iconEl.textContent = options.icon || '❓';
            yesBtn.className = 'btn btn-primary';
            yesBtn.textContent = options.confirmText || 'Yes';
        }

        noBtn.textContent = options.cancelText || 'No';

        // Show modal
        modal.classList.remove('hidden');

        // Handle click events
        const handleYes = () => {
            cleanup();
            resolve(true);
        };

        const handleNo = () => {
            cleanup();
            resolve(false);
        };

        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                resolve(false);
            }
        };

        const cleanup = () => {
            modal.classList.add('hidden');
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
            document.removeEventListener('keydown', handleEscape);
        };

        // Add event listeners
        yesBtn.addEventListener('click', handleYes);
        noBtn.addEventListener('click', handleNo);
        document.addEventListener('keydown', handleEscape);

        // Focus the appropriate button
        (options.danger ? noBtn : yesBtn).focus();
    });
}

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Deck Management
async function loadDecks() {
    try {
        showLoading();
        const url = `/api/decks${state.showEmptyDecks ? '?include_empty=true' : ''}`;
        const decks = await apiCall(url);
        state.decks = decks;
        renderDecks();
    } catch (error) {
        showError(`Failed to load decks: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function renderDecks() {
    const deckList = document.getElementById('deck-list');

    if (state.decks.length === 0) {
        deckList.innerHTML = '<p style="color: #666; text-align: center;">No decks available. Import a markdown file to get started.</p>';
        return;
    }

    deckList.innerHTML = state.decks.map(deck => {
        const dueCards = deck.stats?.due_cards || 0;
        const totalCards = deck.stats?.total_cards || 0;

        return `
        <div class="deck-card" data-deck-id="${deck.id}">
            <div class="deck-checkbox">
                <input type="checkbox"
                       id="deck-checkbox-${deck.id}"
                       onchange="toggleDeckSelection('${deck.id}')"
                       onclick="event.stopPropagation()">
            </div>
            <div class="deck-actions">
                <button class="btn btn-secondary" onclick="event.stopPropagation(); editDeck('${deck.id}')" title="Edit deck">✏️</button>
                <button class="btn btn-danger" onclick="event.stopPropagation(); deleteDeck('${deck.id}')" title="Delete deck">🗑️</button>
            </div>
            <h3>${deck.name}</h3>
            ${deck.source_file ? `<p class="deck-info">Source: ${deck.source_file.split('/').pop()}</p>` : ''}
            <div class="deck-stats">
                <span>Cards: ${totalCards}</span>
                <span>Reviewed: ${deck.stats?.reviewed_cards || 0}</span>
                ${deck.stats?.average_score ? `<span>Avg: ${deck.stats.average_score.toFixed(1)}</span>` : ''}
                ${dueCards > 0 ? `<span class="due-cards-badge">📅 ${dueCards} due</span>` : ''}
            </div>
            <div class="deck-study-buttons">
                ${dueCards > 0 ? `
                    <button class="btn btn-primary" onclick="startDueStudySession('${deck.id}')" title="Study only cards that are due for review">
                        Study Due Cards (${dueCards})
                    </button>
                    <button class="btn btn-secondary" onclick="startStudySession('${deck.id}')" title="Study all cards in deck">
                        Study All Cards (${totalCards})
                    </button>
                ` : `
                    <button class="btn btn-primary" onclick="startStudySession('${deck.id}')" title="Study all cards in deck" ${totalCards === 0 ? 'disabled' : ''}>
                        ${totalCards === 0 ? 'No Cards to Study' : `Study All Cards (${totalCards})`}
                    </button>
                `}
            </div>
        </div>
        `;
    }).join('');

    // Update selection state
    updateSelectionUI();
}

async function startStudySession(deckId) {
    try {
        showLoading();

        // Start session
        const session = await apiCall('/api/sessions/start', {
            method: 'POST',
            body: JSON.stringify({ deck_id: deckId })
        });

        state.sessionId = session.session_id;
        state.currentDeck = state.decks.find(d => d.id === deckId);
        state.sessionStats = {
            cardsReviewed: 0,
            totalScore: 0,
            grades: { perfect: 0, good: 0, partial: 0, wrong: 0 }
        };

        // Load first card
        await loadNextCard();

        showScreen('study-session');
        updateSessionInfo();
    } catch (error) {
        showError(`Failed to start session: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function startDueStudySession(deckId) {
    try {
        showLoading();
        // Start due cards session
        const session = await apiCall('/api/sessions/start-due', {
            method: 'POST',
            body: JSON.stringify({ deck_id: deckId })
        });
        state.sessionId = session.session_id;
        state.currentDeck = state.decks.find(d => d.id === deckId);
        state.sessionStats = {
            cardsReviewed: 0,
            totalScore: 0,
            grades: { perfect: 0, good: 0, partial: 0, wrong: 0 }
        };
        state.sessionType = 'due_only'; // Track session type

        // Load first card
        await loadNextCard();
        showScreen('study-session');
        updateSessionInfo();
    } catch (error) {
        showError(`Failed to start due cards session: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function loadNextCard() {
    try {
        showLoading();

        const response = await apiCall(`/api/sessions/${state.sessionId}/next`);

        if (response.complete) {
            showSessionComplete();
            return;
        }

        state.currentCard = response.flashcard;
        renderQuestion();

        // Hide feedback, show answer input
        document.getElementById('feedback-section').classList.add('hidden');
        document.getElementById('answer-section').classList.remove('hidden');
        document.getElementById('user-answer').value = '';
        document.getElementById('reference-answer-section').classList.add('hidden');

        updateSessionInfo();
    } catch (error) {
        showError(`Failed to load card: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function renderQuestion() {
    const questionText = document.getElementById('question-text');
    questionText.textContent = state.currentCard.question;
}

function updateSessionInfo() {
    const sessionInfo = document.getElementById('session-info');
    sessionInfo.classList.remove('hidden');

    const cardCounter = document.getElementById('card-counter');
    const avgScore = document.getElementById('avg-score');

    const currentIndex = state.sessionStats.cardsReviewed + 1;
    cardCounter.textContent = `Card ${currentIndex} of ${state.currentDeck?.stats?.total_cards || '?'}`;

    if (state.sessionStats.cardsReviewed > 0) {
        const avg = state.sessionStats.totalScore / state.sessionStats.cardsReviewed;
        avgScore.textContent = `Avg Score: ${avg.toFixed(1)}`;
    } else {
        avgScore.textContent = 'Avg Score: --';
    }
}

async function submitAnswer() {
    const userAnswer = document.getElementById('user-answer').value.trim();

    if (!userAnswer) {
        showError('Please enter an answer before submitting.');
        return;
    }

    try {
        showLoading();

        const result = await apiCall('/api/grade', {
            method: 'POST',
            body: JSON.stringify({
                flashcard_id: state.currentCard.id,
                user_answer: userAnswer
            })
        });

        // Update stats
        state.sessionStats.cardsReviewed++;
        state.sessionStats.totalScore += result.score;
        const gradeKey = result.grade.toLowerCase();
        if (state.sessionStats.grades[gradeKey] !== undefined) {
            state.sessionStats.grades[gradeKey]++;
        }

        // Show feedback
        renderFeedback(result);

        // Hide answer section, show feedback
        document.getElementById('answer-section').classList.add('hidden');
        document.getElementById('feedback-section').classList.remove('hidden');

        // Show reference answer
        const refSection = document.getElementById('reference-answer-section');
        const refText = document.getElementById('reference-answer-text');
        refText.textContent = state.currentCard.answer;
        refSection.classList.remove('hidden');

        updateSessionInfo();
    } catch (error) {
        showError(`Failed to grade answer: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function renderFeedback(result) {
    const gradeBadge = document.getElementById('grade-badge');
    const scoreValue = document.getElementById('score-value');
    const feedbackText = document.getElementById('feedback-text');

    // Set grade badge
    gradeBadge.textContent = result.grade;
    gradeBadge.className = 'grade-badge ' + result.grade.toLowerCase();

    // Set score
    scoreValue.textContent = `${result.score}/100`;

    // Set feedback
    feedbackText.textContent = result.feedback;

    // Render concepts
    renderConcepts(result);
}

function renderConcepts(result) {
    const coveredSection = document.getElementById('concepts-covered');
    const missedSection = document.getElementById('concepts-missed');
    const coveredList = document.getElementById('covered-list');
    const missedList = document.getElementById('missed-list');

    // Covered concepts
    if (result.key_concepts_covered && result.key_concepts_covered.length > 0) {
        coveredList.innerHTML = result.key_concepts_covered
            .map(concept => `<li>${concept}</li>`)
            .join('');
        coveredSection.classList.remove('hidden');
    } else {
        coveredSection.classList.add('hidden');
    }

    // Missed concepts
    if (result.key_concepts_missed && result.key_concepts_missed.length > 0) {
        missedList.innerHTML = result.key_concepts_missed
            .map(concept => `<li>${concept}</li>`)
            .join('');
        missedSection.classList.remove('hidden');
    } else {
        missedSection.classList.add('hidden');
    }
}

function skipCard() {
    loadNextCard();
}

function showSessionComplete() {
    const finalCardsReviewed = document.getElementById('final-cards-reviewed');
    const finalAvgScore = document.getElementById('final-avg-score');
    const gradeDistribution = document.getElementById('grade-distribution');

    finalCardsReviewed.textContent = state.sessionStats.cardsReviewed;

    if (state.sessionStats.cardsReviewed > 0) {
        const avg = state.sessionStats.totalScore / state.sessionStats.cardsReviewed;
        finalAvgScore.textContent = avg.toFixed(1);
    } else {
        finalAvgScore.textContent = '0';
    }

    // Render grade distribution
    gradeDistribution.innerHTML = Object.entries(state.sessionStats.grades)
        .filter(([_, count]) => count > 0)
        .map(([grade, count]) => `
            <div class="grade-dist-item">
                <strong>${grade.charAt(0).toUpperCase() + grade.slice(1)}:</strong> ${count}
            </div>
        `)
        .join('');

    showScreen('session-complete');

    // Hide session info in header
    document.getElementById('session-info').classList.add('hidden');
}

async function endSession() {
    const confirmed = await showConfirmation(
        'Your progress will be saved, but you will return to the session summary.',
        'End Study Session',
        {
            danger: true,
            confirmText: 'End Session',
            cancelText: 'Continue Studying'
        }
    );

    if (confirmed) {
        showSessionComplete();
    }
}

function returnToDecks() {
    state.sessionId = null;
    state.currentCard = null;
    state.currentDeck = null;
    document.getElementById('session-info').classList.add('hidden');
    loadDecks();
    showScreen('deck-selection');
}

// Import Functionality
function showImportForm() {
    document.getElementById('import-form').classList.remove('hidden');
}

function hideImportForm() {
    document.getElementById('import-form').classList.add('hidden');
    document.getElementById('file-input').value = '';
    document.getElementById('deck-name-input').value = '';
}

async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const deckNameInput = document.getElementById('deck-name-input');

    if (!fileInput.files || fileInput.files.length === 0) {
        showError('Please select a file to upload.');
        return;
    }

    const file = fileInput.files[0];

    try {
        showLoading();

        const formData = new FormData();
        formData.append('file', file);
        if (deckNameInput.value.trim()) {
            formData.append('deck_name', deckNameInput.value.trim());
        }

        const response = await fetch(`${API_BASE_URL}/api/decks/import`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();

        hideImportForm();
        await loadDecks();

        showSuccess(`Successfully imported ${result.flashcards_count} flashcards into deck "${result.deck_name}"!`);
    } catch (error) {
        showError(`Failed to import file: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Deck selection
    document.getElementById('import-btn').addEventListener('click', showImportForm);
    document.getElementById('cancel-import-btn').addEventListener('click', hideImportForm);
    document.getElementById('upload-btn').addEventListener('click', uploadFile);

    // Study session
    document.getElementById('submit-answer-btn').addEventListener('click', submitAnswer);
    document.getElementById('skip-btn').addEventListener('click', skipCard);
    document.getElementById('end-session-btn').addEventListener('click', endSession);
    document.getElementById('end-session-btn-feedback').addEventListener('click', endSession);
    document.getElementById('next-card-btn').addEventListener('click', loadNextCard);

    // Session complete
    document.getElementById('return-to-decks-btn').addEventListener('click', returnToDecks);

    // Keyboard shortcuts
    setupKeyboardShortcuts();

    // Modal event handlers
    document.getElementById('cancel-edit-btn').addEventListener('click', closeModal);
    document.getElementById('cancel-delete-btn').addEventListener('click', closeModal);
    document.getElementById('cancel-bulk-delete-btn').addEventListener('click', closeModal);
    document.getElementById('confirm-delete-btn').addEventListener('click', confirmDelete);
    document.getElementById('confirm-bulk-delete-btn').addEventListener('click', confirmBulkDelete);
    document.getElementById('deck-form').addEventListener('submit', saveDeck);

    // Filter event handlers
    document.getElementById('show-empty-decks-checkbox').addEventListener('change', toggleEmptyDecksFilter);

    // Selection event handlers
    document.getElementById('select-all-checkbox').addEventListener('change', toggleSelectAll);
    document.getElementById('delete-selected-btn').addEventListener('click', bulkDeleteDecks);

    // Close modal on background click
    document.getElementById('deck-management-modal').addEventListener('click', (e) => {
        if (e.target.id === 'deck-management-modal') closeModal();
    });
    document.getElementById('delete-confirmation-modal').addEventListener('click', (e) => {
        if (e.target.id === 'delete-confirmation-modal') closeModal();
    });
    document.getElementById('bulk-delete-confirmation-modal').addEventListener('click', (e) => {
        if (e.target.id === 'bulk-delete-confirmation-modal') closeModal();
    });
    document.getElementById('confirmation-modal').addEventListener('click', (e) => {
        if (e.target.id === 'confirmation-modal') {
            // Close confirmation modal by simulating 'No' button click
            const noBtn = document.getElementById('confirm-no-btn');
            if (noBtn) noBtn.click();
        }
    });

    // Initial load
    loadDecks();
});

// Deck Management Functions
let currentEditingDeckId = null;
let currentDeletingDeckId = null;
let selectedDeckIds = new Set();

function editDeck(deckId) {
    const deck = state.decks.find(d => d.id === deckId);
    if (!deck) return;

    currentEditingDeckId = deckId;
    document.getElementById('modal-title').textContent = 'Edit Deck';
    document.getElementById('deck-name-edit').value = deck.name;
    document.getElementById('deck-source-edit').value = deck.source_file || '';

    showModal('deck-management-modal');
}

function deleteDeck(deckId) {
    const deck = state.decks.find(d => d.id === deckId);
    if (!deck) return;

    currentDeletingDeckId = deckId;
    document.getElementById('delete-deck-name').textContent = deck.name;

    showModal('delete-confirmation-modal');
}

function showModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal() {
    document.getElementById('deck-management-modal').classList.add('hidden');
    document.getElementById('delete-confirmation-modal').classList.add('hidden');
    document.getElementById('bulk-delete-confirmation-modal').classList.add('hidden');
    currentEditingDeckId = null;
    currentDeletingDeckId = null;
}

async function saveDeck(e) {
    e.preventDefault();

    if (!currentEditingDeckId) return;

    const deckName = document.getElementById('deck-name-edit').value.trim();
    const sourceFile = document.getElementById('deck-source-edit').value.trim();

    if (!deckName) {
        showError('Deck name is required');
        return;
    }

    try {
        showLoading();

        const updateData = { name: deckName };
        if (sourceFile) {
            updateData.source_file = sourceFile;
        }

        await apiCall(`/api/decks/${currentEditingDeckId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });

        closeModal();
        await loadDecks(); // Refresh the deck list
        showSuccess('Deck updated successfully!');

    } catch (error) {
        showError('Failed to update deck: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function confirmDelete() {
    if (!currentDeletingDeckId) return;

    try {
        showLoading();

        await apiCall(`/api/decks/${currentDeletingDeckId}`, {
            method: 'DELETE'
        });

        closeModal();
        await loadDecks(); // Refresh the deck list
        showSuccess('Deck deleted successfully!');

    } catch (error) {
        showError('Failed to delete deck: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Bulk Selection Functions
function toggleDeckSelection(deckId) {
    if (selectedDeckIds.has(deckId)) {
        selectedDeckIds.delete(deckId);
        document.querySelector(`[data-deck-id="${deckId}"]`).classList.remove('selected');
    } else {
        selectedDeckIds.add(deckId);
        document.querySelector(`[data-deck-id="${deckId}"]`).classList.add('selected');
    }
    updateSelectionUI();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    if (selectAllCheckbox.checked) {
        // Select all decks
        state.decks.forEach(deck => {
            selectedDeckIds.add(deck.id);
            document.getElementById(`deck-checkbox-${deck.id}`).checked = true;
            document.querySelector(`[data-deck-id="${deck.id}"]`).classList.add('selected');
        });
    } else {
        // Deselect all decks
        selectedDeckIds.clear();
        state.decks.forEach(deck => {
            document.getElementById(`deck-checkbox-${deck.id}`).checked = false;
            document.querySelector(`[data-deck-id="${deck.id}"]`).classList.remove('selected');
        });
    }
    updateSelectionUI();
}

function updateSelectionUI() {
    const selectedCount = selectedDeckIds.size;
    const totalCount = state.decks.length;
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const selectedCountSpan = document.getElementById('selected-count');

    // Update count display
    selectedCountSpan.textContent = selectedCount;

    // Show/hide delete button
    if (selectedCount > 0) {
        deleteSelectedBtn.classList.remove('hidden');
    } else {
        deleteSelectedBtn.classList.add('hidden');
    }

    // Update select all checkbox state
    if (selectedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (selectedCount === totalCount) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

function bulkDeleteDecks() {
    if (selectedDeckIds.size === 0) return;

    const selectedDecks = state.decks.filter(deck => selectedDeckIds.has(deck.id));
    document.getElementById('bulk-delete-count').textContent = selectedDecks.length;

    // Create list of selected deck names
    const deckList = document.getElementById('bulk-delete-list');
    deckList.innerHTML = '<ul>' + selectedDecks.map(deck => `<li>${deck.name}</li>`).join('') + '</ul>';

    showModal('bulk-delete-confirmation-modal');
}

async function confirmBulkDelete() {
    if (selectedDeckIds.size === 0) return;

    const originalSelectedCount = selectedDeckIds.size;

    try {
        showLoading();

        await apiCall('/api/decks/bulk-delete', {
            method: 'POST',
            body: JSON.stringify({ deck_ids: Array.from(selectedDeckIds) })
        });

        // Clear selection
        selectedDeckIds.clear();

        closeModal();
        await loadDecks(); // Refresh the deck list
        showSuccess(`Successfully deleted ${originalSelectedCount} deck(s)!`);

    } catch (error) {
        showError('Failed to delete decks: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Empty Deck Filter Functions
async function toggleEmptyDecksFilter() {
    const checkbox = document.getElementById('show-empty-decks-checkbox');
    state.showEmptyDecks = checkbox.checked;

    // Clear selection when filtering changes
    selectedDeckIds.clear();

    // Reload decks with new filter
    await loadDecks();
}

// Keyboard Shortcuts
function setupKeyboardShortcuts() {
    // Update keyboard hints based on platform
    updateKeyboardHints();

    // Helper function to check for Ctrl/Cmd + Enter
    const isSubmitShortcut = (e) => {
        return e.key === 'Enter' && (e.ctrlKey || e.metaKey);
    };

    // Study session answer submission
    const userAnswerField = document.getElementById('user-answer');
    if (userAnswerField) {
        userAnswerField.addEventListener('keydown', (e) => {
            if (isSubmitShortcut(e)) {
                e.preventDefault();
                submitAnswer();
            }
        });
    }

    // Deck name input during import
    const deckNameInput = document.getElementById('deck-name-input');
    if (deckNameInput) {
        deckNameInput.addEventListener('keydown', (e) => {
            if (isSubmitShortcut(e)) {
                e.preventDefault();
                const uploadBtn = document.getElementById('upload-btn');
                if (uploadBtn && !uploadBtn.disabled) {
                    uploadBtn.click();
                }
            }
        });
    }

    // Deck edit modal form
    const deckEditForm = document.getElementById('deck-form');
    if (deckEditForm) {
        // Add shortcut to all inputs in the form
        const formInputs = deckEditForm.querySelectorAll('input[type="text"]');
        formInputs.forEach(input => {
            input.addEventListener('keydown', (e) => {
                if (isSubmitShortcut(e)) {
                    e.preventDefault();
                    deckEditForm.requestSubmit(); // Triggers form validation and submit event
                }
            });
        });
    }

    // Global shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key handling
        if (e.key === 'Escape') {
            // Close any open modals first
            const openModals = document.querySelectorAll('.modal:not(.hidden)');
            if (openModals.length > 0) {
                e.preventDefault();
                closeModal();
                return;
            }

            // If no modals open and we're in a study session, end the session
            const studySessionScreen = document.getElementById('study-session');
            if (studySessionScreen && !studySessionScreen.classList.contains('hidden')) {
                e.preventDefault();
                endSession(); // endSession() now handles confirmation internally
            }
        }

        // Ctrl/Cmd + Arrow Right for next card (only during study sessions)
        if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowRight') {
            const studySessionScreen = document.getElementById('study-session');
            const feedbackSection = document.getElementById('feedback-section');

            // Only trigger if we're in study session and showing feedback (ready for next card)
            if (studySessionScreen && !studySessionScreen.classList.contains('hidden') &&
                feedbackSection && !feedbackSection.classList.contains('hidden')) {

                e.preventDefault();
                nextCard();
            }
        }

        // TODO: Ctrl/Cmd + Arrow Left could be used for "Previous Card" functionality in future
        // Currently not implemented as study sessions are forward-only
    });
}

function updateKeyboardHints() {
    // Detect if user is on Mac (show ⌘) or PC (show Ctrl)
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 || navigator.userAgent.toUpperCase().indexOf('MAC') >= 0;
    const shortcutText = isMac ? '⌘+Enter' : 'Ctrl+Enter';

    // Update keyboard hints based on their content
    document.querySelectorAll('.keyboard-hint').forEach(hint => {
        const parentButton = hint.closest('button');
        if (!parentButton) return;

        const buttonText = parentButton.textContent.trim().toLowerCase();

        if (buttonText.includes('submit') || buttonText.includes('save') || buttonText.includes('upload')) {
            hint.textContent = `(${shortcutText})`;
        } else if (buttonText.includes('next card')) {
            const arrowText = isMac ? '⌘+→' : 'Ctrl+→';
            hint.textContent = `(${arrowText})`;
        } else if (buttonText.includes('end session')) {
            hint.textContent = '(Esc)';
        }
    });

    // Update placeholders with correct shortcuts
    const userAnswer = document.getElementById('user-answer');
    if (userAnswer) {
        userAnswer.placeholder = `Type your answer here... Press ${shortcutText} to submit`;
    }

    const deckNameInput = document.getElementById('deck-name-input');
    if (deckNameInput) {
        deckNameInput.placeholder = `Deck name (optional) - Press ${shortcutText} to upload`;
    }
}

// Settings Management
let currentSettings = {
    initial_interval_days: 1,
    easy_multiplier: 2.5,
    good_multiplier: 1.8,
    minimum_interval_days: 1,
    maximum_interval_days: 180
};

async function openSettings() {
    try {
        // Load current settings from API
        const response = await apiCall('/api/config');
        currentSettings = response;
        populateSettingsForm();
        showModal('settings-modal');
    } catch (error) {
        showError(`Failed to load settings: ${error.message}`);
    }
}

function populateSettingsForm() {
    document.getElementById('initial-interval').value = currentSettings.initial_interval_days;
    document.getElementById('easy-multiplier').value = currentSettings.easy_multiplier;
    document.getElementById('good-multiplier').value = currentSettings.good_multiplier;
    document.getElementById('min-interval').value = currentSettings.minimum_interval_days;
    document.getElementById('max-interval').value = currentSettings.maximum_interval_days;
}

async function saveSettings() {
    try {
        // Get values from form
        const settings = {
            initial_interval_days: parseInt(document.getElementById('initial-interval').value),
            easy_multiplier: parseFloat(document.getElementById('easy-multiplier').value),
            good_multiplier: parseFloat(document.getElementById('good-multiplier').value),
            minimum_interval_days: parseInt(document.getElementById('min-interval').value),
            maximum_interval_days: parseInt(document.getElementById('max-interval').value)
        };

        // Validate settings
        if (settings.initial_interval_days < 1 || settings.initial_interval_days > 365) {
            showError('Initial interval must be between 1 and 365 days');
            return;
        }
        if (settings.easy_multiplier < 1.1 || settings.easy_multiplier > 5.0) {
            showError('Perfect grade multiplier must be between 1.1 and 5.0');
            return;
        }
        if (settings.good_multiplier < 1.1 || settings.good_multiplier > 5.0) {
            showError('Good grade multiplier must be between 1.1 and 5.0');
            return;
        }
        if (settings.minimum_interval_days < 1 || settings.minimum_interval_days > 30) {
            showError('Minimum interval must be between 1 and 30 days');
            return;
        }
        if (settings.maximum_interval_days < 30 || settings.maximum_interval_days > 1825) {
            showError('Maximum interval must be between 30 and 1825 days');
            return;
        }
        if (settings.minimum_interval_days >= settings.maximum_interval_days) {
            showError('Minimum interval must be less than maximum interval');
            return;
        }

        // Save to API
        await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify(settings)
        });

        currentSettings = settings;
        closeModal();
        showSuccess('Settings saved successfully!');

    } catch (error) {
        showError(`Failed to save settings: ${error.message}`);
    }
}

async function resetSettings() {
    const confirmed = await showConfirmation(
        'This will restore all spaced repetition settings to their default values. Your current custom settings will be lost.',
        'Reset Settings to Defaults',
        {
            danger: true,
            confirmText: 'Reset to Defaults',
            cancelText: 'Keep Current Settings'
        }
    );

    if (confirmed) {
        // Reset to default values
        currentSettings = {
            initial_interval_days: 1,
            easy_multiplier: 2.5,
            good_multiplier: 1.8,
            minimum_interval_days: 1,
            maximum_interval_days: 180
        };

        try {
            await apiCall('/api/config', {
                method: 'PUT',
                body: JSON.stringify(currentSettings)
            });

            populateSettingsForm();
            showSuccess('Settings have been reset to default values');
        } catch (error) {
            showError(`Failed to reset settings: ${error.message}`);
        }
    }
}

function cancelSettings() {
    // Restore original values without saving
    populateSettingsForm();
    closeModal();
}

// Initialize settings event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Settings button
    document.getElementById('settings-btn').addEventListener('click', openSettings);

    // Settings modal buttons
    document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
    document.getElementById('cancel-settings-btn').addEventListener('click', cancelSettings);
    document.getElementById('reset-settings-btn').addEventListener('click', resetSettings);
});
