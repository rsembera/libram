/* Libram - Backups JavaScript */

let pendingRestoreId = null;

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
            showMessage('Error', 'Error saving settings: ' + (data.message || 'Unknown error'));
        } else if (locationChanged) {
            window.location.reload();
        }
    })
    .catch(err => {
        showMessage('Error', 'Error saving settings');
    });
}

// ============================================================================
// BACKUP OPERATIONS
// ============================================================================

function createBackup() {
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ph ph-circle-notch ph-spin icon-sm icon-inline"></i> Creating...';
    btn.disabled = true;
    
    // Show progress modal
    document.getElementById('progress-modal').style.display = 'flex';
    
    fetch('/backups/create', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('progress-modal').style.display = 'none';
        if (data.status === 'ok') {
            if (data.no_changes) {
                showMessage('No Changes', 'No changes since last backup.');
                btn.innerHTML = originalText;
                btn.disabled = false;
            } else {
                showMessage('Backup Created', 
                    `Created ${data.type} backup: ${data.filename} (${data.size})`);
                setTimeout(() => location.reload(), 1500);
            }
        } else {
            showMessage('Error', 'Error creating backup: ' + data.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    })
    .catch(err => {
        document.getElementById('progress-modal').style.display = 'none';
        showMessage('Error', 'Error creating backup');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function confirmRestore(restorePointId) {
    pendingRestoreId = restorePointId;
    document.getElementById('restore-modal').style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    pendingRestoreId = null;
}

function showMessage(title, text) {
    document.getElementById('message-modal-title').textContent = title;
    document.getElementById('message-modal-text').textContent = text;
    document.getElementById('message-modal').style.display = 'flex';
}

function doRestore() {
    if (!pendingRestoreId) return;
    
    const btn = document.querySelector('#restore-modal .btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ph ph-circle-notch ph-spin"></i> Preparing...';
    btn.disabled = true;
    
    fetch('/backups/restore/' + encodeURIComponent(pendingRestoreId), {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        closeModal('restore-modal');
        if (data.status === 'ok') {
            if (data.requires_restart) {
                showMessage('Restore Prepared', 
                    'Restore has been prepared. Please restart the application to complete the restore.');
            } else {
                showMessage('Success', 'Backup restored successfully.');
                setTimeout(() => location.reload(), 1500);
            }
        } else {
            showMessage('Error', 'Error restoring backup: ' + data.message);
        }
    })
    .catch(err => {
        closeModal('restore-modal');
        showMessage('Error', 'Error restoring backup');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
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
        pendingRestoreId = null;
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
