/* Libram - Main View JavaScript */

function init() {
    // Initialize view mode
    initViewMode();
    
    // Initialize search
    initSearch();
    
    // Initialize card drag and drop
    initCardDragDrop();
    
    // Initialize books per month chart
    initBooksChart();
    
    // Start time update
    updateTime();
    setInterval(updateTime, 60000);
}

// Run init when DOM is ready (or immediately if already loaded)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

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
    const form = document.querySelector('.search-box');
    
    if (searchInput && clearBtn) {
        // Prevent form submission - we're doing client-side filtering
        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });
        
        // Filter as you type
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            clearBtn.style.display = query ? 'block' : 'none';
            filterBooks(query);
        });
        
        // Clear search
        clearBtn.addEventListener('click', function() {
            searchInput.value = '';
            clearBtn.style.display = 'none';
            filterBooks('');
            searchInput.focus();
        });
    }
}

function filterBooks(query) {
    const yearSections = document.querySelectorAll('.year-section');
    
    yearSections.forEach(section => {
        const bookCards = section.querySelectorAll('.book-card');
        let visibleCount = 0;
        
        bookCards.forEach(card => {
            const title = card.dataset.title || '';
            const author = card.dataset.author || '';
            const matches = !query || title.includes(query) || author.includes(query);
            
            card.style.display = matches ? '' : 'none';
            if (matches) visibleCount++;
        });
        
        // Update year header count and visibility
        const header = section.querySelector('.year-header');
        const countSpan = section.querySelector('.entry-count');
        const content = section.querySelector('.year-content');
        
        if (query) {
            // When searching, show sections with matches, hide empty ones
            section.style.display = visibleCount > 0 ? '' : 'none';
            if (countSpan) {
                countSpan.textContent = `${visibleCount} Book${visibleCount !== 1 ? 's' : ''}`;
            }
            // Expand sections with matches
            if (visibleCount > 0 && content) {
                content.classList.add('expanded');
                const icon = section.querySelector('[id$="-icon"]');
                if (icon) icon.textContent = '▼';
            }
        } else {
            // When not searching, show all sections
            section.style.display = '';
            // Reset count from original
            const originalCount = bookCards.length;
            if (countSpan) {
                countSpan.textContent = `${originalCount} Book${originalCount !== 1 ? 's' : ''}`;
            }
        }
    });
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

/* ============================================
   CHART (BOOKS PER MONTH / AVG PAGES PER DAY / BY TYPE)
   ============================================ */
let currentChartView = 'books'; // 'books', 'pages', or 'types'
let chartDataCache = { books: null, pages: null, types: null };

async function initBooksChart() {
    const container = document.getElementById('books-chart');
    if (!container) return;
    
    try {
        const response = await fetch('/api/books-per-month');
        chartDataCache.books = await response.json();
        renderBooksChart(container, chartDataCache.books);
    } catch (error) {
        console.error('Failed to load chart data:', error);
        container.innerHTML = '<div class="chart-error">Unable to load chart</div>';
    }
}

async function toggleChartView() {
    const container = document.getElementById('books-chart');
    const titleEl = document.getElementById('chart-title');
    if (!container) return;
    
    if (currentChartView === 'books') {
        // Switch to pages per day
        currentChartView = 'pages';
        titleEl.textContent = 'Avg Pages/Day';
        
        if (!chartDataCache.pages) {
            try {
                const response = await fetch('/api/pages-per-day-by-month');
                chartDataCache.pages = await response.json();
            } catch (error) {
                console.error('Failed to load pages chart data:', error);
                return;
            }
        }
        renderPagesChart(container, chartDataCache.pages);
    } else if (currentChartView === 'pages') {
        // Switch to by type
        currentChartView = 'types';
        titleEl.textContent = 'By Type';
        
        if (!chartDataCache.types) {
            try {
                const response = await fetch('/api/books-by-type');
                chartDataCache.types = await response.json();
            } catch (error) {
                console.error('Failed to load types chart data:', error);
                return;
            }
        }
        renderTypesChart(container, chartDataCache.types);
    } else {
        // Switch to books per month
        currentChartView = 'books';
        titleEl.textContent = 'Books Per Month';
        renderBooksChart(container, chartDataCache.books);
    }
}

function renderBooksChart(container, data) {
    // Get theme colors from CSS variables
    const styles = getComputedStyle(document.documentElement);
    const barColor = styles.getPropertyValue('--chart-bar').trim() || '#667eea';
    const emptyColor = styles.getPropertyValue('--chart-empty').trim() || '#E5E7EB';
    const textColor = styles.getPropertyValue('--text-secondary').trim() || '#4B5563';
    const gridColor = styles.getPropertyValue('--chart-grid').trim() || '#c8c4d8';
    
    // Chart dimensions
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 100;
    const padding = { top: 8, right: 8, bottom: 20, left: 24 };
    
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Find max value for scaling
    const maxCount = Math.max(...data.map(d => d.count), 1);
    const yMax = Math.ceil(maxCount * 1.1) || 5; // Add 10% headroom, minimum 5
    
    // Calculate bar dimensions
    const barCount = data.length;
    const barGap = 4;
    const barWidth = (chartWidth - (barCount - 1) * barGap) / barCount;
    
    // Create SVG
    let svg = `<svg width="${width}" height="${height}" class="books-chart-svg">`;
    
    // Y-axis gridlines and labels
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
        const y = padding.top + chartHeight - (i / gridLines) * chartHeight;
        const value = Math.round((i / gridLines) * yMax);
        
        // Gridline
        svg += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" 
                      stroke="${gridColor}" stroke-width="1" />`;
        
        // Y-axis label (only show a few)
        if (i === 0 || i === gridLines || i === gridLines / 2) {
            svg += `<text x="${padding.left - 6}" y="${y + 3}" 
                          text-anchor="end" font-size="9" fill="${textColor}">${value}</text>`;
        }
    }
    
    // Bars
    data.forEach((d, i) => {
        const x = padding.left + i * (barWidth + barGap);
        const barHeight = (d.count / yMax) * chartHeight;
        const y = padding.top + chartHeight - barHeight;
        
        // Bar
        const color = d.count > 0 ? barColor : emptyColor;
        svg += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" 
                      fill="${color}" rx="2" class="chart-bar">
                  <title>${d.label} ${d.year}: ${d.count} book${d.count !== 1 ? 's' : ''}</title>
                </rect>`;
        
        // X-axis label (show every other month to avoid crowding)
        if (i % 2 === 0 || barCount <= 6) {
            svg += `<text x="${x + barWidth / 2}" y="${height - 4}" 
                          text-anchor="middle" font-size="9" fill="${textColor}">${d.label}</text>`;
        }
    });
    
    svg += '</svg>';
    container.innerHTML = svg;
}

function renderPagesChart(container, data) {
    // Get theme colors from CSS variables
    const styles = getComputedStyle(document.documentElement);
    const barColor = styles.getPropertyValue('--chart-bar-alt').trim() || '#10B981';
    const emptyColor = styles.getPropertyValue('--chart-empty').trim() || '#E5E7EB';
    const textColor = styles.getPropertyValue('--text-secondary').trim() || '#4B5563';
    const gridColor = styles.getPropertyValue('--chart-grid').trim() || '#c8c4d8';
    
    // Chart dimensions
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 100;
    const padding = { top: 8, right: 8, bottom: 20, left: 24 };
    
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Find max value for scaling
    const maxAvg = Math.max(...data.map(d => d.avg), 1);
    const yMax = Math.ceil(maxAvg * 1.1) || 50; // Add 10% headroom, minimum 50
    
    // Calculate bar dimensions
    const barCount = data.length;
    const barGap = 4;
    const barWidth = (chartWidth - (barCount - 1) * barGap) / barCount;
    
    // Create SVG
    let svg = `<svg width="${width}" height="${height}" class="books-chart-svg">`;
    
    // Y-axis gridlines and labels
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
        const y = padding.top + chartHeight - (i / gridLines) * chartHeight;
        const value = Math.round((i / gridLines) * yMax);
        
        // Gridline
        svg += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" 
                      stroke="${gridColor}" stroke-width="1" />`;
        
        // Y-axis label (only show a few)
        if (i === 0 || i === gridLines || i === gridLines / 2) {
            svg += `<text x="${padding.left - 6}" y="${y + 3}" 
                          text-anchor="end" font-size="9" fill="${textColor}">${value}</text>`;
        }
    }
    
    // Bars (use a different color - teal/green)
    data.forEach((d, i) => {
        const x = padding.left + i * (barWidth + barGap);
        const barHeight = (d.avg / yMax) * chartHeight;
        const y = padding.top + chartHeight - barHeight;
        
        // Bar
        const color = d.avg > 0 ? barColor : emptyColor;
        svg += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" 
                      fill="${color}" rx="2" class="chart-bar">
                  <title>${d.label} ${d.year}: ${d.avg} pg/day avg</title>
                </rect>`;
        
        // X-axis label (show every other month to avoid crowding)
        if (i % 2 === 0 || barCount <= 6) {
            svg += `<text x="${x + barWidth / 2}" y="${height - 4}" 
                          text-anchor="middle" font-size="9" fill="${textColor}">${d.label}</text>`;
        }
    });
    
    svg += '</svg>';
    container.innerHTML = svg;
}

function renderTypesChart(container, data) {
    // Get theme colors
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--text-secondary').trim() || '#4B5563';
    const textPrimary = styles.getPropertyValue('--text-primary').trim() || '#1F2937';
    
    // Chart dimensions
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 100;
    const padding = { top: 4, right: 8, bottom: 4, left: 8 };
    
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Find max count for scaling
    const maxCount = Math.max(...data.map(d => d.count), 1);
    
    // Calculate bar dimensions
    const barCount = data.length;
    const barGap = 6;
    const barHeight = Math.min(18, (chartHeight - (barCount - 1) * barGap) / barCount);
    const labelWidth = 60; // Space for type name on left
    const countWidth = 24; // Space for count on right
    const barMaxWidth = chartWidth - labelWidth - countWidth - 8;
    
    // Create SVG
    let svg = `<svg width="${width}" height="${height}" class="types-chart-svg">`;
    
    // Bars with labels
    data.forEach((d, i) => {
        const y = padding.top + i * (barHeight + barGap);
        const barWidth = maxCount > 0 ? (d.count / maxCount) * barMaxWidth : 0;
        
        // Type name (left)
        svg += `<text x="${padding.left}" y="${y + barHeight / 2 + 4}" 
                      font-size="11" font-weight="500" fill="${textPrimary}">${d.name}</text>`;
        
        // Bar (use the type's own color)
        if (barWidth > 0) {
            svg += `<rect x="${padding.left + labelWidth}" y="${y}" 
                          width="${barWidth}" height="${barHeight}" 
                          fill="${d.color}" rx="3" class="chart-bar">
                      <title>${d.name}: ${d.count} book${d.count !== 1 ? 's' : ''}</title>
                    </rect>`;
        }
        
        // Count (right of bar)
        svg += `<text x="${padding.left + labelWidth + barWidth + 6}" y="${y + barHeight / 2 + 4}" 
                      font-size="10" fill="${textColor}">${d.count}</text>`;
    });
    
    svg += '</svg>';
    container.innerHTML = svg;
}


// Manage dropdown
function toggleManageDropdown() {
    document.getElementById('manage-dropdown-menu').classList.toggle('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    const dropdown = document.querySelector('.manage-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        document.getElementById('manage-dropdown-menu')?.classList.remove('open');
    }
});
