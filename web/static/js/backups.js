/* Libram - Backups JavaScript */

let pendingFilename = null;

function saveBackupSettings() {
    const frequency = document.getElementById('frequency').value;
    const retention = document.getElementById('retention').value;
    
    const formData = new FormData();
    formData.append('frequency', frequency);
    formData.append('retention', retention);
    
    fetch('/backups/settings', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'ok') {
            alert('Error saving settings: ' + (data.message || 'Unknown error'));
        }
    })
    .catch(err => {
        alert('Error saving settings');
    });
}

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

function confirmRestore(filename) {
    pendingFilename = filename;
    document.getElementById('restore-modal').style.display = 'flex';
}

function confirmDelete(filename) {
    pendingFilename = filename;
    document.getElementById('delete-modal').style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    pendingFilename = null;
}

function doRestore() {
    if (!pendingFilename) return;
    
    fetch('/backups/restore/' + pendingFilename, {
        method: 'POST'
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
    
    fetch('/backups/delete/' + pendingFilename, {
        method: 'POST'
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

// Close modals on click outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
        pendingFilename = null;
    }
});
