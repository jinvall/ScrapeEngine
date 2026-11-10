#!/usr/bin/env python3
"""
GUI Application Launcher
Entry point for the Kilo Web Research Workstation GUI.
"""

import sys
import os
import traceback

# Add the virtual environment path
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.12/site-packages'))
    print("[DEBUG] entrypoint: Added venv path", file=sys.stderr)
except Exception as e:
    print(f"[DEBUG] entrypoint: Failed to add venv path: {e}", file=sys.stderr)
    traceback.print_exc()

# Add parent directory to path
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("[DEBUG] entrypoint: Added gui dir to path", file=sys.stderr)
except Exception as e:
    print(f"[DEBUG] entrypoint: Failed to add gui dir: {e}", file=sys.stderr)
    traceback.print_exc()

# Try to import QApplication
try:
    from PySide6.QtWidgets import QApplication
    print("[DEBUG] entrypoint: Imported QApplication", file=sys.stderr)
except Exception as e:
    print(f"[DEBUG] entrypoint: Failed to import QApplication: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

# Import main GUI components
try:
    from gui.main_window import KiloMainWindow
    print("[DEBUG] entrypoint: Imported KiloMainWindow", file=sys.stderr)
    from gui.core.service_registry import ServiceRegistry
    print("[DEBUG] entrypoint: Imported ServiceRegistry", file=sys.stderr)
    from gui.core.backend_adapter import BackendServiceAdapter
    print("[DEBUG] entrypoint: Imported BackendServiceAdapter", file=sys.stderr)
except Exception as e:
    print(f"[DEBUG] entrypoint: Failed to import GUI components: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

def main():
    """Main application entry point."""
    print("[DEBUG] entrypoint: Starting main()", file=sys.stderr)
    try:
        # Create application
        app = QApplication(sys.argv)
        print("[DEBUG] entrypoint: Created QApplication", file=sys.stderr)
        
        # Set application properties
        app.setApplicationName("Kilo - Web Research Workstation")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Kilo")
        print("[DEBUG] entrypoint: Set app properties", file=sys.stderr)
        
        # Create service registry and backend
        try:
            service_registry = ServiceRegistry()
            print("[DEBUG] entrypoint: Created ServiceRegistry", file=sys.stderr)
            backend = BackendServiceAdapter(service_registry)
            print("[DEBUG] entrypoint: Created BackendServiceAdapter", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] entrypoint: Failed to create services: {e}", file=sys.stderr)
            traceback.print_exc()
            raise
        
        # Create main window
        try:
            main_window = KiloMainWindow(service_registry, backend)
            print("[DEBUG] entrypoint: Created KiloMainWindow", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] entrypoint: Failed to create main window: {e}", file=sys.stderr)
            traceback.print_exc()
            raise
        
        # Show main window
        try:
            main_window.show()
            print("[DEBUG] entrypoint: Showed main window", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] entrypoint: Failed to show main window: {e}", file=sys.stderr)
            traceback.print_exc()
            raise
        
        # Start the event loop
        print("[DEBUG] entrypoint: Starting event loop", file=sys.stderr)
        return app.exec()
    except Exception as e:
        print(f"[DEBUG] entrypoint: Fatal error in main: {e}", file=sys.stderr)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[DEBUG] entrypoint: Uncaught exception: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
