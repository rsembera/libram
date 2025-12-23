/* Libram - Backups JavaScript */

let pendingFilename = null;
let pendingLocation = null;

// Track current dropdown values
let currentFrequency = null;
let currentRetention = null;
let currentLocation = null;

// ============================================================================
// CUSTOM DROPDOWN HANDLING
// ============================================================================

function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const isOpen = dropdown.classList.contains('open');
    
    // Close all dropdowns first
    document.querySelectorAll('.custom-dropdown').forEach(d => {
        d.classList.remove('open');
    });
    
    // Toggle the clicked one
    if (!isOpen) {
        dropdown.classList.toggle('open');
    }
}

function selectFrequency(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    document.getElementById('frequency-selected-text').textContent = text;
    
    document.querySelectorAll('#frequency-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    document.getElementById('frequency-dropdown').classList.remove('open');
    
    currentFrequency = value;
    saveBackupSettings();
}

function selectRetention(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    
    document.getElementById('retention-selected-text').textContent = text;
    
    document.querySelectorAll('#retention-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    document.getElementById('retention-dropdown').classList.remove('open');
    
    currentRetention = value;
    saveBackupSettings();
}

function selectLocation(element) {
    const value = element.dataset.value;
    const text = element.textContent.trim();
    const previousLocation = currentLocation;
    
    document.getElementById('location-selected-text').textContent = text;
    
    document.querySelectorAll('#location-dropdown .custom-dropdown-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    
    document.getElementById('location-dropdown').classList.remove('open');
    
    currentLocation = value;
    saveBackupSettings(previousLocation !== value);
}

// ============================================================================
// SETTINGS SAVE
// ============================================================================

function saveBackupSettings(locationChanged = false) {
    const formData = new FormData();
    formData.append('frequency', currentFrequency);
    formData.append('retention', currentRetention);
    formData.append('location', currentLocation);
    
    fetch('/backups/settings', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'ok') {
            alert('Error saving settings: ' + (data.message || 'Unknown error'));
        } else if (locationChanged) {
            window.location.reload();
        }
    })
    .catch(err => {
        alert('Error saving settings');
    });
}

// ============================================================================
// BACKUP OPERATIONS
// ============================================================================

function createBackup() {
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ph ph-circle-notch icon-sm icon-inline"></i> Creating...';
    btn.disabled = true;
    
    fetch('/backups/create', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            location.reload();
        } else {
            alert('Error creating backup: ' + data.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    })
    .catch(err => {
        alert('Error creating backup');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function confirmRestore(filename, location) {
    pendingFilename = filename;
    pendingLocation = location;
    document.getElementById('restore-modal').style.display = 'flex';
}

function confirmDelete(filename, location) {
    pendingFilename = filename;
    pendingLocation = location;
    document.getElementById('delete-modal').style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    pendingFilename = null;
    pendingLocation = null;
}

function doRestore() {
    if (!pendingFilename) return;
    
    const formData = new FormData();
    formData.append('location', pendingLocation || 'default');
    
    fetch('/backups/restore/' + pendingFilename, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            alert('Backup restored successfully. The page will reload.');
            location.reload();
        } else {
            alert('Error restoring backup: ' + data.message);
        }
    })
    .catch(err => {
        alert('Error restoring backup');
    })
    .finally(() => {
        closeModal('restore-modal');
    });
}

function doDelete() {
    if (!pendingFilename) return;
    
    const formData = new FormData();
    formData.append('location', pendingLocation || 'default');
    
    fetch('/backups/delete/' + pendingFilename, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            location.reload();
        } else {
            alert('Error deleting backup: ' + data.message);
        }
    })
    .catch(err => {
        alert('Error deleting backup');
    })
    .finally(() => {
        closeModal('delete-modal');
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Close dropdowns when clicking outside
document.addEventListener('click', function(e) {
    document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
        if (!dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });
    
    // Close modals on click outside
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
        pendingFilename = null;
        pendingLocation = null;
    }
});

// Initialize current values from selected options
document.addEventListener('DOMContentLoaded', function() {
    const freqSelected = document.querySelector('#frequency-dropdown .custom-dropdown-option.selected');
    const retSelected = document.querySelector('#retention-dropdown .custom-dropdown-option.selected');
    const locSelected = document.querySelector('#location-dropdown .custom-dropdown-option.selected');
    
    if (freqSelected) currentFrequency = freqSelected.dataset.value;
    if (retSelected) currentRetention = retSelected.dataset.value;
    if (locSelected) currentLocation = locSelected.dataset.value;
});
