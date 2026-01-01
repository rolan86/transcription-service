/**
 * Settings modal functionality
 */

// State
let currentSettings = null;

// Elements - initialized after DOM ready
let settingsBtn, settingsModal, settingsModalClose, settingsCancel, settingsSave;
let aiStatus, aiProvider, ollamaModel, ollamaUrl;
let anthropicKey, claudeModel, zaiKey, zaiModel, zaiUrl, llamaPath;
let featuresStatus, featureDetails;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get element references after DOM is ready
    settingsBtn = document.getElementById('settings-btn');
    settingsModal = document.getElementById('settings-modal');
    settingsModalClose = document.getElementById('settings-modal-close');
    settingsCancel = document.getElementById('settings-cancel');
    settingsSave = document.getElementById('settings-save');
    aiStatus = document.getElementById('ai-status');
    aiProvider = document.getElementById('ai-provider');
    ollamaModel = document.getElementById('ollama-model');
    ollamaUrl = document.getElementById('ollama-url');
    anthropicKey = document.getElementById('anthropic-key');
    claudeModel = document.getElementById('claude-model');
    zaiKey = document.getElementById('zai-key');
    zaiModel = document.getElementById('zai-model');
    zaiUrl = document.getElementById('zai-url');
    llamaPath = document.getElementById('llama-path');
    featuresStatus = document.getElementById('features-status');
    featureDetails = document.getElementById('feature-details');

    setupSettingsListeners();
    updateStatusBar();

    // Export functions to window for inline handlers
    window.saveAISettings = saveAISettings;
    window.openSettings = openSettings;
    window.updateStatusBar = updateStatusBar;
});

function setupSettingsListeners() {
    // Open modal
    settingsBtn?.addEventListener('click', openSettings);

    // Close modal
    settingsModalClose?.addEventListener('click', closeSettings);
    settingsCancel?.addEventListener('click', closeSettings);

    // Close on overlay click
    settingsModal?.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            closeSettings();
        }
    });

    // Save settings
    if (settingsSave) {
        settingsSave.addEventListener('click', saveAISettings);
    }

    // Provider selection change - show/hide appropriate settings
    aiProvider?.addEventListener('change', (e) => {
        showProviderSettings(e.target.value);
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && settingsModal && !settingsModal.hidden) {
            closeSettings();
        }
    });
}

async function openSettings() {
    if (!settingsModal) return;

    settingsModal.hidden = false;
    await loadSettings();
}

function closeSettings() {
    if (!settingsModal) return;
    settingsModal.hidden = true;
}

async function loadSettings() {
    try {
        // Fetch settings and status in parallel
        const [settingsResponse, statusResponse] = await Promise.all([
            fetch('/api/settings'),
            fetch('/api/settings/status'),
        ]);

        if (!settingsResponse.ok) {
            if (settingsResponse.status === 404) {
                throw new Error('Settings API not found. Please restart the server.');
            }
            const errorData = await settingsResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to load settings');
        }

        currentSettings = await settingsResponse.json();
        populateSettings(currentSettings);

        // Load features status
        if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            updateFeaturesStatus(statusData);
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
        showSettingsError(error.message);
    }
}

/**
 * Show only the settings section for the selected provider.
 */
function showProviderSettings(provider) {
    const allSections = document.querySelectorAll('.provider-settings');
    allSections.forEach(section => {
        section.hidden = section.dataset.provider !== provider;
    });
}

function populateSettings(settings) {
    const ai = settings.ai || {};

    // Show AI status
    updateAIStatus(ai);

    // Set current provider and show its settings
    const provider = ai.provider || 'ollama';
    if (aiProvider) {
        aiProvider.value = provider;
    }
    showProviderSettings(provider);

    // Populate Ollama models
    if (ollamaModel && ai.ollama?.models) {
        populateOllamaModels(ai.ollama.models, ai.ollama.model);
    }

    // Set Ollama URL
    if (ollamaUrl) {
        ollamaUrl.value = ai.ollama?.base_url || 'http://localhost:11434';
    }

    // Set Claude model
    if (claudeModel) {
        claudeModel.value = ai.claude?.model || 'claude-sonnet-4-20250514';
    }

    // Set z.ai model
    if (zaiModel) {
        zaiModel.value = ai.zai?.model || 'glm-4.5';
    }

    // Set z.ai URL
    if (zaiUrl) {
        zaiUrl.value = ai.zai?.base_url || 'https://api.z.ai/api/paas/v4/';
    }

    // Set Llama path
    if (llamaPath) {
        llamaPath.value = ai.llama?.model_path || '';
    }

    // Note: We don't pre-fill API keys for security reasons
    // But we show if they're configured
    if (anthropicKey) {
        anthropicKey.placeholder = ai.claude?.configured ? '(configured)' : 'sk-ant-...';
    }
    if (zaiKey) {
        zaiKey.placeholder = ai.zai?.configured ? '(configured)' : 'API Key';
    }
}

function updateAIStatus(ai) {
    if (!aiStatus) return;

    const available = ai.available_providers || [];
    const current = ai.provider;

    if (available.length === 0) {
        aiStatus.innerHTML = `
            <div class="status-warning">
                No AI providers available. Configure at least one provider below.
            </div>
        `;
        return;
    }

    const statusItems = available.map(p => {
        const names = {
            'ollama': 'Ollama',
            'claude': 'Claude',
            'zai': 'z.ai',
            'llama': 'Llama.cpp'
        };
        const isActive = p === current;
        return `<span class="status-chip ${isActive ? 'active' : ''}">${names[p] || p}${isActive ? ' (active)' : ''}</span>`;
    }).join(' ');

    aiStatus.innerHTML = `
        <div class="status-info">
            Available: ${statusItems}
        </div>
    `;
}

function updateFeaturesStatus(status) {
    // Update Translation status
    const translationEl = document.getElementById('feature-translation');
    if (translationEl) {
        updateFeatureItem(translationEl, status.translation, 'Translation');
    }

    // Update Speaker Detection status
    const speakerEl = document.getElementById('feature-speaker');
    if (speakerEl) {
        updateFeatureItem(speakerEl, status.speaker_detection, 'Speaker Detection');
    }

    // Update Semantic Search status
    const semanticEl = document.getElementById('feature-semantic');
    if (semanticEl) {
        updateFeatureItem(semanticEl, status.semantic_search, 'Semantic Search');
    }
}

function updateFeatureItem(element, featureStatus, featureName) {
    const indicator = element.querySelector('.feature-indicator');
    if (!indicator) return;

    indicator.classList.remove('loading');

    if (featureStatus?.available) {
        indicator.classList.add('available');
        indicator.classList.remove('unavailable');
        indicator.title = 'Available';
        indicator.textContent = '\u2713'; // checkmark
    } else {
        indicator.classList.add('unavailable');
        indicator.classList.remove('available');
        indicator.title = featureStatus?.error || 'Not available';
        indicator.textContent = '\u2717'; // X mark

        // Add click handler to show install instructions
        if (featureStatus?.install_cmd) {
            element.style.cursor = 'pointer';
            element.onclick = () => showFeatureDetails(featureName, featureStatus);
        }
    }
}

function showFeatureDetails(featureName, featureStatus) {
    if (!featureDetails) return;

    featureDetails.hidden = false;
    featureDetails.innerHTML = `
        <div class="feature-detail-card">
            <strong>${featureName}</strong>
            <p class="feature-error">${featureStatus.error || 'Not available'}</p>
            ${featureStatus.install_cmd ? `
                <div class="install-cmd">
                    <code>${featureStatus.install_cmd}</code>
                    <button class="copy-cmd-btn" onclick="copyInstallCmd('${featureStatus.install_cmd}')" title="Copy">Copy</button>
                </div>
            ` : ''}
        </div>
    `;
}

function copyInstallCmd(cmd) {
    navigator.clipboard.writeText(cmd).then(() => {
        // Brief visual feedback
        const btn = document.querySelector('.copy-cmd-btn');
        if (btn) {
            const original = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = original, 1500);
        }
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function populateOllamaModels(models, currentModel) {
    if (!ollamaModel) return;

    ollamaModel.innerHTML = '';

    if (!models || models.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No models available';
        ollamaModel.appendChild(option);
        return;
    }

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        if (model === currentModel) {
            option.selected = true;
        }
        ollamaModel.appendChild(option);
    });
}

async function saveAISettings() {
    try {
        settingsSave.disabled = true;
        settingsSave.textContent = 'Saving...';

        const formData = new FormData();

        // Add provider
        if (aiProvider?.value) {
            formData.append('provider', aiProvider.value);
        }

        // Add Ollama settings
        if (ollamaModel?.value) {
            formData.append('ollama_model', ollamaModel.value);
        }
        if (ollamaUrl?.value) {
            formData.append('ollama_base_url', ollamaUrl.value);
        }

        // Add Claude settings
        if (anthropicKey?.value) {
            formData.append('anthropic_api_key', anthropicKey.value);
        }
        if (claudeModel?.value) {
            formData.append('claude_model', claudeModel.value);
        }

        // Add z.ai settings
        if (zaiKey?.value) {
            formData.append('zai_api_key', zaiKey.value);
        }
        if (zaiModel?.value) {
            formData.append('zai_model', zaiModel.value);
        }
        if (zaiUrl?.value) {
            formData.append('zai_base_url', zaiUrl.value);
        }

        // Add Llama settings
        if (llamaPath?.value !== undefined) {
            formData.append('llama_model_path', llamaPath.value);
        }

        const response = await fetch('/api/settings/ai', {
            method: 'PUT',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save settings');
        }

        const result = await response.json();

        // Clear sensitive fields
        if (anthropicKey) anthropicKey.value = '';
        if (zaiKey) zaiKey.value = '';

        // Reload settings to show updated status
        await loadSettings();

        // Update status bar
        updateStatusBar();

        // Show success message
        showSettingsSuccess('Settings saved successfully');

    } catch (error) {
        console.error('Failed to save settings:', error);
        showSettingsError('Failed to save: ' + error.message);
    } finally {
        settingsSave.disabled = false;
        settingsSave.textContent = 'Save Settings';
    }
}

function showSettingsError(message) {
    if (!aiStatus) return;
    aiStatus.innerHTML = `<div class="status-error">${message}</div>`;
}

function showSettingsSuccess(message) {
    if (!aiStatus) return;
    const existingContent = aiStatus.innerHTML;
    aiStatus.innerHTML = `<div class="status-success">${message}</div>` + existingContent;
    setTimeout(() => {
        loadSettings(); // Refresh to remove success message
    }, 2000);
}

/**
 * Update the status bar with current AI provider status.
 */
async function updateStatusBar() {
    const statusDot = document.getElementById('ai-status-dot');
    const statusText = document.getElementById('ai-status-text');

    if (!statusDot || !statusText) return;

    // Set checking state
    statusDot.className = 'status-dot checking';

    try {
        const response = await fetch('/api/settings');
        if (!response.ok) throw new Error('Failed to fetch settings');

        const settings = await response.json();
        const ai = settings.ai || {};
        const available = ai.available_providers || [];
        const current = ai.provider;

        if (available.length > 0 && current) {
            statusDot.className = 'status-dot available';
            const providerNames = {
                'ollama': 'Ollama',
                'claude': 'Claude',
                'zai': 'z.ai',
                'llama': 'Llama'
            };
            statusText.textContent = `AI: ${providerNames[current] || current}`;
        } else {
            statusDot.className = 'status-dot unavailable';
            statusText.textContent = 'AI: Not configured';
        }
    } catch (error) {
        console.warn('Failed to update status bar:', error);
        statusDot.className = 'status-dot unavailable';
        statusText.textContent = 'AI: Error';
    }
}

// Note: Functions are exported to window in DOMContentLoaded callback above
