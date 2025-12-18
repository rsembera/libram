/* Libram - Settings JavaScript */

// Track current background for delete functionality
let currentBackgroundValue = '';
let userBackgrounds = [];

function saveTimeout() {
    const timeout = document.getElementById('session-timeout').value;
    
    fetch('/settings/api/timeout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timeout: timeout })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showTimeoutSaved();
        }
    });
}

function showTimeoutSaved() {
    // Remove any existing saved indicator
    const existing = document.querySelector('.timeout-saved');
    if (existing) existing.remove();
    
    // Show brief "Saved" confirmation next to dropdown
    const select = document.getElementById('session-timeout');
    const saved = document.createElement('span');
    saved.innerHTML = '<i class="ph ph-check"></i> Saved';
    saved.className = 'timeout-saved';
    saved.style.cssText = 'color: var(--accent-primary); font-size: 0.85rem; margin-left: 0.5rem; opacity: 1; transition: opacity 0.3s;';
    select.parentNode.appendChild(saved);
    
    // Fade out and remove after 2 seconds
    setTimeout(() => {
        saved.style.opacity = '0';
        setTimeout(() => saved.remove(), 300);
    }, 2000);
}

// ============================================================================
// CARD POSITION MANAGEMENT
// ============================================================================

const DEFAULT_CARD_ORDER = ['pages', 'reading-chart', 'navigation'];
const CARD_NAMES = {
    'pages': 'Pages Card',
    'reading-chart': 'Reading Chart',
    'navigation': 'Navigation'
};

// Track current order so we know what changed
let currentCardOrder = [...DEFAULT_CARD_ORDER];

function initCardPositions() {
    // Get current order from data attribute or use default
    const container = document.querySelector('[data-card-order]');
    
    if (container) {
        const orderStr = container.dataset.cardOrder;
        if (orderStr) {
            currentCardOrder = orderStr.split(',');
        }
    }
    
    // Set dropdown values
    for (let i = 0; i < 3; i++) {
        const select = document.getElementById(`card-position-${i + 1}`);
        if (select && currentCardOrder[i]) {
            select.value = currentCardOrder[i];
        }
    }
}

function handleCardPositionChange(position) {
    const select = document.getElementById(`card-position-${position + 1}`);
    const newCardId = select.value;
    const oldCardId = currentCardOrder[position];
    
    // If selecting the same card, do nothing
    if (newCardId === oldCardId) return;
    
    // Find where the new card currently is
    const swapPosition = currentCardOrder.indexOf(newCardId);
    
    if (swapPosition !== -1) {
        // Swap: put the old card into the position where the new card was
        currentCardOrder[swapPosition] = oldCardId;
        document.getElementById(`card-position-${swapPosition + 1}`).value = oldCardId;
    }
    
    // Update our tracked order
    currentCardOrder[position] = newCardId;
    
    // Save the new order
    fetch('/settings/api/card-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: currentCardOrder })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            showCardOrderSaved();
        }
    });
}

function showCardOrderSaved() {
    // Remove any existing saved indicator
    const existing = document.querySelector('.card-order-saved');
    if (existing) existing.remove();
    
    // Show brief "Saved" confirmation
    const grid = document.querySelector('.card-position-grid');
    if (!grid) return;
    
    const saved = document.createElement('div');
    saved.innerHTML = '<i class="ph ph-check"></i> Layout saved';
    saved.className = 'card-order-saved';
    saved.style.cssText = 'color: var(--accent-primary); font-size: 0.85rem; margin-top: 0.75rem; opacity: 1; transition: opacity 0.3s;';
    grid.appendChild(saved);
    
    // Fade out and remove after 2 seconds
    setTimeout(() => {
        saved.style.opacity = '0';
        setTimeout(() => saved.remove(), 300);
    }, 2000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initCardPositions();
});

// ============================================================================
// THEME DROPDOWN
// ============================================================================

const themeNames = {
    'witching-hour': 'The Witching Hour',
    'crimson-veil': 'Crimson Veil',
    'hardboiled': 'Hardboiled',
    'terminal': 'Terminal',
    'grimoire': 'Grimoire',
    'wasteland': 'Wasteland',
    'lost-world': 'Lost World',
    'nautilus': 'Nautilus'
};

function toggleThemeDropdown() {
    const dropdown = document.getElementById('theme-dropdown');
    dropdown.classList.toggle('open');
    // Close other dropdowns
    document.getElementById('background-dropdown').classList.remove('open');
    document.getElementById('font-dropdown').classList.remove('open');
    const borderDropdown = document.getElementById('border-style-dropdown');
    if (borderDropdown) borderDropdown.classList.remove('open');
}

function selectTheme(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    // Update selected text
    document.getElementById('theme-selected-text').textContent = text;
    
    // Update selected state
    document.querySelectorAll('#theme-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Close dropdown
    document.getElementById('theme-dropdown').classList.remove('open');
    
    // Save to server
    fetch('/settings/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: value })
    }).then(() => {
        // Update data-theme attribute for immediate preview
        document.documentElement.setAttribute('data-theme', value);
    });
}

// ============================================================================
// FONT DROPDOWN
// ============================================================================

function toggleFontDropdown() {
    const dropdown = document.getElementById('font-dropdown');
    dropdown.classList.toggle('open');
    // Close other dropdowns
    document.getElementById('background-dropdown').classList.remove('open');
    document.getElementById('theme-dropdown').classList.remove('open');
    const borderDropdown = document.getElementById('border-style-dropdown');
    if (borderDropdown) borderDropdown.classList.remove('open');
}

function selectFont(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    // Update selected text with the appropriate font class
    const selectedText = document.getElementById('font-selected-text');
    selectedText.textContent = text;
    selectedText.className = 'font-option-' + value;
    
    // Update selected state
    document.querySelectorAll('#font-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Close dropdown
    document.getElementById('font-dropdown').classList.remove('open');
    
    // Save to server
    fetch('/settings/api/font', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: value })
    }).then(() => {
        // Update body class for immediate preview
        document.body.className = document.body.className
            .replace(/\bfont-(?!size)[\w-]+\b/g, '')
            .trim() + ' font-' + value;
    });
}

function selectFontSize(size) {
    // Update active state
    document.querySelectorAll('.font-size-toggle .size-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.size === size);
    });
    
    // Save to server
    fetch('/settings/api/font-size', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ size: size })
    }).then(() => {
        // Update html element class for immediate preview
        document.documentElement.className = document.documentElement.className
            .replace(/\bfont-size-\w+\b/g, '')
            .trim() + ' font-size-' + size;
    });
}

// ============================================================================
// BORDER STYLE DROPDOWN
// ============================================================================

function toggleBorderStyleDropdown() {
    const dropdown = document.getElementById('border-style-dropdown');
    dropdown.classList.toggle('open');
    // Close other dropdowns
    document.getElementById('background-dropdown').classList.remove('open');
    document.getElementById('theme-dropdown').classList.remove('open');
    document.getElementById('font-dropdown').classList.remove('open');
}

function selectBorderStyle(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    // Update selected text
    document.getElementById('border-style-selected-text').textContent = text;
    
    // Update selected state
    document.querySelectorAll('#border-style-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Close dropdown
    document.getElementById('border-style-dropdown').classList.remove('open');
    
    // Save to server
    fetch('/settings/api/border-style', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: value })
    }).then(() => {
        // Update html element attribute for immediate preview
        document.documentElement.dataset.borderStyle = value;
    });
}

// ============================================================================
// BACKGROUND DROPDOWN
// ============================================================================

async function loadBackgroundOptions() {
    try {
        const response = await fetch('/settings/api/backgrounds');
        const data = await response.json();
        
        const menu = document.getElementById('background-dropdown-menu');
        menu.innerHTML = '';
        
        // Store user backgrounds for delete check
        userBackgrounds = data.user || [];
        
        // Add "Theme Default" option
        const defaultOption = document.createElement('div');
        defaultOption.className = 'custom-dropdown-option';
        defaultOption.dataset.value = '';
        defaultOption.innerHTML = '<span class="bg-preview bg-preview-default"></span>Theme Default';
        defaultOption.onclick = () => selectBackground(defaultOption);
        if (!currentBackgroundValue) {
            defaultOption.classList.add('selected');
        }
        menu.appendChild(defaultOption);
        
        // Add user backgrounds
        if (data.user && data.user.length > 0) {
            const userLabel = document.createElement('div');
            userLabel.className = 'dropdown-group-label';
            userLabel.textContent = 'My Backgrounds';
            menu.appendChild(userLabel);
            
            data.user.forEach(bg => {
                const option = document.createElement('div');
                option.className = 'custom-dropdown-option';
                option.dataset.value = bg.value;
                option.dataset.filename = bg.filename;
                const thumbUrl = `/static/user_backgrounds/${bg.filename}`;
                option.innerHTML = `<span class="bg-preview bg-preview-image" style="background-image: url('${thumbUrl}')"></span>${bg.name}`;
                option.onclick = () => selectBackground(option);
                if (bg.value === currentBackgroundValue) {
                    option.classList.add('selected');
                }
                menu.appendChild(option);
            });
        }
        
        // Update selected text
        updateBackgroundSelectedText();
        updateDeleteButtonVisibility();
        
    } catch (error) {
        console.error('Failed to load background options:', error);
    }
}

function toggleBackgroundDropdown() {
    const dropdown = document.getElementById('background-dropdown');
    dropdown.classList.toggle('open');
    // Close other dropdowns
    document.getElementById('font-dropdown').classList.remove('open');
    document.getElementById('theme-dropdown').classList.remove('open');
    const borderDropdown = document.getElementById('border-style-dropdown');
    if (borderDropdown) borderDropdown.classList.remove('open');
}

function selectBackground(element) {
    const value = element.dataset.value;
    currentBackgroundValue = value;
    
    // Update selected state
    document.querySelectorAll('#background-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Update selected text
    updateBackgroundSelectedText();
    
    // Close dropdown
    document.getElementById('background-dropdown').classList.remove('open');
    
    // Update delete button visibility
    updateDeleteButtonVisibility();
    
    // Save to server
    fetch('/settings/api/background', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: value })
    }).then(() => {
        // Apply background immediately
        applyBackground(value);
    });
}

function updateBackgroundSelectedText() {
    const selectedOption = document.querySelector('#background-dropdown .custom-dropdown-option.selected');
    const selectedText = document.getElementById('background-selected-text');
    
    if (selectedOption) {
        // Get just the text, not the preview span
        const text = selectedOption.textContent.trim();
        selectedText.textContent = text;
    }
}

function applyBackground(value) {
    const body = document.body;
    
    // Remove existing background styles
    body.style.backgroundImage = '';
    body.style.backgroundSize = '';
    body.style.backgroundPosition = '';
    body.style.backgroundAttachment = '';
    
    if (value && value.startsWith('user:')) {
        // User uploaded image
        const filename = value.substring(5);
        body.style.backgroundImage = `url('/static/user_backgrounds/${filename}')`;
        body.style.backgroundSize = 'cover';
        body.style.backgroundPosition = 'center';
        body.style.backgroundAttachment = 'fixed';
    }
    // If empty or no value, theme background applies via CSS
}

function updateDeleteButtonVisibility() {
    const deleteBtn = document.getElementById('delete-bg-button');
    if (currentBackgroundValue && currentBackgroundValue.startsWith('user:')) {
        deleteBtn.classList.remove('hidden');
    } else {
        deleteBtn.classList.add('hidden');
    }
}

async function deleteBackground() {
    if (!currentBackgroundValue || !currentBackgroundValue.startsWith('user:')) {
        return;
    }
    
    const filename = currentBackgroundValue.substring(5);
    
    if (!confirm(`Delete background "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/settings/delete_background', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Reset to theme default
            currentBackgroundValue = '';
            await loadBackgroundOptions();
            applyBackground('');
            
            // Save to server
            fetch('/settings/api/background', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ style: '' })
            });
            
            showUploadStatus('✓ Background deleted', 'success');
        } else {
            showUploadStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showUploadStatus('Error deleting background', 'error');
    }
}

// ============================================================================
// BACKGROUND UPLOAD
// ============================================================================

function setupUploadHandler() {
    const fileInput = document.getElementById('background-upload');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const filenameSpan = document.getElementById('upload-filename');
            const uploadBtn = document.getElementById('upload-button');
            
            if (this.files && this.files[0]) {
                filenameSpan.textContent = this.files[0].name;
                uploadBtn.classList.remove('hidden');
            } else {
                filenameSpan.textContent = '';
                uploadBtn.classList.add('hidden');
            }
        });
    }
}

async function uploadBackground() {
    const fileInput = document.getElementById('background-upload');
    
    if (!fileInput.files || !fileInput.files[0]) {
        showUploadStatus('No file selected', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('background', file);
    
    showUploadStatus('Uploading...', 'info');
    
    try {
        const response = await fetch('/settings/upload_background', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showUploadStatus('✓ Background uploaded!', 'success');
            
            // Clear file input
            fileInput.value = '';
            document.getElementById('upload-filename').textContent = '';
            document.getElementById('upload-button').classList.add('hidden');
            
            // Reload backgrounds and select the new one
            currentBackgroundValue = 'user:' + result.filename;
            await loadBackgroundOptions();
            applyBackground(currentBackgroundValue);
            
            // Save to server
            fetch('/settings/api/background', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ style: currentBackgroundValue })
            });
        } else {
            showUploadStatus('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showUploadStatus('Upload failed', 'error');
    }
}

function showUploadStatus(message, type) {
    const statusDiv = document.getElementById('upload-status');
    statusDiv.textContent = message;
    statusDiv.className = 'upload-status ' + type;
    statusDiv.style.display = 'block';
    
    // Hide after 3 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Close dropdowns when clicking outside
document.addEventListener('click', function(e) {
    const fontDropdown = document.getElementById('font-dropdown');
    const bgDropdown = document.getElementById('background-dropdown');
    const themeDropdown = document.getElementById('theme-dropdown');
    
    if (fontDropdown && !fontDropdown.contains(e.target)) {
        fontDropdown.classList.remove('open');
    }
    if (bgDropdown && !bgDropdown.contains(e.target)) {
        bgDropdown.classList.remove('open');
    }
    if (themeDropdown && !themeDropdown.contains(e.target)) {
        themeDropdown.classList.remove('open');
    }
});

// Rating color preset picker
function selectRatingColor(rating, element) {
    const color = element.dataset.color;
    const name = element.dataset.name;
    const picker = document.getElementById('color-picker-' + rating);
    
    // Update selected state
    picker.querySelectorAll('.color-preset').forEach(btn => {
        btn.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Save to server (color and name)
    fetch('/settings/api/rating-color', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: rating, color: color, name: name })
    }).then(() => {
        // Update CSS variable for immediate preview
        const varName = rating === 5 ? '--rating-5-star' : '--rating-1-star';
        document.documentElement.style.setProperty(varName, color);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme dropdown
    const selectedThemeOption = document.querySelector('#theme-dropdown .custom-dropdown-option.selected');
    if (selectedThemeOption) {
        document.getElementById('theme-selected-text').textContent = selectedThemeOption.textContent.trim();
    }
    
    // Initialize font dropdown
    const selectedFontOption = document.querySelector('#font-dropdown .custom-dropdown-option.selected');
    if (selectedFontOption) {
        const selectedText = document.getElementById('font-selected-text');
        selectedText.textContent = selectedFontOption.textContent.trim();
        selectedText.className = 'font-option-' + selectedFontOption.dataset.value;
    }
    
    // Initialize background dropdown
    if (window.currentSettings) {
        currentBackgroundValue = window.currentSettings.backgroundStyle || '';
    }
    loadBackgroundOptions();
    setupUploadHandler();
});

// About Modal functions
function showAboutModal() {
    const modal = document.getElementById('about-modal');
    modal.style.display = 'flex';
}

function closeAboutModal() {
    const modal = document.getElementById('about-modal');
    modal.style.display = 'none';
}

// Astrology toggle
function toggleAstrology(show) {
    fetch('/settings/api/show-astrology', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ show: show })
    });
}

// Close modal on backdrop click
document.addEventListener('click', function(e) {
    const modal = document.getElementById('about-modal');
    if (e.target === modal) {
        closeAboutModal();
    }
});
