/**
 * Date Picker Component - Libram
 * Grid-based picker optimized for touch and mouse
 * Adapted from EdgeCase Equalizer
 * 
 * Usage:
 *   initDatePicker('containerId', { onSelect: (date) => {} })
 */

// ============================================================
// CONFIGURATION
// ============================================================

const PICKER_CONFIG = {
    months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    monthsFull: ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December'],
    daysOfWeek: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'],
    yearRangeStart: 1950,
    yearRangeEnd: 2040
};

// ============================================================
// DATE PICKER CLASS
// ============================================================

class DatePicker {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            onSelect: options.onSelect || (() => {}),
            initialDate: options.initialDate || null,
            placeholder: options.placeholder || 'Select date',
            allowClear: options.allowClear || false
        };
        
        this.selectedDate = this.options.initialDate;
        if (this.selectedDate) {
            this.viewYear = this.selectedDate.getFullYear();
            this.viewMonth = this.selectedDate.getMonth();
        } else {
            const now = new Date();
            this.viewYear = now.getFullYear();
            this.viewMonth = now.getMonth();
        }
        this.currentView = 'days';
        this.yearsPageStart = Math.floor(this.viewYear / 16) * 16;
        
        this.render();
        this.attachEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="picker-wrapper">
                <div class="picker-display" tabindex="0">
                    <span class="picker-display-value"></span>
                    <svg class="picker-display-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                </div>
                <div class="picker-dropdown"></div>
            </div>
        `;
        
        this.display = this.container.querySelector('.picker-display');
        this.displayValue = this.container.querySelector('.picker-display-value');
        this.dropdown = this.container.querySelector('.picker-dropdown');
        
        this.updateDisplay();
        this.renderView();
    }

    updateDisplay() {
        if (this.selectedDate) {
            const month = PICKER_CONFIG.monthsFull[this.selectedDate.getMonth()];
            const day = this.selectedDate.getDate();
            const year = this.selectedDate.getFullYear();
            this.displayValue.textContent = `${month} ${day}, ${year}`;
            this.displayValue.classList.remove('picker-display-placeholder');
        } else {
            this.displayValue.textContent = this.options.placeholder;
            this.displayValue.classList.add('picker-display-placeholder');
        }
    }
    
    setDate(date, triggerCallback = true) {
        this.selectedDate = date;
        if (date) {
            this.viewYear = date.getFullYear();
            this.viewMonth = date.getMonth();
        }
        this.updateDisplay();
        this.renderView();
        
        if (triggerCallback) {
            this.options.onSelect(date);
        }
    }
    
    getDate() {
        return this.selectedDate;
    }
    
    renderView() {
        switch (this.currentView) {
            case 'years':
                this.renderYearsView();
                break;
            case 'months':
                this.renderMonthsView();
                break;
            case 'days':
            default:
                this.renderDaysView();
                break;
        }
    }
    
    renderYearsView() {
        let html = `
            <div class="picker-header">
                <button type="button" class="picker-nav-btn" data-action="prev-years">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                </button>
                <span class="picker-title">${this.yearsPageStart} – ${this.yearsPageStart + 15}</span>
                <button type="button" class="picker-nav-btn" data-action="next-years">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                </button>
            </div>
            <div class="picker-grid picker-grid-years">
        `;
        
        const currentYear = new Date().getFullYear();
        for (let i = 0; i < 16; i++) {
            const year = this.yearsPageStart + i;
            const isSelected = this.selectedDate && this.selectedDate.getFullYear() === year;
            const isCurrentYear = year === currentYear;
            
            let classes = 'picker-cell';
            if (isSelected) classes += ' selected';
            if (isCurrentYear) classes += ' today';
            
            html += `<div class="${classes}" data-year="${year}">${year}</div>`;
        }
        
        html += '</div>';
        this.dropdown.innerHTML = html;
    }

    renderMonthsView() {
        let html = `
            <div class="picker-header">
                <button type="button" class="picker-back-btn" data-action="back-to-years">← Years</button>
                <span class="picker-title">${this.viewYear}</span>
                <div></div>
            </div>
            <div class="picker-grid picker-grid-months">
        `;
        
        const currentDate = new Date();
        const isCurrentYear = this.viewYear === currentDate.getFullYear();
        
        for (let i = 0; i < 12; i++) {
            const isSelected = this.selectedDate && 
                               this.selectedDate.getFullYear() === this.viewYear && 
                               this.selectedDate.getMonth() === i;
            const isCurrentMonth = isCurrentYear && i === currentDate.getMonth();
            
            let classes = 'picker-cell';
            if (isSelected) classes += ' selected';
            if (isCurrentMonth) classes += ' today';
            
            html += `<div class="${classes}" data-month="${i}">${PICKER_CONFIG.months[i]}</div>`;
        }
        
        html += '</div>';
        this.dropdown.innerHTML = html;
    }

    renderDaysView() {
        const firstDay = new Date(this.viewYear, this.viewMonth, 1);
        const lastDay = new Date(this.viewYear, this.viewMonth + 1, 0);
        const startDayOfWeek = firstDay.getDay();
        const daysInMonth = lastDay.getDate();
        
        const prevMonthLastDay = new Date(this.viewYear, this.viewMonth, 0).getDate();
        
        // Clear button HTML (only if allowClear and date is selected)
        const clearBtn = (this.options.allowClear && this.selectedDate) 
            ? '<button type="button" class="picker-clear-btn" data-action="clear">Clear</button>'
            : '';
        
        let html = `
            <div class="picker-header">
                <button type="button" class="picker-back-btn" data-action="back-to-months">← ${this.viewYear}</button>
                <span class="picker-title">${PICKER_CONFIG.monthsFull[this.viewMonth]}</span>
                <div style="display: flex; gap: 0.25rem; align-items: center;">
                    ${clearBtn}
                    <button type="button" class="picker-nav-btn" data-action="prev-month">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </button>
                    <button type="button" class="picker-nav-btn" data-action="next-month">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        html += '<div class="picker-grid picker-grid-days">';
        for (const dow of PICKER_CONFIG.daysOfWeek) {
            html += `<div class="picker-dow">${dow}</div>`;
        }
        
        const today = new Date();
        const todayStr = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`;
        const selectedStr = this.selectedDate ? 
            `${this.selectedDate.getFullYear()}-${this.selectedDate.getMonth()}-${this.selectedDate.getDate()}` : '';
        
        // Previous month's trailing days
        for (let i = startDayOfWeek - 1; i >= 0; i--) {
            const day = prevMonthLastDay - i;
            html += `<div class="picker-cell other-month" data-day="${day}" data-month-offset="-1">${day}</div>`;
        }
        
        // Current month days
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${this.viewYear}-${this.viewMonth}-${day}`;
            let classes = 'picker-cell';
            if (dateStr === selectedStr) classes += ' selected';
            if (dateStr === todayStr) classes += ' today';
            
            html += `<div class="${classes}" data-day="${day}">${day}</div>`;
        }
        
        // Next month's leading days
        const totalCells = startDayOfWeek + daysInMonth;
        const remainingCells = totalCells <= 35 ? 35 - totalCells : 42 - totalCells;
        for (let day = 1; day <= remainingCells; day++) {
            html += `<div class="picker-cell other-month" data-day="${day}" data-month-offset="1">${day}</div>`;
        }
        
        html += '</div>';
        this.dropdown.innerHTML = html;
    }


    attachEvents() {
        this.display.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });
        
        this.display.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.toggle();
            }
        });
        
        this.dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
            const target = e.target.closest('[data-action], [data-year], [data-month], [data-day]');
            if (!target) return;
            
            const action = target.dataset.action;
            if (action) {
                this.handleAction(action);
                return;
            }
            
            if (target.dataset.year) {
                this.viewYear = parseInt(target.dataset.year);
                this.currentView = 'months';
                this.renderView();
                return;
            }
            
            if (target.dataset.month !== undefined) {
                this.viewMonth = parseInt(target.dataset.month);
                this.currentView = 'days';
                this.renderView();
                return;
            }
            
            if (target.dataset.day) {
                let year = this.viewYear;
                let month = this.viewMonth;
                
                const monthOffset = parseInt(target.dataset.monthOffset || 0);
                if (monthOffset !== 0) {
                    month += monthOffset;
                    if (month < 0) { month = 11; year--; }
                    if (month > 11) { month = 0; year++; }
                }
                
                const day = parseInt(target.dataset.day);
                this.selectedDate = new Date(year, month, day);
                this.viewYear = year;
                this.viewMonth = month;
                
                this.updateDisplay();
                this.close();
                this.options.onSelect(this.selectedDate);
            }
        });
        
        document.addEventListener('click', () => this.close());
    }
    
    handleAction(action) {
        switch (action) {
            case 'clear':
                this.selectedDate = null;
                this.updateDisplay();
                this.close();
                this.options.onSelect(null);
                break;
            case 'prev-years':
                this.yearsPageStart -= 16;
                this.renderView();
                break;
            case 'next-years':
                this.yearsPageStart += 16;
                this.renderView();
                break;
            case 'back-to-years':
                this.yearsPageStart = Math.floor(this.viewYear / 16) * 16;
                this.currentView = 'years';
                this.renderView();
                break;
            case 'back-to-months':
                this.currentView = 'months';
                this.renderView();
                break;
            case 'prev-month':
                this.viewMonth--;
                if (this.viewMonth < 0) {
                    this.viewMonth = 11;
                    this.viewYear--;
                }
                this.renderView();
                break;
            case 'next-month':
                this.viewMonth++;
                if (this.viewMonth > 11) {
                    this.viewMonth = 0;
                    this.viewYear++;
                }
                this.renderView();
                break;
        }
    }
    
    toggle() {
        if (this.dropdown.classList.contains('show')) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        document.querySelectorAll('.picker-dropdown.show').forEach(d => d.classList.remove('show'));
        this.dropdown.classList.add('show');
        this.renderView();
    }
    
    close() {
        this.dropdown.classList.remove('show');
    }
}


// ============================================================
// INITIALIZATION HELPERS
// ============================================================

const pickerInstances = {};

function initDatePicker(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Date picker container not found: ${containerId}`);
        return null;
    }
    
    const picker = new DatePicker(container, options);
    pickerInstances[containerId] = picker;
    return picker;
}

function getPicker(containerId) {
    return pickerInstances[containerId] || null;
}

function parseDateString(dateStr) {
    if (!dateStr) return null;
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (match) {
        return new Date(parseInt(match[1]), parseInt(match[2]) - 1, parseInt(match[3]));
    }
    return null;
}

function formatDateForServer(date) {
    if (!date) return '';
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}
