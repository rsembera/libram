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
    });
}

// ============================================================================
// CARD STYLE DROPDOWN
// ============================================================================

function toggleCardStyleDropdown() {
    const dropdown = document.getElementById('card-style-dropdown');
    dropdown.classList.toggle('open');
    // Close other dropdowns
    document.getElementById('background-dropdown').classList.remove('open');
    document.getElementById('font-dropdown').classList.remove('open');
}

function selectCardStyle(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    // Update selected text
    document.getElementById('card-style-selected-text').textContent = text;
    
    // Update selected state
    document.querySelectorAll('#card-style-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Close dropdown
    document.getElementById('card-style-dropdown').classList.remove('open');
    
    // Save to server
    fetch('/settings/api/card-style', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: value })
    }).then(() => {
        // Update body class for immediate preview
        document.body.className = document.body.className
            .replace(/\b(strait-laced|garden-path|ocean-breeze|sunset-glow|tutti-frutti)\b/g, '')
            .trim() + ' ' + value;
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
    document.getElementById('card-style-dropdown').classList.remove('open');
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
            .replace(/\bfont-[\w-]+\b/g, '')
            .trim() + ' font-' + value;
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
        
        // Add solid colors
        if (data.solid && data.solid.length > 0) {
            const solidLabel = document.createElement('div');
            solidLabel.className = 'dropdown-group-label';
            solidLabel.textContent = 'Solid Colors';
            menu.appendChild(solidLabel);
            
            data.solid.forEach(bg => {
                const option = document.createElement('div');
                option.className = 'custom-dropdown-option';
                option.dataset.value = bg.value;
                option.innerHTML = `<span class="bg-preview bg-preview-${bg.value}"></span>${bg.name}`;
                option.onclick = () => selectBackground(option);
                if (bg.value === currentBackgroundValue) {
                    option.classList.add('selected');
                }
                menu.appendChild(option);
            });
        }
        
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
    document.getElementById('card-style-dropdown').classList.remove('open');
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
    
    // Remove existing background classes and styles
    body.className = body.className.replace(/\bbg-[\w-]+\b/g, '').trim();
    body.style.backgroundImage = '';
    body.style.backgroundSize = '';
    body.style.backgroundPosition = '';
    body.style.backgroundAttachment = '';
    
    if (value.startsWith('user:')) {
        // User uploaded image
        const filename = value.substring(5);
        body.style.backgroundImage = `url('/static/user_backgrounds/${filename}')`;
        body.style.backgroundSize = 'cover';
        body.style.backgroundPosition = 'center';
        body.style.backgroundAttachment = 'fixed';
    } else {
        // Solid color
        body.className = body.className + ' bg-' + value;
    }
}

function updateDeleteButtonVisibility() {
    const deleteBtn = document.getElementById('delete-bg-button');
    if (currentBackgroundValue.startsWith('user:')) {
        deleteBtn.classList.remove('hidden');
    } else {
        deleteBtn.classList.add('hidden');
    }
}

async function deleteBackground() {
    if (!currentBackgroundValue.startsWith('user:')) {
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
            // Reset to default background
            currentBackgroundValue = 'suit-grey';
            await loadBackgroundOptions();
            applyBackground('suit-grey');
            
            // Save to server
            fetch('/settings/api/background', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ style: 'suit-grey' })
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
    const cardStyleDropdown = document.getElementById('card-style-dropdown');
    
    if (fontDropdown && !fontDropdown.contains(e.target)) {
        fontDropdown.classList.remove('open');
    }
    if (bgDropdown && !bgDropdown.contains(e.target)) {
        bgDropdown.classList.remove('open');
    }
    if (cardStyleDropdown && !cardStyleDropdown.contains(e.target)) {
        cardStyleDropdown.classList.remove('open');
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize card style dropdown
    const selectedCardStyleOption = document.querySelector('#card-style-dropdown .custom-dropdown-option.selected');
    if (selectedCardStyleOption) {
        document.getElementById('card-style-selected-text').textContent = selectedCardStyleOption.textContent.trim();
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
        currentBackgroundValue = window.currentSettings.backgroundStyle || 'suit-grey';
    }
    loadBackgroundOptions();
    setupUploadHandler();
});
