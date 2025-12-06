/* Libram - Main View JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize view mode
    initViewMode();
    
    // Initialize search
    initSearch();
    
    // Initialize card drag and drop
    initCardDragDrop();
    
    // Start time update
    updateTime();
    setInterval(updateTime, 60000);
});

/* ============================================
   VIEW MODE
   ============================================ */
function initViewMode() {
    const mode = getCookie('libram_view') || 'detailed';
    setViewMode(mode, false);
}

function setViewMode(mode, save = true) {
    const container = document.getElementById('books-container');
    const headers = document.getElementById('column-headers');
    const detailedBtn = document.getElementById('view-detailed-btn');
    const compactBtn = document.getElementById('view-compact-btn');
    
    if (container) {
        container.classList.remove('detailed-mode', 'compact-mode');
        container.classList.add(mode + '-mode');
    }
    
    if (headers) {
        headers.classList.toggle('hidden', mode === 'compact');
    }
    
    if (detailedBtn) {
        detailedBtn.classList.toggle('active', mode === 'detailed');
    }
    if (compactBtn) {
        compactBtn.classList.toggle('active', mode === 'compact');
    }
    
    if (save) {
        setCookie('libram_view', mode, 365);
    }
}

/* ============================================
   YEAR COLLAPSE/EXPAND
   ============================================ */
function toggleYear(yearId) {
    const content = document.getElementById(yearId + '-content');
    const icon = document.getElementById(yearId + '-icon');
    
    if (content) {
        const isExpanded = content.classList.contains('expanded');
        content.classList.toggle('expanded');
        
        if (icon) {
            icon.textContent = isExpanded ? '▶' : '▼';
        }
    }
}

/* ============================================
   SEARCH
   ============================================ */
function initSearch() {
    const searchInput = document.querySelector('.search-box input[name="search"]');
    const clearBtn = document.querySelector('.clear-search');
    
    if (searchInput && clearBtn) {
        // Show/hide clear button
        searchInput.addEventListener('input', function() {
            clearBtn.style.display = this.value ? 'block' : 'none';
        });
        
        // Clear search
        clearBtn.addEventListener('click', function() {
            searchInput.value = '';
            clearBtn.style.display = 'none';
            searchInput.form.submit();
        });
    }
}

/* ============================================
   TIME DISPLAY
   ============================================ */
function updateTime() {
    const timeEl = document.querySelector('[data-card-id="current-time"] .stat-number');
    const dateEl = document.querySelector('[data-card-id="current-time"] .stat-label');
    
    if (timeEl && dateEl) {
        const now = new Date();
        
        let hours = now.getHours();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        const minutes = now.getMinutes().toString().padStart(2, '0');
        timeEl.textContent = `${hours}:${minutes} ${ampm}`;
        
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
        dateEl.textContent = `${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()}`;
    }
}

/* ============================================
   CARD DRAG AND DROP
   ============================================ */
function initCardDragDrop() {
    const container = document.getElementById('stats-container');
    if (!container) return;
    
    const cards = container.querySelectorAll('.stat-card');
    let draggedCard = null;
    
    cards.forEach(card => {
        card.addEventListener('dragstart', function(e) {
            draggedCard = this;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });
        
        card.addEventListener('dragend', function() {
            this.classList.remove('dragging');
            cards.forEach(c => c.classList.remove('drag-over'));
            draggedCard = null;
            saveCardOrder();
        });
        
        card.addEventListener('dragover', function(e) {
            e.preventDefault();
            if (this !== draggedCard) {
                this.classList.add('drag-over');
            }
        });
        
        card.addEventListener('dragleave', function() {
            this.classList.remove('drag-over');
        });
        
        card.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            if (draggedCard && this !== draggedCard) {
                const allCards = [...container.querySelectorAll('.stat-card')];
                const draggedIdx = allCards.indexOf(draggedCard);
                const targetIdx = allCards.indexOf(this);
                
                if (draggedIdx < targetIdx) {
                    this.parentNode.insertBefore(draggedCard, this.nextSibling);
                } else {
                    this.parentNode.insertBefore(draggedCard, this);
                }
            }
        });
    });
}

function saveCardOrder() {
    const cards = document.querySelectorAll('#stats-container .stat-card');
    const order = [...cards].map(c => c.dataset.cardId);
    
    fetch('/settings/api/card-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: order })
    });
}

/* ============================================
   COOKIE UTILITIES
   ============================================ */
function setCookie(name, value, days) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/';
}

function getCookie(name) {
    return document.cookie.split('; ').reduce((r, v) => {
        const parts = v.split('=');
        return parts[0] === name ? decodeURIComponent(parts[1]) : r;
    }, '');
}
