#!/usr/bin/env python3
"""
Core GUI Application Components
"""

import sys
from PySide6.QtCore import QSettings, QObject, Signal
from PySide6.QtWidgets import QApplication

class GUIApplication(QApplication):
    """Core GUI application class."""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Kilo - Web Research Workstation")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("Kilo")
        
        # Initialize service registry
        from gui.core.service_registry import ServiceRegistry
        self.service_registry = ServiceRegistry()
        
        # Initialize backend adapters
        from gui.core.backend_adapter import BackendServiceAdapter
        self.backend = BackendServiceAdapter(self.service_registry)
        
        # Set up global state
        self._setup_globals()
    
    def _setup_globals(self):
        """Set up global application state."""
        self.current_workspace = "overview"
        self.active_sessions = {}
        self.background_workers = []
        self.settings = QSettings("Kilo", "ScrapeEngine")
    
    def save_application_state(self):
        """Save application state to settings."""
        self.settings.setValue("windowGeometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("currentWorkspace", self.current_workspace)
    
    def load_application_state(self):
        """Load application state from settings."""
        if self.settings.contains("windowGeometry"):
            self.restoreGeometry(self.settings.value("windowGeometry"))
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))
        if self.settings.contains("currentWorkspace"):
            self.current_workspace = self.settings.value("currentWorkspace")
    
    def get_service_registry(self):
        """Get the service registry."""
        return self.service_registry
    
    def get_backend(self):
        """Get the backend adapter."""
        return self.backend

class ApplicationSignals(QObject):
    """Signal definitions for application-wide communication."""
    
    # Status updates
    status_updated = Signal(str)
    progress_updated = Signal(int, int)  # value, maximum
    
    # Workspace updates
    workspace_changed = Signal(str)
    
    # Session management
    session_created = Signal(dict)
    session_updated = Signal(dict)
    session_deleted = Signal(str)
    
    # Task completion
    task_completed = Signal(dict)
    task_failed = Signal(str)
    
    # Storage updates
    storage_updated = Signal(dict)
    
    # Error handling
    error_occurred = Signal(str, str)  # message, details
    
    # Background worker events
    worker_started = Signal(str)
    worker_completed = Signal(str)
    worker_failed = Signal(str, str)
    worker_progress = Signal(str, int, int)
class GlobalState:
    """Global application state management."""
    
    def __init__(self):
        self._state = {
            "active_sessions": {},
            "background_jobs": {},
            "storage_usage": {},
            "workspaces": {},
            "settings": {},
            "errors": [],
            "last_activity": None
        }
    
    def update_session(self, session_id: str, session_data: dict):
        """Update session state."""
        self._state["active_sessions"][session_id] = session_data
        self._state["last_activity"] = session_data.get("updated_at")
    
    def remove_session(self, session_id: str):
        """Remove session from state."""
        self._state["active_sessions"].pop(session_id, None)
    
    def update_storage(self, storage_data: dict):
        """Update storage state."""
        self._state["storage_usage"] = storage_data
    
    def add_error(self, message: str, details: str = ""):
        """Add error to error log."""
        error = {
            "message": message,
            "details": details,
            "timestamp": str(__import__("datetime").datetime.now())
        }
        self._state["errors"].append(error)
        # Keep only last 100 errors
        if len(self._state["errors"]) > 100:
            self._state["errors"] = self._state["errors"][-100:]
    
    def get_state(self, key: str = None):
        """Get state or specific key."""
        if key:
            return self._state.get(key)
        return self._state.copy()
    
    def update_workspace(self, workspace_id: str, workspace_data: dict):
        """Update workspace state."""
        self._state["workspaces"][workspace_id] = workspace_data
    
    def get_active_sessions(self):
        """Get active sessions."""
        return list(self._state["active_sessions"].values())
    
    def get_storage_stats(self):
        """Get storage statistics."""
        return self._state["storage_usage"]