// ---------------------------------------------------------------------------
// form-guard.js — unsaved-changes protection for the book form.
// Ported from EdgeCase's form-guard.js (leave-protection half only; no
// dirty-state Save button).
//
// Opt-in: <form data-dirty-guard>. Per guarded form:
//
// - beforeunload: tab close / reload / browser back / address bar gets the
//   browser's native "leave site?" prompt when the form is dirty.
//   Disarmed on any un-prevented form submit on the page (Save, and the
//   Delete modal's separate form), so deliberate actions never prompt.
// - In-page links (Cancel — any .form-actions a): the custom
//   #unsaved-changes-modal, with the destination remembered until the
//   user picks Stay Here or Leave Without Saving.
//
// Snapshot-and-compare, not event counting: pickers.js writes hidden input
// values programmatically with no input/change events, so the form is
// serialized at load and re-compared on demand (edit + undo reads clean).
//
// Load this script AFTER the page's own init scripts: its DOMContentLoaded
// handler must run after the date pickers write their initial values, or
// the form reads as dirty from page load. A second re-baseline at window
// `load` covers anything slower, unless the user has already touched the
// form.
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[data-dirty-guard]').forEach(function(form) {
        const serialize = function() {
            const params = new URLSearchParams(new FormData(form)).toString();
            // FormData renders File objects as "[object File]"; append names.
            const files = Array.from(form.querySelectorAll('input[type="file"]'))
                .map(function(input) { return input.value; })
                .join('|');
            return params + '\u0000' + files;
        };

        let baseline = serialize();
        const isDirty = function() { return serialize() !== baseline; };

        let userTouched = false;
        const markTouched = function() { userTouched = true; };
        form.addEventListener('input', markTouched);
        form.addEventListener('change', markTouched);
        form.addEventListener('click', markTouched);

        window.addEventListener('load', function() {
            if (!userTouched) baseline = serialize();
        });

        // --- Native prompt for tab close / reload / back ---
        const onBeforeUnload = function(e) {
            if (isDirty()) {
                e.preventDefault();
                e.returnValue = '';  // some browsers require this
            }
        };
        const disarm = function() {
            window.removeEventListener('beforeunload', onBeforeUnload);
        };
        window.addEventListener('beforeunload', onBeforeUnload);

        // Any form on the page (Save, Delete modal). Bubble phase on document
        // so form-level handlers have already had their chance to cancel.
        document.addEventListener('submit', function(e) {
            if (!e.defaultPrevented) disarm();
        });

        // --- Custom modal for in-page links (Cancel) ---
        const modal = document.getElementById('unsaved-changes-modal');
        const stayBtn = document.getElementById('unsaved-stay-btn');
        const leaveBtn = document.getElementById('unsaved-leave-btn');
        if (!modal || !stayBtn || !leaveBtn) return;

        let pendingHref = null;

        window.addEventListener('click', function(e) {
            const link = e.target && e.target.closest
                ? e.target.closest('.form-actions a')
                : null;
            if (!link || !isDirty()) return;
            e.preventDefault();
            e.stopPropagation();
            pendingHref = link.href;
            modal.style.display = 'flex';
        }, true);

        const close = function() {
            pendingHref = null;
            modal.style.display = 'none';
        };
        stayBtn.addEventListener('click', close);
        modal.addEventListener('click', function(e) {
            if (e.target === modal) close();
        });
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.style.display === 'flex') close();
        });

        leaveBtn.addEventListener('click', function() {
            if (!pendingHref) return;
            const href = pendingHref;
            disarm();
            close();
            window.location.assign(href);
        });
    });
});
