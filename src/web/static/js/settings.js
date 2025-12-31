/**
 * Settings modal functionality
 */

// State
let currentSettings = null;

// Elements
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const settingsModalClose = document.getElementById('settings-modal-close');
const settingsCancel = document.getElementById('settings-cancel');
const settingsSave = document.getElementById('settings-save');
const aiStatus = document.getElementById('ai-status');
const aiProvider = document.getElementById('ai-provider');
const ollamaModel = document.getElementById('ollama-model');
const ollamaUrl = document.getElementById('ollama-url');
const anthropicKey = document.getElementById('anthropic-key');
const claudeModel = document.getElementById('claude-model');
const zaiKey = document.getElementById('zai-key');
const zaiUrl = document.getElementById('zai-url');
const llamaPath = document.getElementById('llama-path');
const translationStatus = document.getElementById('translation-status');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupSettingsListeners();
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
    settingsSave?.addEventListener('click', saveSettings);

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
        const response = await fetch('/api/settings');
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Settings API not found. Please restart the server.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to load settings');
        }

        currentSettings = await response.json();
        populateSettings(currentSettings);
    } catch (error) {
        console.error('Failed to load settings:', error);
        showSettingsError(error.message);
    }
}

function populateSettings(settings) {
    const ai = settings.ai || {};
    const translation = settings.translation || {};

    // Show status
    updateAIStatus(ai);
    updateTranslationStatus(translation);

    // Set current provider
    if (aiProvider) {
        aiProvider.value = ai.provider || 'ollama';
    }

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

    // Set z.ai URL
    if (zaiUrl) {
        zaiUrl.value = ai.zai?.base_url || 'https://api.z.ai/v1';
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

function updateTranslationStatus(translation) {
    if (!translationStatus) return;

    if (translation.available) {
        translationStatus.innerHTML = `
            <div class="status-success">Translation service available (argostranslate)</div>
        `;
    } else {
        const error = translation.error || 'Not available';
        translationStatus.innerHTML = `
            <div class="status-warning">
                ${error}
            </div>
        `;
    }
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

async function saveSettings() {
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

// Export for use in other modules
window.openSettings = openSettings;
