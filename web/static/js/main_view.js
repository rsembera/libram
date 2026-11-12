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
const COMPACT_ONLY_BREAKPOINT = 1200;

function initViewMode() {
    // Force compact on smaller screens regardless of saved preference
    if (window.innerWidth <= COMPACT_ONLY_BREAKPOINT) {
        setViewMode('compact', false);
    } else {
        const mode = getCookie('libram_view') || 'detailed';
        setViewMode(mode, false);
    }
}

// Re-check view mode on resize
window.addEventListener('resize', function() {
    if (window.innerWidth <= COMPACT_ONLY_BREAKPOINT) {
        setViewMode('compact', false);
    }
});

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
        
        // Page opened with ?search=... : apply it
        if (searchInput.value.trim()) {
            filterBooks(searchInput.value.toLowerCase().trim());
        }
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
        const countSpan = section.querySelector('.year-book-count');
        const content = section.querySelector('.year-content');
        
        if (query) {
            // When searching, show sections with matches, hide empty ones
            section.style.display = visibleCount > 0 ? '' : 'none';
            if (countSpan) {
                countSpan.textContent = `– ${visibleCount} Book${visibleCount !== 1 ? 's' : ''}`;
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
                countSpan.textContent = `– ${originalCount} Book${originalCount !== 1 ? 's' : ''}`;
            }
        }
    });
}

/* ============================================
   CARD DRAG AND DROP
   ============================================ */
// Track initial card order to detect actual changes
let initialCardOrder = null;

function initCardDragDrop() {
    const container = document.getElementById('stats-container');
    if (!container) return;
    
    const cards = container.querySelectorAll('.stat-card');
    
    // Capture initial order for change detection
    initialCardOrder = [...cards].map(c => c.dataset.cardId).join(',');
    
    // Disable drag-drop on touch devices or narrow screens
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const isNarrowScreen = window.innerWidth <= 768;
    
    if (isTouchDevice || isNarrowScreen) {
        // Remove draggable attribute on mobile/tablet
        cards.forEach(card => {
            card.removeAttribute('draggable');
        });
        return;
    }
    
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
    const orderStr = order.join(',');
    
    // Only save if order actually changed
    if (orderStr === initialCardOrder) return;
    
    initialCardOrder = orderStr;  // Update baseline
    
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
   CHART (BOOKS PER MONTH / PAGES PER MONTH / AVG PAGES PER DAY / BY TYPE / BY RATING)
   ============================================ */
// The chart card cycles through these views in order (toggle button).
// Each view's data is fetched the first time it is shown, then cached.
const CHART_VIEWS = [
    { key: 'books',      title: 'Books Per Month', url: '/api/books-per-month',         render: renderBooksChart },
    { key: 'pagesmonth', title: 'Pages Per Month', url: '/api/pages-per-month',         render: renderPagesPerMonthChart },
    { key: 'pages',      title: 'Avg Pages/Day',   url: '/api/pages-per-day-by-month',  render: renderPagesChart },
    { key: 'types',      title: 'By Type',         url: '/api/books-by-type',           render: renderTypesChart },
    { key: 'ratings',    title: 'By Rating',       url: '/api/books-by-rating',         render: renderRatingsChart },
];
let currentChartIndex = 0;
const chartDataCache = {};

async function loadChartData(view) {
    if (!chartDataCache[view.key]) {
        const response = await fetch(view.url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        chartDataCache[view.key] = await response.json();
    }
    return chartDataCache[view.key];
}

async function initBooksChart() {
    const container = document.getElementById('books-chart');
    if (!container) return;
    
    const view = CHART_VIEWS[currentChartIndex];
    try {
        view.render(container, await loadChartData(view));
    } catch (error) {
        console.error('Failed to load chart data:', error);
        container.innerHTML = '<div class="chart-error">Unable to load chart</div>';
    }
}

async function toggleChartView() {
    const container = document.getElementById('books-chart');
    const titleEl = document.getElementById('chart-title');
    if (!container) return;
    
    const nextIndex = (currentChartIndex + 1) % CHART_VIEWS.length;
    const view = CHART_VIEWS[nextIndex];
    
    let data;
    try {
        data = await loadChartData(view);
    } catch (error) {
        console.error(`Failed to load ${view.key} chart data:`, error);
        return;  // Stay on the current view
    }
    
    currentChartIndex = nextIndex;
    titleEl.textContent = view.title;
    view.render(container, data);
}

// Text from the database (type names) goes into SVG markup built as a string
function escapeXml(value) {
    return String(value).replace(/[&<>"']/g, ch => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
    ));
}

function chartColors() {
    const styles = getComputedStyle(document.documentElement);
    const get = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
    return {
        get,
        empty: get('--chart-empty', '#E5E7EB'),
        text: get('--text-secondary', '#4B5563'),
        textPrimary: get('--text-primary', '#1F2937'),
        grid: get('--chart-grid', '#c8c4d8'),
    };
}

/**
 * Vertical bar chart with one bar per month (the three "per month" views).
 *
 * options:
 *   valueKey    - field of each data row to plot ('count', 'pages', 'avg')
 *   barColor    - fill for non-zero bars
 *   leftPadding - room for y-axis labels (wider for large numbers)
 *   formatValue - formats y-axis labels (default: plain number)
 *   tooltip     - (row) => text after "Mon YYYY: " in the hover tooltip
 */
function renderMonthlyBarChart(container, data, options) {
    const colors = chartColors();
    const formatValue = options.formatValue || (v => v);
    
    // Chart dimensions
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 100;
    const padding = { top: 8, right: 8, bottom: 20, left: options.leftPadding || 24 };
    
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Find max value for scaling (10% headroom)
    const maxValue = Math.max(...data.map(d => d[options.valueKey]), 1);
    const yMax = Math.ceil(maxValue * 1.1);
    
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
                      stroke="${colors.grid}" stroke-width="1" />`;
        
        // Y-axis label (only show a few)
        if (i === 0 || i === gridLines || i === gridLines / 2) {
            svg += `<text x="${padding.left - 6}" y="${y + 3}" 
                          text-anchor="end" font-size="9" fill="${colors.text}">${formatValue(value)}</text>`;
        }
    }
    
    // Bars
    data.forEach((d, i) => {
        const value = d[options.valueKey];
        const x = padding.left + i * (barWidth + barGap);
        const barHeight = (value / yMax) * chartHeight;
        const y = padding.top + chartHeight - barHeight;
        
        // Bar
        const color = value > 0 ? options.barColor : colors.empty;
        svg += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" 
                      fill="${color}" rx="2" class="chart-bar">
                  <title>${d.label} ${d.year}: ${options.tooltip(d)}</title>
                </rect>`;
        
        // X-axis label (show every other month to avoid crowding)
        if (i % 2 === 0 || barCount <= 6) {
            svg += `<text x="${x + barWidth / 2}" y="${height - 4}" 
                          text-anchor="middle" font-size="9" fill="${colors.text}">${d.label}</text>`;
        }
    });
    
    svg += '</svg>';
    container.innerHTML = svg;
}

function renderBooksChart(container, data) {
    renderMonthlyBarChart(container, data, {
        valueKey: 'count',
        barColor: chartColors().get('--chart-bar', '#667eea'),
        tooltip: d => `${d.count} book${d.count !== 1 ? 's' : ''}`,
    });
}

function renderPagesPerMonthChart(container, data) {
    // Shares the primary bar color with Books Per Month; the two views are
    // never shown at the same time, and the title makes the view clear.
    // Wider left padding for the larger numbers.
    renderMonthlyBarChart(container, data, {
        valueKey: 'pages',
        barColor: chartColors().get('--chart-bar', '#667eea'),
        leftPadding: 36,
        formatValue: v => v.toLocaleString(),
        tooltip: d => `${d.pages.toLocaleString()} pages`,
    });
}

function renderPagesChart(container, data) {
    renderMonthlyBarChart(container, data, {
        valueKey: 'avg',
        barColor: chartColors().get('--chart-bar-alt', '#10B981'),
        tooltip: d => `${d.avg} pg/day avg`,
    });
}

/**
 * Horizontal bar chart: a name on the left, a bar, and the count after it
 * (By Type and By Rating). colorFor(row) returns each bar's fill.
 */
function renderHorizontalBarChart(container, data, colorFor) {
    const colors = chartColors();
    
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
    const labelWidth = 60; // Space for name on left
    const countWidth = 24; // Space for count on right
    const barMaxWidth = chartWidth - labelWidth - countWidth - 8;
    
    // Create SVG
    let svg = `<svg width="${width}" height="${height}" class="types-chart-svg">`;
    
    // Bars with labels
    data.forEach((d, i) => {
        const y = padding.top + i * (barHeight + barGap);
        const barWidth = (d.count / maxCount) * barMaxWidth;
        const name = escapeXml(d.name);
        
        // Name (left)
        svg += `<text x="${padding.left}" y="${y + barHeight / 2 + 4}" 
                      font-size="11" font-weight="500" fill="${colors.textPrimary}">${name}</text>`;
        
        // Bar
        if (barWidth > 0) {
            svg += `<rect x="${padding.left + labelWidth}" y="${y}" 
                          width="${barWidth}" height="${barHeight}" 
                          fill="${escapeXml(colorFor(d))}" rx="3" class="chart-bar">
                      <title>${name}: ${d.count} book${d.count !== 1 ? 's' : ''}</title>
                    </rect>`;
        }
        
        // Count (right of bar)
        svg += `<text x="${padding.left + labelWidth + barWidth + 6}" y="${y + barHeight / 2 + 4}" 
                      font-size="10" fill="${colors.text}">${d.count}</text>`;
    });
    
    svg += '</svg>';
    container.innerHTML = svg;
}

function renderTypesChart(container, data) {
    // Each bar uses the type's own color
    renderHorizontalBarChart(container, data, d => d.color);
}

function renderRatingsChart(container, data) {
    // Rating tier colors match the rating star CSS classes, including any
    // custom colors set for the 5 and 1 tiers via CSS variables.
    // Rows arrive ordered 5 down to 1 from the API.
    const colors = chartColors();
    const ratingColors = {
        5: colors.get('--rating-5-star', '#10B981'),
        4: '#F59E0B',
        3: '#9CA3AF',
        2: '#B8860B',
        1: colors.get('--rating-1-star', '#1F2937'),
    };
    renderHorizontalBarChart(container, data, d => ratingColors[d.rating] || colors.text);
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
