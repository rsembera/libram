#!/usr/bin/env python3
"""
Libram - Personal Reading Tracker
Entry point for the application.
"""

import atexit
import os
import sys
import logging
import webbrowser
import signal
import time
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app  # noqa: E402

# Track if cleanup has run to avoid running twice
_cleanup_done = False
_app = None

# Heartbeat tracking for desktop mode
_last_heartbeat = time.time()
_heartbeat_lock = threading.Lock()
HEARTBEAT_TIMEOUT = 30  # seconds without heartbeat before shutdown


def update_heartbeat():
    """Update the last heartbeat timestamp. Called from session-status endpoint."""
    global _last_heartbeat
    with _heartbeat_lock:
        _last_heartbeat = time.time()


def _heartbeat_monitor():
    """Background thread that monitors for heartbeat timeout in desktop mode."""
    global _last_heartbeat
    
    while True:
        time.sleep(5)  # Check every 5 seconds
        
        with _heartbeat_lock:
            elapsed = time.time() - _last_heartbeat
        
        if elapsed > HEARTBEAT_TIMEOUT:
            print(f"\n[Desktop] No browser heartbeat for {int(elapsed)}s - shutting down...")
            # Trigger graceful shutdown
            os.kill(os.getpid(), signal.SIGTERM)
            break


def _cleanup():
    """Cleanup function for atexit - backup and checkpoint database."""
    global _cleanup_done
    if _cleanup_done or _app is None:
        return
    _cleanup_done = True
    
    try:
        with _app.app_context():
            db = _app.get_db()
            if db:
                # Run backup check before shutdown
                try:
                    from web.blueprints.backups import check_auto_backup
                    check_auto_backup(_app)
                except Exception as e:
                    print(f"[Backup] Warning: {e}")
                
                db.checkpoint()
    except Exception:
        pass  # Silent fail on exit


# Register atexit handler
atexit.register(_cleanup)


class QuietRequestFilter(logging.Filter):
    """Filter out noisy static file requests from logs."""
    def filter(self, record):
        msg = record.getMessage()
        # Filter out static files (fonts, css, js, images)
        if '/static/' in msg:
            return False
        return True


def shutdown_handler(signum, frame):
    """Handle Ctrl-C gracefully - backup and checkpoint database before exit."""
    global _cleanup_done
    
    print("\n\nShutting down...")
    
    if not _cleanup_done and _app is not None:
        _cleanup_done = True
        try:
            with _app.app_context():
                db = _app.get_db()
                if db:
                    # Run backup check before shutdown
                    try:
                        from web.blueprints.backups import check_auto_backup
                        check_auto_backup(_app)
                        print("[Backup] Auto-backup check completed.")
                    except Exception as e:
                        print(f"[Backup] Warning: {e}")
                    
                    db.checkpoint()
                    print("[Database] Checkpoint completed.")
        except Exception as e:
            print(f"[Shutdown] Warning: {e}")
    
    sys.exit(0)


def main():
    """Start the Libram application."""
    global _app
    app = create_app()
    _app = app
    
    # Desktop mode: register heartbeat callback
    desktop_mode = os.environ.get('LIBRAM_DESKTOP') == '1'
    if desktop_mode:
        app.config['HEARTBEAT_CALLBACK'] = update_heartbeat
    
    # Get port from environment or use default
    port = int(os.environ.get('LIBRAM_PORT', 8090))
    host = os.environ.get('LIBRAM_HOST', '127.0.0.1')
    
    # Check for debug mode
    debug_mode = '--debug' in sys.argv or os.environ.get('LIBRAM_DEBUG') == '1'
    
    server_type = "Flask development server" if debug_mode else "Waitress"
    url = f"http://{host}:{port}"
    
    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   📚  LIBRAM - Personal Reading Tracker               ║
    ║                                                       ║
    ║   Running at: {url:<40}║
    ║   Server: {server_type:<44}║
    ║                                                       ║
    ║   Press Ctrl+C to stop                                ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Register shutdown handler for clean database checkpoint on Ctrl-C
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Desktop mode: start heartbeat monitor and auto-open browser
    desktop_mode = os.environ.get('LIBRAM_DESKTOP') == '1'
    if desktop_mode:
        # Start heartbeat monitor thread
        monitor = threading.Thread(target=_heartbeat_monitor, daemon=True)
        monitor.start()
        
        # Always open browser in desktop mode
        def open_browser():
            time.sleep(1.0)
            webbrowser.open(f'http://{host}:{port}')
        threading.Thread(target=open_browser, daemon=True).start()
    elif os.environ.get('LIBRAM_BROWSER') == '1':
        # Manual browser open request
        def open_browser():
            time.sleep(1.0)
            webbrowser.open(f'http://{host}:{port}')
        threading.Thread(target=open_browser, daemon=True).start()
    
    if debug_mode:
        # Development mode with auto-reload
        log = logging.getLogger('werkzeug')
        log.addFilter(QuietRequestFilter())
        app.run(host=host, port=port, debug=True)
    else:
        # Production mode with Waitress
        from waitress import serve
        
        # Configure Waitress logging
        logger = logging.getLogger('waitress')
        logger.setLevel(logging.INFO)
        
        serve(app, host=host, port=port, threads=4)


if __name__ == '__main__':
    main()
