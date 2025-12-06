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
