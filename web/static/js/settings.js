/* Libram - Settings JavaScript */

function saveCardStyle() {
    const style = document.getElementById('card-style').value;
    
    fetch('/settings/api/card-style', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: style })
    }).then(() => {
        // Update body class for immediate preview
        document.body.className = document.body.className
            .replace(/\b(strait-laced|garden-path|ocean-breeze|sunset-glow|tutti-frutti)\b/g, '')
            .trim() + ' ' + style;
    });
}

function saveBackground() {
    const style = document.getElementById('background-style').value;
    
    fetch('/settings/api/background', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style: style })
    }).then(() => {
        // Update body class for immediate preview
        document.body.className = document.body.className
            .replace(/\bbg-[\w-]+\b/g, '')
            .trim() + ' bg-' + style;
    });
}

function saveTimeout() {
    const timeout = document.getElementById('session-timeout').value;
    
    fetch('/settings/api/timeout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timeout: timeout })
    });
}

// Font dropdown functions
function toggleFontDropdown() {
    const dropdown = document.getElementById('font-dropdown');
    dropdown.classList.toggle('open');
}

function selectFont(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    // Update selected text with the appropriate font class
    const selectedText = document.getElementById('font-selected-text');
    selectedText.textContent = text;
    selectedText.className = 'font-option-' + value;
    
    // Update selected state
    document.querySelectorAll('.custom-dropdown-option').forEach(opt => {
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

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('font-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// Initialize font dropdown selected text on page load
document.addEventListener('DOMContentLoaded', function() {
    const selectedOption = document.querySelector('.custom-dropdown-option.selected');
    if (selectedOption) {
        const selectedText = document.getElementById('font-selected-text');
        selectedText.textContent = selectedOption.textContent.trim();
        selectedText.className = 'font-option-' + selectedOption.dataset.value;
    }
});
