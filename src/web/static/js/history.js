/**
 * History page JavaScript
 */

(function() {
    'use strict';

    const PAGE_SIZE = 20;
    let currentPage = 0;
    let totalEntries = 0;
    let isSearchMode = false;
    let currentSearchQuery = '';
    let currentEntryId = null;
    let searchMode = 'keyword'; // 'keyword' or 'semantic'
    let semanticAvailable = false;

    // DOM Elements
    const elements = {
        historyList: document.getElementById('history-list'),
        loading: document.getElementById('loading'),
        searchInput: document.getElementById('search-input'),
        searchBtn: document.getElementById('search-btn'),
        clearHistoryBtn: document.getElementById('clear-history-btn'),
        pagination: document.getElementById('pagination'),
        prevPage: document.getElementById('prev-page'),
        nextPage: document.getElementById('next-page'),
        pageInfo: document.getElementById('page-info'),
        statTotal: document.getElementById('stat-total'),
        statWords: document.getElementById('stat-words'),
        entryModal: document.getElementById('entry-modal'),
        entryTitle: document.getElementById('entry-title'),
        entryMeta: document.getElementById('entry-meta'),
        entryTranscript: document.getElementById('entry-transcript'),
        entryModalClose: document.getElementById('entry-modal-close'),
        entryDeleteBtn: document.getElementById('entry-delete-btn'),
        entryCopyBtn: document.getElementById('entry-copy-btn'),
        confirmModal: document.getElementById('confirm-modal'),
        confirmCancel: document.getElementById('confirm-cancel'),
        confirmClear: document.getElementById('confirm-clear'),
        // Semantic search elements
        searchModeToggle: document.getElementById('search-mode-toggle'),
        reindexBtn: document.getElementById('reindex-btn'),
        semanticStatus: document.getElementById('semantic-status'),
        semanticIndicator: document.getElementById('semantic-indicator'),
        semanticStatusText: document.getElementById('semantic-status-text'),
        // Tab elements
        detailTabs: document.querySelectorAll('.detail-tab'),
        tabTranscript: document.getElementById('tab-transcript'),
        tabMetadata: document.getElementById('tab-metadata'),
        tabAnalysis: document.getElementById('tab-analysis'),
        entryAnalysis: document.getElementById('entry-analysis'),
        entryExportBtn: document.getElementById('entry-export-btn'),
        // Batch elements
        batchActions: document.getElementById('batch-actions'),
        batchCount: document.getElementById('batch-count'),
        batchSelectAll: document.getElementById('batch-select-all'),
        batchExport: document.getElementById('batch-export'),
        batchMerge: document.getElementById('batch-merge'),
        batchDelete: document.getElementById('batch-delete'),
        batchCancel: document.getElementById('batch-cancel'),
        // Merge modal elements
        mergeModal: document.getElementById('merge-modal'),
        mergeModalClose: document.getElementById('merge-modal-close'),
        mergeList: document.getElementById('merge-list'),
        mergeAddSeparators: document.getElementById('merge-add-separators'),
        mergeName: document.getElementById('merge-name'),
        mergeCancel: document.getElementById('merge-cancel'),
        mergeConfirm: document.getElementById('merge-confirm'),
    };

    // Batch selection state
    let selectedEntries = new Set();

    // Initialize
    document.addEventListener('DOMContentLoaded', init);

    function init() {
        initTheme();
        loadStats();
        loadHistory();
        bindEvents();
        checkSemanticSearchStatus();
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.innerHTML = savedTheme === 'dark' ? '&#9788;' : '&#9790;';
        }

        // Bind theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', toggleTheme);
        }
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme');
        const newTheme = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.innerHTML = newTheme === 'dark' ? '&#9788;' : '&#9790;';
        }
    }

    function bindEvents() {
        elements.searchBtn.addEventListener('click', performSearch);
        elements.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
        elements.searchInput.addEventListener('input', () => {
            if (elements.searchInput.value === '' && isSearchMode) {
                isSearchMode = false;
                currentPage = 0;
                loadHistory();
            }
        });

        elements.clearHistoryBtn.addEventListener('click', showConfirmModal);
        elements.confirmCancel.addEventListener('click', hideConfirmModal);
        elements.confirmClear.addEventListener('click', clearAllHistory);

        elements.prevPage.addEventListener('click', () => changePage(-1));
        elements.nextPage.addEventListener('click', () => changePage(1));

        elements.entryModalClose.addEventListener('click', hideEntryModal);
        elements.entryDeleteBtn.addEventListener('click', deleteCurrentEntry);
        elements.entryCopyBtn.addEventListener('click', copyCurrentEntry);
        elements.entryModal.addEventListener('click', (e) => {
            if (e.target === elements.entryModal) hideEntryModal();
        });
        elements.confirmModal.addEventListener('click', (e) => {
            if (e.target === elements.confirmModal) hideConfirmModal();
        });

        // Semantic search events
        if (elements.searchModeToggle) {
            elements.searchModeToggle.querySelectorAll('.mode-toggle-btn').forEach(btn => {
                btn.addEventListener('click', () => setSearchMode(btn.dataset.mode));
            });
        }
        if (elements.reindexBtn) {
            elements.reindexBtn.addEventListener('click', reindexAll);
        }

        // Tab events
        elements.detailTabs.forEach(tab => {
            tab.addEventListener('click', () => switchDetailTab(tab.dataset.tab));
        });

        // Export entry button
        if (elements.entryExportBtn) {
            elements.entryExportBtn.addEventListener('click', exportCurrentEntry);
        }

        // Batch operation events
        if (elements.batchSelectAll) {
            elements.batchSelectAll.addEventListener('click', selectAllEntries);
        }
        if (elements.batchExport) {
            elements.batchExport.addEventListener('click', exportSelectedEntries);
        }
        if (elements.batchDelete) {
            elements.batchDelete.addEventListener('click', deleteSelectedEntries);
        }
        if (elements.batchMerge) {
            elements.batchMerge.addEventListener('click', showMergeModal);
        }
        if (elements.batchCancel) {
            elements.batchCancel.addEventListener('click', cancelBatchSelection);
        }

        // Merge modal events
        if (elements.mergeModalClose) {
            elements.mergeModalClose.addEventListener('click', hideMergeModal);
        }
        if (elements.mergeCancel) {
            elements.mergeCancel.addEventListener('click', hideMergeModal);
        }
        if (elements.mergeConfirm) {
            elements.mergeConfirm.addEventListener('click', mergeSelectedEntries);
        }
        if (elements.mergeModal) {
            elements.mergeModal.addEventListener('click', (e) => {
                if (e.target === elements.mergeModal) hideMergeModal();
            });
        }
    }

    async function loadStats() {
        try {
            const response = await fetch('/api/history/stats');
            if (!response.ok) throw new Error('Failed to load stats');
            const stats = await response.json();

            elements.statTotal.textContent = `${stats.total_entries} transcription${stats.total_entries !== 1 ? 's' : ''}`;
            elements.statWords.textContent = `${stats.total_words.toLocaleString()} words`;
            totalEntries = stats.total_entries;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    async function loadHistory() {
        showLoading();
        try {
            const offset = currentPage * PAGE_SIZE;
            const response = await fetch(`/api/history?limit=${PAGE_SIZE}&offset=${offset}`);
            if (!response.ok) throw new Error('Failed to load history');
            const data = await response.json();

            totalEntries = data.total;
            renderHistoryList(data.entries);
            updatePagination();
        } catch (error) {
            console.error('Error loading history:', error);
            showError('Failed to load history');
        }
    }

    async function performSearch() {
        const query = elements.searchInput.value.trim();
        if (query.length < 2) {
            if (query.length === 0) {
                isSearchMode = false;
                currentPage = 0;
                loadHistory();
            }
            return;
        }

        isSearchMode = true;
        currentSearchQuery = query;
        currentPage = 0;
        showLoading();

        try {
            let response, data;

            if (searchMode === 'semantic' && semanticAvailable) {
                // Semantic search
                response = await fetch(`/api/semantic-search?q=${encodeURIComponent(query)}&limit=50`);
                if (!response.ok) throw new Error('Semantic search failed');
                data = await response.json();

                totalEntries = data.count;
                renderSemanticResults(data.results, query);
            } else {
                // Keyword search
                response = await fetch(`/api/history/search?q=${encodeURIComponent(query)}&limit=50`);
                if (!response.ok) throw new Error('Search failed');
                data = await response.json();

                totalEntries = data.count;
                renderHistoryList(data.entries, query);
            }
            elements.pagination.hidden = true;
        } catch (error) {
            console.error('Error searching:', error);
            showError('Search failed');
        }
    }

    function renderHistoryList(entries, highlightQuery = null) {
        elements.loading.hidden = true;

        if (entries.length === 0) {
            elements.historyList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#128196;</div>
                    <p>${isSearchMode ? 'No results found' : 'No transcriptions yet'}</p>
                    ${!isSearchMode ? '<p class="empty-hint">Transcribe some audio to see it here</p>' : ''}
                </div>
            `;
            return;
        }

        const html = entries.map(entry => {
            let preview = escapeHtml(entry.preview || '');
            if (highlightQuery) {
                const regex = new RegExp(`(${escapeRegExp(highlightQuery)})`, 'gi');
                preview = preview.replace(regex, '<mark>$1</mark>');
            }

            const date = new Date(entry.created_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            return `
                <div class="history-entry" data-id="${entry.id}">
                    <div class="entry-header">
                        <span class="entry-filename">${escapeHtml(entry.audio_filename)}</span>
                        <span class="entry-date">${dateStr}</span>
                    </div>
                    <div class="entry-preview">${preview}</div>
                    <div class="entry-footer">
                        <span class="entry-stat">${entry.word_count} words</span>
                        ${entry.language ? `<span class="entry-stat">${entry.language.toUpperCase()}</span>` : ''}
                        ${entry.speaker_count > 0 ? `<span class="entry-stat">${entry.speaker_count} speakers</span>` : ''}
                        ${entry.confidence ? `<span class="entry-stat">${Math.round(entry.confidence * 100)}% confidence</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        elements.historyList.innerHTML = html;

        // Bind click events to entries
        elements.historyList.querySelectorAll('.history-entry').forEach(el => {
            el.addEventListener('click', () => showEntryDetail(parseInt(el.dataset.id)));
        });
    }

    async function showEntryDetail(entryId) {
        currentEntryId = entryId;
        try {
            const response = await fetch(`/api/history/${entryId}`);
            if (!response.ok) throw new Error('Failed to load entry');
            const entry = await response.json();

            elements.entryTitle.textContent = entry.audio_filename;

            const date = new Date(entry.created_at);
            elements.entryMeta.innerHTML = `
                <div class="meta-card">
                    <div class="meta-card-label">Date</div>
                    <div class="meta-card-value">${date.toLocaleString()}</div>
                </div>
                <div class="meta-card">
                    <div class="meta-card-label">Words</div>
                    <div class="meta-card-value">${entry.word_count.toLocaleString()}</div>
                </div>
                ${entry.language ? `
                <div class="meta-card">
                    <div class="meta-card-label">Language</div>
                    <div class="meta-card-value">${entry.language.toUpperCase()}</div>
                </div>
                ` : ''}
                ${entry.model ? `
                <div class="meta-card">
                    <div class="meta-card-label">Model</div>
                    <div class="meta-card-value">${entry.model}</div>
                </div>
                ` : ''}
                ${entry.confidence ? `
                <div class="meta-card">
                    <div class="meta-card-label">Confidence</div>
                    <div class="meta-card-value">${Math.round(entry.confidence * 100)}%</div>
                </div>
                ` : ''}
                ${entry.speaker_count > 0 ? `
                <div class="meta-card">
                    <div class="meta-card-label">Speakers</div>
                    <div class="meta-card-value">${entry.speaker_count}</div>
                </div>
                ` : ''}
            `;

            elements.entryTranscript.textContent = entry.transcript_text || 'No transcript available';

            // Reset to transcript tab
            switchDetailTab('transcript');

            elements.entryModal.hidden = false;
        } catch (error) {
            console.error('Error loading entry:', error);
            alert('Failed to load entry details');
        }
    }

    function hideEntryModal() {
        elements.entryModal.hidden = true;
        currentEntryId = null;
    }

    async function deleteCurrentEntry() {
        if (!currentEntryId) return;
        if (!confirm('Delete this transcription?')) return;

        try {
            const response = await fetch(`/api/history/${currentEntryId}`, {method: 'DELETE'});
            if (!response.ok) throw new Error('Failed to delete');

            hideEntryModal();
            loadStats();
            if (isSearchMode) {
                performSearch();
            } else {
                loadHistory();
            }
        } catch (error) {
            console.error('Error deleting:', error);
            alert('Failed to delete entry');
        }
    }

    function copyCurrentEntry() {
        const text = elements.entryTranscript.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const btn = elements.entryCopyBtn;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = 'Copy Text', 2000);
        }).catch(err => {
            console.error('Copy failed:', err);
            alert('Failed to copy text');
        });
    }

    function showConfirmModal() {
        elements.confirmModal.hidden = false;
    }

    function hideConfirmModal() {
        elements.confirmModal.hidden = true;
    }

    async function clearAllHistory() {
        try {
            const response = await fetch('/api/history', {method: 'DELETE'});
            if (!response.ok) throw new Error('Failed to clear');

            hideConfirmModal();
            loadStats();
            loadHistory();
        } catch (error) {
            console.error('Error clearing:', error);
            alert('Failed to clear history');
        }
    }

    function updatePagination() {
        if (isSearchMode) {
            elements.pagination.hidden = true;
            return;
        }

        const totalPages = Math.ceil(totalEntries / PAGE_SIZE);
        elements.pagination.hidden = totalPages <= 1;
        elements.prevPage.disabled = currentPage === 0;
        elements.nextPage.disabled = currentPage >= totalPages - 1;
        elements.pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages}`;
    }

    function changePage(delta) {
        const totalPages = Math.ceil(totalEntries / PAGE_SIZE);
        const newPage = currentPage + delta;
        if (newPage >= 0 && newPage < totalPages) {
            currentPage = newPage;
            loadHistory();
        }
    }

    function showLoading() {
        elements.loading.hidden = false;
        elements.historyList.innerHTML = '';
        elements.historyList.appendChild(elements.loading);
    }

    function showError(message) {
        elements.loading.hidden = true;
        elements.historyList.innerHTML = `
            <div class="error-state">
                <p>${escapeHtml(message)}</p>
            </div>
        `;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // ========================================================================
    // Semantic Search Functions
    // ========================================================================

    async function checkSemanticSearchStatus() {
        try {
            const response = await fetch('/api/semantic-search/status');
            const data = await response.json();

            semanticAvailable = data.available;

            if (elements.semanticStatus) {
                elements.semanticStatus.hidden = false;
                elements.semanticIndicator.className = 'status-indicator ' + (data.available ? 'available' : 'unavailable');

                if (data.available) {
                    elements.semanticStatusText.textContent = `Semantic search: ${data.indexed_transcripts} indexed (${data.total_chunks} chunks)`;
                } else {
                    elements.semanticStatusText.textContent = `Semantic search unavailable: ${data.error || 'Unknown error'}`;
                }
            }

            // Disable semantic mode button if not available
            if (!semanticAvailable && elements.searchModeToggle) {
                const semanticBtn = elements.searchModeToggle.querySelector('[data-mode="semantic"]');
                if (semanticBtn) {
                    semanticBtn.disabled = true;
                    semanticBtn.title = 'Semantic search not available';
                }
            }
        } catch (error) {
            console.error('Error checking semantic search status:', error);
            semanticAvailable = false;
        }
    }

    function setSearchMode(mode) {
        if (mode === 'semantic' && !semanticAvailable) {
            alert('Semantic search is not available. Install sentence-transformers and reindex.');
            return;
        }

        searchMode = mode;

        // Update toggle buttons
        if (elements.searchModeToggle) {
            elements.searchModeToggle.querySelectorAll('.mode-toggle-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === mode);
            });
        }

        // Update placeholder text
        if (elements.searchInput) {
            elements.searchInput.placeholder = mode === 'semantic'
                ? 'Search by meaning...'
                : 'Search transcriptions...';
        }

        // Re-run search if there's a query
        if (isSearchMode && currentSearchQuery) {
            performSearch();
        }
    }

    function renderSemanticResults(results, query) {
        elements.loading.hidden = true;

        if (results.length === 0) {
            elements.historyList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#128270;</div>
                    <p>No semantically similar transcripts found</p>
                    <p class="empty-hint">Try a different search query or reindex your transcripts</p>
                </div>
            `;
            return;
        }

        const html = results.map(result => {
            const similarity = Math.round(result.similarity * 100);
            const similarityClass = similarity >= 70 ? 'high' : similarity >= 50 ? 'medium' : 'low';

            const date = new Date(result.created_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            // Truncate chunk text for preview
            let preview = escapeHtml(result.chunk_text || '');
            if (preview.length > 200) {
                preview = preview.substring(0, 200) + '...';
            }

            return `
                <div class="history-entry" data-id="${result.history_id}">
                    <div class="entry-header">
                        <span class="entry-filename">${escapeHtml(result.filename)}</span>
                        <span class="similarity-badge ${similarityClass}">${similarity}% match</span>
                        <span class="entry-date">${dateStr}</span>
                    </div>
                    <div class="entry-preview">${preview}</div>
                    <div class="entry-footer">
                        ${result.language ? `<span class="entry-stat">${result.language.toUpperCase()}</span>` : ''}
                        ${result.duration ? `<span class="entry-stat">${Math.round(result.duration)}s</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        elements.historyList.innerHTML = html;

        // Bind click events to entries
        elements.historyList.querySelectorAll('.history-entry').forEach(el => {
            el.addEventListener('click', () => showEntryDetail(parseInt(el.dataset.id)));
        });
    }

    async function reindexAll() {
        if (!confirm('This will reindex all transcripts for semantic search. This may take a while for large histories. Continue?')) {
            return;
        }

        if (elements.reindexBtn) {
            elements.reindexBtn.disabled = true;
            elements.reindexBtn.textContent = 'Reindexing...';
        }

        if (elements.semanticIndicator) {
            elements.semanticIndicator.className = 'status-indicator indexing';
        }
        if (elements.semanticStatusText) {
            elements.semanticStatusText.textContent = 'Reindexing all transcripts...';
        }

        try {
            const response = await fetch('/api/semantic-search/reindex', { method: 'POST' });
            if (!response.ok) throw new Error('Reindex failed');
            const data = await response.json();

            alert(`Reindexing complete! Indexed: ${data.indexed}, Failed: ${data.failed}`);
            checkSemanticSearchStatus();
        } catch (error) {
            console.error('Error reindexing:', error);
            alert('Reindexing failed: ' + error.message);
        } finally {
            if (elements.reindexBtn) {
                elements.reindexBtn.disabled = false;
                elements.reindexBtn.textContent = 'Reindex';
            }
        }
    }

    // ========================================================================
    // Detail Tab Functions
    // ========================================================================

    function switchDetailTab(tabName) {
        // Update tab buttons
        elements.detailTabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Show/hide tab content
        if (elements.tabTranscript) {
            elements.tabTranscript.hidden = tabName !== 'transcript';
        }
        if (elements.tabMetadata) {
            elements.tabMetadata.hidden = tabName !== 'metadata';
        }
        if (elements.tabAnalysis) {
            elements.tabAnalysis.hidden = tabName !== 'analysis';
        }
    }

    function exportCurrentEntry() {
        if (!currentEntryId) return;

        const text = elements.entryTranscript.textContent;
        const filename = elements.entryTitle.textContent || 'transcript';

        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename.replace(/\.[^/.]+$/, '') + '.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // ========================================================================
    // Batch Operation Functions
    // ========================================================================

    function updateBatchUI() {
        const count = selectedEntries.size;
        if (elements.batchActions) {
            elements.batchActions.hidden = count === 0;
        }
        if (elements.batchCount) {
            elements.batchCount.textContent = `${count} selected`;
        }
    }

    function selectAllEntries() {
        const checkboxes = elements.historyList.querySelectorAll('.entry-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = true;
            selectedEntries.add(parseInt(cb.dataset.id));
        });
        updateBatchUI();
    }

    function cancelBatchSelection() {
        const checkboxes = elements.historyList.querySelectorAll('.entry-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
        selectedEntries.clear();
        updateBatchUI();
    }

    async function exportSelectedEntries() {
        if (selectedEntries.size === 0) return;

        let combined = '';
        for (const id of selectedEntries) {
            try {
                const response = await fetch(`/api/history/${id}`);
                if (response.ok) {
                    const entry = await response.json();
                    combined += `=== ${entry.audio_filename} ===\n`;
                    combined += `Date: ${new Date(entry.created_at).toLocaleString()}\n\n`;
                    combined += (entry.transcript_text || '') + '\n\n';
                }
            } catch (e) {
                console.error('Error fetching entry:', e);
            }
        }

        const blob = new Blob([combined], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transcripts_export_${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        cancelBatchSelection();
    }

    async function deleteSelectedEntries() {
        if (selectedEntries.size === 0) return;

        const count = selectedEntries.size;
        if (!confirm(`Delete ${count} transcription${count !== 1 ? 's' : ''}? This cannot be undone.`)) {
            return;
        }

        let deleted = 0;
        for (const id of selectedEntries) {
            try {
                const response = await fetch(`/api/history/${id}`, { method: 'DELETE' });
                if (response.ok) deleted++;
            } catch (e) {
                console.error('Error deleting entry:', e);
            }
        }

        alert(`Deleted ${deleted} transcription${deleted !== 1 ? 's' : ''}`);
        selectedEntries.clear();
        updateBatchUI();
        loadStats();
        loadHistory();
    }

    // ========================================================================
    // Merge Functions
    // ========================================================================

    // State for merge ordering
    let mergeOrder = [];

    async function showMergeModal() {
        if (selectedEntries.size < 2) {
            alert('Please select at least 2 transcriptions to merge.');
            return;
        }

        // Fetch entry details for all selected entries
        mergeOrder = [];
        for (const id of selectedEntries) {
            try {
                const response = await fetch(`/api/history/${id}`);
                if (response.ok) {
                    const entry = await response.json();
                    mergeOrder.push({
                        id: entry.id,
                        filename: entry.audio_filename,
                        date: new Date(entry.created_at),
                        word_count: entry.word_count,
                    });
                }
            } catch (e) {
                console.error('Error fetching entry:', e);
            }
        }

        // Sort by date by default
        mergeOrder.sort((a, b) => a.date - b.date);

        // Render merge list
        renderMergeList();

        // Set default merge name
        if (elements.mergeName) {
            elements.mergeName.value = `Merged_${new Date().toISOString().slice(0, 10)}`;
        }

        elements.mergeModal.hidden = false;
    }

    function hideMergeModal() {
        elements.mergeModal.hidden = true;
        mergeOrder = [];
    }

    function renderMergeList() {
        if (!elements.mergeList) return;

        const html = mergeOrder.map((entry, index) => {
            const dateStr = entry.date.toLocaleDateString() + ' ' + entry.date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            return `
                <div class="merge-item" data-id="${entry.id}" draggable="true">
                    <span class="merge-handle">&#8597;</span>
                    <span class="merge-order">${index + 1}</span>
                    <span class="merge-filename">${escapeHtml(entry.filename)}</span>
                    <span class="merge-date">${dateStr}</span>
                    <span class="merge-words">${entry.word_count} words</span>
                </div>
            `;
        }).join('');

        elements.mergeList.innerHTML = html;

        // Add drag and drop functionality
        setupMergeDragDrop();
    }

    function setupMergeDragDrop() {
        const items = elements.mergeList.querySelectorAll('.merge-item');
        let draggedItem = null;

        items.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                draggedItem = item;
                item.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
                draggedItem = null;
                updateMergeOrder();
            });

            item.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                const rect = item.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;
                if (e.clientY < midY) {
                    item.classList.add('drag-above');
                    item.classList.remove('drag-below');
                } else {
                    item.classList.add('drag-below');
                    item.classList.remove('drag-above');
                }
            });

            item.addEventListener('dragleave', () => {
                item.classList.remove('drag-above', 'drag-below');
            });

            item.addEventListener('drop', (e) => {
                e.preventDefault();
                item.classList.remove('drag-above', 'drag-below');
                if (draggedItem && draggedItem !== item) {
                    const rect = item.getBoundingClientRect();
                    const midY = rect.top + rect.height / 2;
                    if (e.clientY < midY) {
                        elements.mergeList.insertBefore(draggedItem, item);
                    } else {
                        elements.mergeList.insertBefore(draggedItem, item.nextSibling);
                    }
                }
            });
        });
    }

    function updateMergeOrder() {
        const items = elements.mergeList.querySelectorAll('.merge-item');
        const newOrder = [];
        items.forEach((item, index) => {
            const id = parseInt(item.dataset.id);
            const entry = mergeOrder.find(e => e.id === id);
            if (entry) {
                newOrder.push(entry);
            }
            // Update order number display
            const orderSpan = item.querySelector('.merge-order');
            if (orderSpan) {
                orderSpan.textContent = index + 1;
            }
        });
        mergeOrder = newOrder;
    }

    async function mergeSelectedEntries() {
        if (mergeOrder.length < 2) {
            alert('Please select at least 2 transcriptions to merge.');
            return;
        }

        const addSeparators = elements.mergeAddSeparators?.checked ?? true;
        const mergeName = elements.mergeName?.value || `Merged_${Date.now()}`;
        const entryIds = mergeOrder.map(e => e.id);

        // Disable confirm button
        if (elements.mergeConfirm) {
            elements.mergeConfirm.disabled = true;
            elements.mergeConfirm.textContent = 'Merging...';
        }

        try {
            const response = await fetch('/api/history/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    entry_ids: entryIds,
                    add_separators: addSeparators,
                    merged_name: mergeName,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Merge failed');
            }

            const result = await response.json();
            alert(`Successfully merged ${entryIds.length} transcriptions!`);

            hideMergeModal();
            cancelBatchSelection();
            loadStats();
            loadHistory();

        } catch (error) {
            console.error('Error merging entries:', error);
            alert('Failed to merge: ' + error.message);
        } finally {
            if (elements.mergeConfirm) {
                elements.mergeConfirm.disabled = false;
                elements.mergeConfirm.textContent = 'Merge Transcriptions';
            }
        }
    }
})();
