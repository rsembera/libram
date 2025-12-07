#!/usr/bin/env python3
"""
Libram - Personal Reading Tracker
Entry point for the application.
"""

import os
import sys
import webbrowser
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app

def main():
    """Start the Libram application."""
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.environ.get('LIBRAM_PORT', 8090))
    host = os.environ.get('LIBRAM_HOST', '127.0.0.1')
    
    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   📚  LIBRAM - Personal Reading Tracker              ║
    ║                                                       ║
    ║   Running at: http://{host}:{port}                  ║
    ║                                                       ║
    ║   Press Ctrl+C to stop                               ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Open browser after short delay (only if explicitly requested)
    if os.environ.get('LIBRAM_BROWSER') == '1':
        def open_browser():
            time.sleep(1.0)
            webbrowser.open(f'http://{host}:{port}')
        
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the Flask app
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main()
