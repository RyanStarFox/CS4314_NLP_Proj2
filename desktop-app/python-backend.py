#!/usr/bin/env python3
"""
Python Backend Entry Point for Desktop App
This script starts the Streamlit server for the desktop application.
"""
import os
import sys
import subprocess
import signal

def get_app_dir():
    """Get the directory where the app files are located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller stores data files in _MEIPASS (for onefile) or _internal (for onedir)
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            # Look for _internal directory next to executable
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, '_internal')
            if os.path.exists(internal_dir):
                return internal_dir
            return exe_dir
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def main():
    app_dir = get_app_dir()
    
    # Change to app directory
    os.chdir(app_dir)
    
    # Set up environment
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_BROWSER_SERVER_ADDRESS'] = '127.0.0.1'
    
    # Find app.py
    app_py = os.path.join(app_dir, 'app.py')
    if not os.path.exists(app_py):
        print(f"Error: app.py not found at {app_py}")
        sys.exit(1)
    
    print(f"Starting Streamlit from: {app_py}")
    
    # Find available port
    import socket
    
    def find_available_port(start_port, max_tries=20):
        for port in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        return start_port

    port = find_available_port(8501)
    print(f"PYTHON_BACKEND_PORT={port}")
    sys.stdout.flush()

    print("DEBUG: Setting up environment...", flush=True)
    print(f"DEBUG: App dir: {app_dir}", flush=True)
    print(f"DEBUG: Python executable: {sys.executable}", flush=True)
    print(f"DEBUG: CWD: {os.getcwd()}", flush=True)
    if os.path.exists(app_dir):
        print(f"DEBUG: Content of app dir: {os.listdir(app_dir)}", flush=True)

    # Run Streamlit
    print("DEBUG: Importing streamlit.web.cli...", flush=True)
    try:
        from streamlit.web import cli as stcli
        print("DEBUG: Successfully imported streamlit.web.cli", flush=True)
    except Exception as e:
        print(f"ERROR: Failed to import streamlit: {e}", flush=True)
        sys.exit(1)
    
    sys.argv = [
        'streamlit',
        'run',
        app_py,
        '--global.developmentMode=false',
        f'--server.port={port}',
        '--server.address=127.0.0.1',
        '--server.headless=true',
        '--server.enableCORS=false',
        '--server.enableXsrfProtection=false',
        '--browser.gatherUsageStats=false',
        '--logger.level=warning',
    ]
    
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()
