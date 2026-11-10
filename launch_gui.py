#!/usr/bin/env python3
import traceback
"""
SRP GUI Launcher Script
"""
import os
import sys
from pathlib import Path

# Ensure the project directory is in the Python path.
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def main():
    print("=" * 60)
    print("Slutty Rabbit Productions Web Research Workstation")
    print("=" * 60)
    print()

    # Verify Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)

    # Verify PySide6 is installed.
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        print(f"✓ PySide6 {QtCore.__version__} loaded")
    except ImportError as exc:
        print(f"✗ PySide6 not available: {exc}")
        print("  Install with: pip install PySide6")
        sys.exit(1)

    # Verify Qt platform.
    try:
        from PySide6.QtCore import QCoreApplication
        app_name = QCoreApplication.applicationName() or "SRP"
        print(f"✓ Qt platform initialized")
    except Exception as exc:
        print(f"✗ Qt platform error: {exc}")
        sys.exit(1)

    # Import core services.
    try:
        from gui.core.service_registry import ServiceRegistry
        from gui.core.backend_adapter import BackendServiceAdapter
        print("✓ Core services imported")
    except ImportError as exc:
        print(f"✗ Failed to import core services: {exc}")
        traceback.print_exc()
        sys.exit(1)

    # Create the service registry and backend adapter.
    service_registry = ServiceRegistry()
    backend = BackendServiceAdapter(service_registry)

    # Import the main window.
    try:
        from gui.main_window import SRPMainWindow
        print("✓ Main window imported")
    except ImportError as exc:
        print(f"✗ Failed to import main window: {exc}")
        traceback.print_exc()
        sys.exit(1)

    # Create the Qt application.
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("SRP")
    app.setApplicationDisplayName("Slutty Rabbit Productions Web Research Workstation")
    app.setApplicationVersion("1.0.1")

    # Create and show the main window.
    main_window = SRPMainWindow(service_registry, backend)
    main_window.show()

    print("Application ready. Press Ctrl+C to exit.\n")

    # Start the event loop
    return app.exec()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        sys.exit(0)
