"""
Main Window Implementation
Professional Qt6 desktop application for web research workstation
"""

import sys
from PySide6.QtCore import QSettings, Qt, QRect, Signal, Slot
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolBar, QMenuBar, QMessageBox, QStatusBar
)

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter
import traceback

class SRPMainWindow(QMainWindow):
    """Main application window - professional research workstation interface."""
    
    # Signals for communication between components
    workspace_changed = Signal(str)
    status_updated = Signal(str)
    storage_updated = Signal(dict)
    research_session_created = Signal(dict)
    
    def __init__(self, service_registry: ServiceRegistry, backend: BackendServiceAdapter):
        print("[DEBUG] SRPMainWindow: Initializing...", file=__import__("sys").stderr)
        try:
            super().__init__()
            self.service_registry = service_registry
            self.backend = backend
            
            self.current_workspace = "overview"
            self.active_sessions = {}
            
            self.setWindowTitle("Slutty Rabit Productions Web Research Workstation")
            self.setMinimumSize(1400, 900)
            print("[DEBUG] SRPMainWindow: Basic setup done", file=__import__("sys").stderr)
            
            # Initialize UI
            print("[DEBUG] SRPMainWindow: Calling init_ui()...", file=__import__("sys").stderr)
            self.init_ui()
            print("[DEBUG] SRPMainWindow: init_ui() done", file=__import__("sys").stderr)
            try:
                self.load_application_settings()
                print("[DEBUG] SRPMainWindow: load_application_settings() done", file=__import__("sys").stderr)
            except Exception as e:
                print(f"[DEBUG] SRPMainWindow: load_application_settings() failed: {e}", file=__import__("sys").stderr)
                traceback.print_exc()
            
            # Connect signals
            try:
                self.connect_signals()
                print("[DEBUG] SRPMainWindow: connect_signals() done", file=__import__("sys").stderr)
            except Exception as e:
                print(f"[DEBUG] SRPMainWindow: connect_signals() failed: {e}", file=__import__("sys").stderr)
                traceback.print_exc()
            
            # Update initial status
            try:
                self.update_status_bar("Ready")
                self.update_storage_indicator()
                print("[DEBUG] SRPMainWindow: Initial status updated", file=__import__("sys").stderr)
            except Exception as e:
                print(f"[DEBUG] SRPMainWindow: status update failed: {e}", file=__import__("sys").stderr)
                traceback.print_exc()
            print("[DEBUG] SRPMainWindow: Initialization complete", file=__import__("sys").stderr)
        except Exception as e:
            print(f"[DEBUG] SRPMainWindow: Fatal error in __init__: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
            raise
    
    def init_ui(self):
        """Initialize the user interface."""
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Create navigation panel
        self.create_navigation_panel()
        
        # Create workspace area
        self.create_workspace_area()
        
        # Create status bar
        self.create_status_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Show overview workspace by default
        self.show_overview_workspace()
    
    def create_navigation_panel(self):
        """Create the left navigation panel."""
        self.nav_panel = QWidget()
        self.nav_panel.setFixedWidth(280)
        self.nav_layout = QVBoxLayout(self.nav_panel)
        
        # Navigation header
        nav_header = QLabel("Workspaces")
        nav_header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.nav_layout.addWidget(nav_header)
        
        # Navigation buttons
        self.nav_buttons = {}
        workspaces = [
            ("Overview", "📊", "Overview workspace"),
            ("Research", "🔍", "Research workspace"),
            ("Web Discovery", "🕷️", "Web discovery workspace"),
            ("Site Explorer", "🌐", "Site explorer workspace"),
            ("Search", "🔎", "Search workspace"),
            ("Documents", "📄", "Documents workspace"),
            ("Entities", "🏷️", "Entities workspace"),
            ("Relationships", "🔗", "Relationships workspace"),
            ("Collections", "📚", "Collections workspace"),
            ("Crawl Queue", "⏱️", "Crawl queue workspace"),
            ("Reports", "📊", "Reports workspace"),
            ("Storage", "💾", "Storage workspace"),
        ]
        
        for workspace_id, icon, tooltip in workspaces:
            button = QPushButton(f"  {icon} {workspace_id}")
            button.setToolTip(tooltip)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, wid=workspace_id: self.switch_workspace(wid))
            self.nav_buttons[workspace_id] = button
            self.nav_layout.addWidget(button)
        
        self.nav_layout.addStretch()
        
        self.main_layout.addWidget(self.nav_panel)
    
    def create_workspace_area(self):
        """Create the central workspace area."""
        self.workspace_panel = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_panel)
        
        # Workspace title
        self.workspace_title = QLabel("Overview")
        self.workspace_title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        self.workspace_layout.addWidget(self.workspace_title)
        
        # Workspace content area
        self.workspace_content = QWidget()
        self.workspace_content_layout = QVBoxLayout(self.workspace_content)
        
        # Initialize with overview workspace content directly (no placeholder)
        overview_widget = self.create_overview_workspace()
        self.workspace_content_layout.addWidget(overview_widget)
        
        self.workspace_layout.addWidget(self.workspace_content)
        
        self.main_layout.addWidget(self.workspace_panel, stretch= dll")
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Storage indicator
        self.storage_label = QLabel("Storage: 0/5 GiB (0%)")
        self.status_bar.addWidget(self.storage_label)
        
        # Progress indicator
        self.progress_label = QLabel("Ready")
        self.status_bar.addWidget(self.progress_label)
        
        # Worker count
        self.workers_label = QLabel("Workers: 0")
        self.status_bar.addWidget(self.workers_label)
        
        # Connection status
        self.connection_label = QLabel("● Connected")
        self.connection_label.setStyleSheet("color: green;")
        self.status_bar.addWidget(self.connection_label)
    
    def create_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Command interface button
        self.cmd_button = QPushButton("Command")
        self.cmd_button.setToolTip("Universal command interface")
        self.cmd_button.clicked.connect(self.show_command_interface)
        toolbar.addWidget(self.cmd_button)
        
        toolbar.addSeparator()
        
        # Research controls
        self.new_research_button = QPushButton("New Research")
        self.new_research_button.setToolTip("Start a new research session")
        self.new_research_button.clicked.connect(self.show_new_research_dialog)
        toolbar.addWidget(self.new_research_button)
        
        self.pause_research_button = QPushButton("Pause")
        self.pause_research_button.setToolTip("Pause current research")
        self.pause_research_button.clicked.connect(self.pause_research)
        self.pause_research_button.setEnabled(False)
        toolbar.addWidget(self.pause_research_button)
        
        self.resume_research_button = QPushButton("Resume")
        self.resume_research_button.setToolTip("Resume current research")
        self.resume_research_button.clicked.connect(self.resume_research)
        self.resume_research_button.setEnabled(False)
        toolbar.addWidget(self.resume_research_button)
        
        toolbar.addSeparator()
        
        # Crawl controls
        self.new_crawl_button = QPushButton("New Crawl")
        self.new_crawl_button.setToolTip("Start a new crawl job")
        self.new_crawl_button.clicked.connect(self.show_new_crawl_dialog)
        toolbar.addWidget(self.new_crawl_button)
        
        self.pause_crawl_button = QPushButton("Pause Crawl")
        self.pause_crawl_button.setToolTip("Pause current crawl")
        self.pause_crawl_button.clicked.connect(self.pause_crawl)
        self.pause_crawl_button.setEnabled(False)
        toolbar.addWidget(self.pause_crawl_button)
        
        toolbar.addSeparator()
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.setToolTip("Open search workspace")
        self.search_button.clicked.connect(self.show_search_workspace)
        toolbar.addWidget(self.search_button)
        
        # Explore button
        self.explore_button = QPushButton("Explore")
        self.explore_button.setToolTip("Open site explorer")
        self.explore_button.clicked.connect(self.show_site_explorer_workspace)
        toolbar.addWidget(self.explore_button)
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Research Session", self.show_new_research_dialog)
        file_menu.addAction("Save", self.save_session)
        file_menu.addAction("Export", self.export_results)
        file_menu.addSeparator()
        file_menu.addAction("Settings", self.show_settings_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # Workspace menu
        workspace_menu = menubar.addMenu("Workspaces")
        for workspace_id, button in self.nav_buttons.items():
            def make_handler(wid):
                def handler(checked=False):
                    self.switch_workspace(wid)
                return handler
            workspace_menu.addAction(button.text().replace("  ", ""), make_handler(workspace_id))
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about_dialog)
        help_menu.addAction("Documentation", self.show_documentation)
        help_menu.addAction("Keyboard Shortcuts", self.show_keyboard_shortcuts)
    
    def create_overview_workspace(self):
        """Create the overview workspace widget."""
        from gui.views.overview_view import OverviewView
        return OverviewView(self.service_registry, self.backend, main_window=self)
    
    def create_research_workspace(self):
        """Create the research workspace widget."""
        from gui.views.research_view import ResearchView
        return ResearchView(self.service_registry, self.backend)
    
    def create_web_discovery_workspace(self):
        """Create the web discovery workspace widget."""
        from gui.views.discovery_view import DiscoveryView
        return DiscoveryView(self.service_registry, self.backend)
    
    def create_site_explorer_workspace(self):
        """Create the site explorer workspace widget."""
        from gui.views.site_explorer_view import SiteExplorerView
        return SiteExplorerView(self.service_registry, self.backend)
    
    def create_search_workspace(self):
        """Create the search workspace widget."""
        from gui.views.search_view import SearchView
        return SearchView(self.service_registry, self.backend)
    
    def create_documents_workspace(self):
        """Create the documents workspace widget."""
        from gui.views.documents_view import DocumentsView
        return DocumentsView(self.service_registry, self.backend)
    
    def create_entities_workspace(self):
        """Create the entities workspace widget."""
        from gui.views.entities_view import EntitiesView
        return EntitiesView(self.service_registry, self.backend)
    
    def create_relationships_workspace(self):
        """Create the relationships workspace widget."""
        from gui.views.relationships_view import RelationshipsView
        return RelationshipsView(self.service_registry, self.backend)
    
    def create_collections_workspace(self):
        """Create the collections workspace widget."""
        from gui.views.collections_view import CollectionsView
        return CollectionsView(self.service_registry, self.backend)
    
    def create_crawl_queue_workspace(self):
        """Create the crawl queue workspace widget."""
        from gui.views.crawl_queue_view import CrawlQueueView
        return CrawlQueueView(self.service_registry, self.backend)
    
    def create_reports_workspace(self):
        """Create the reports workspace widget."""
        from gui.views.reports_view import ReportsView
        return ReportsView(self.service_registry, self.backend)
    
    def create_storage_workspace(self):
        """Create the storage workspace widget."""
        from gui.views.storage_view import StorageView
        return StorageView(self.service_registry, self.backend)
    
    def switch_workspace(self, workspace_id: str):
        """Switch to a different workspace."""
        if workspace_id not in self.workspace_widgets:
            return
        
        # Update current workspace
        self.current_workspace = workspace_id
        
        # Update navigation buttons
        for wid, button in self.nav_buttons.items():
            button.setChecked(wid == workspace_id)
        
        # Update workspace title
        self.workspace_title.setText(workspace_id.replace('_', ' ').title())
        
        # Switch workspace content
        workspace_widget = self.workspace_widgets[workspace_id]
        self.clear_workspace_content()
        self.workspace_content_layout.addWidget(workspace_widget)
        
        # Update status
        self.update_status_bar(f"Switched to {workspace_id} workspace")
        
        # Emit signal
        self.workspace_changed.emit(workspace_id)
    
    def connect_command_interface_signals(self):
        """Connect command interface signals to main window slots."""
        # Check if command interface is active and connect signals
        try:
            # We would connect signals here when command interface is created
            # For example:
            # self.command_interface.command_executed.connect(self.on_command_executed)
            # self.command_interface.command_error.connect(self.on_command_error)
            pass
        except Exception as e:
            import traceback
            print(f"[DEBUG] MainWindow: Failed to connect command interface signals: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
    
    def show_overview_workspace(self):
        """Show the overview workspace."""
        self.switch_workspace("overview")
    
    def show_research_workspace(self):
        """Show the research workspace."""
        self.switch_workspace("research")
    
    def show_discovery_workspace(self):
        """Show the web discovery workspace."""
        self.switch_workspace("web_discovery")
    
    def show_site_explorer_workspace(self):
        """Show the site explorer workspace."""
        self.switch_workspace("site_explorer")
    
    def show_search_workspace(self):
        """Show the search workspace."""
        self.switch_workspace("search")
    
    def show_documents_workspace(self):
        """Show the documents workspace."""
        self.switch_workspace("documents")
    
    def show_entities_workspace(self):
        """Show the entities workspace."""
        self.switch_workspace("entities")
    
    def show_relationships_workspace(self):
        """Show the relationships workspace."""
        self.switch_workspace("relationships")
    
    def show_collections_workspace(self):
        """Show the collections workspace."""
        self.switch_workspace("collections")
    
    def show_crawl_queue_workspace(self):
        """Show the crawl queue workspace."""
        self.switch_workspace("crawl_queue")
    
    def show_reports_workspace(self):
        """Show the reports workspace."""
        self.switch_workspace("reports")
    
    def show_storage_workspace(self):
        """Show the storage workspace."""
        self.switch_workspace("storage")
    
    def clear_workspace_content(self):
        """Clear current workspace content."""
        for i in reversed(range(self.workspace_content_layout.count())):
            item = self.workspace_content_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
    
    def update_status_bar(self, message: str):
        """Update the status bar message."""
        self.progress_label.setText(message)
        print(f"Status: {message}")
    
    def update_storage_indicator(self):
        """Update the storage usage indicator."""
        storage_service = self.backend.get_storage_service()
        if storage_service:
            status = storage_service.get_storage_status()
            self.storage_label.setText(
                f"Storage: {status.get('available_bytes', 0) / (1024**3):.1f}/"
                f"{status.get('hard_ceiling_bytes', 0) / (1024**3):.0f} GiB "
                f"({status.get('pct_used', 0):.1f}%)"
            )
    
    def update_worker_count(self, count: int):
        """Update the worker count display."""
        self.workers_label.setText(f"Workers: {count}")
    
    def connect_signals(self):
        """Connect signals between components."""
        # Connect backend signals
        try:
            storage_service = self.backend.get_storage_service()
            if storage_service and hasattr(storage_service, 'storage_updated'):
                storage_service.storage_updated.connect(self.update_storage_indicator)
        except Exception as e:
            import traceback
            print(f"[DEBUG] Failed to connect storage signal: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        # Connect workspace signals
        self.workspace_changed.connect(self.update_workspace_navigation)
        
        # Connect command interface signals
        # (would be connected when command interface is created)
    
    def update_workspace_navigation(self, workspace_id: str):
        """Update workspace navigation state."""
        self.nav_buttons[self.current_workspace].setChecked(False)
        if workspace_id in self.nav_buttons:
            self.nav_buttons[workspace_id].setChecked(True)
    
    def show_command_interface(self):
        """Show the command interface dialog."""
        from gui.widgets.command_interface import CommandInterface
        dialog = CommandInterface(self.service_registry, self)
        dialog.show()
    
    def show_new_research_dialog(self):
        """Show the new research dialog."""
        from gui.widgets.research_dialog import ResearchDialog
        try:
            dialog = ResearchDialog(self.service_registry, self)
        except Exception as e:
            import traceback
            print(f"[DEBUG] show_new_research_dialog: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
            try:
                dialog = ResearchDialog(self)
            except Exception as e2:
                print(f"[DEBUG] show_new_research_dialog fallback: {e2}", file=__import__("sys").stderr)
                traceback.print_exc()
                return
        dialog.show()
    
    def show_new_crawl_dialog(self):
        """Show the new crawl dialog."""
        try:
            from gui.widgets.crawl_dialog import CrawlDialog
            try:
                dialog = CrawlDialog(self.service_registry, self)
            except Exception:
                dialog = CrawlDialog(self)
            dialog.show()
        except Exception as e:
            import traceback
            print(f"[DEBUG] show_new_crawl_dialog: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
    
    def show_settings_dialog(self):
        """Show the settings dialog."""
        try:
            from gui.widgets.settings_dialog import SettingsDialog
            try:
                dialog = SettingsDialog(self.service_registry, self)
            except Exception:
                dialog = SettingsDialog(self)
            dialog.show()
        except Exception as e:
            import traceback
            print(f"[DEBUG] show_settings_dialog: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
    
    def pause_research(self):
        """Pause current research."""
        # Implementation would pause active research session
        self.update_status_bar("Research paused")
    
    def resume_research(self):
        """Resume current research."""
        # Implementation would resume active research session
        self.update_status_bar("Research resumed")
    
    def pause_crawl(self):
        """Pause current crawl."""
        # Implementation would pause active crawl job
        self.update_status_bar("Crawl paused")
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About SRP",
            "SRP - Web Research Workstation\n\n"
            "Version 1.0.0\n\n"
            "A professional desktop application for web scraping, research, and analysis."
        )
    
    def show_documentation(self):
        """Show documentation."""
        # Implementation would show documentation
        pass
    
    def show_keyboard_shortcuts(self):
        """Show keyboard shortcuts."""
        # Implementation would show keyboard shortcuts
        pass
    
    def save_session(self):
        """Save current session."""
        # Implementation would save current research session
        self.update_status_bar("Session saved")
    
    def export_results(self):
        """Export results."""
        # Implementation would export results
        self.update_status_bar("Results exported")
    
    def load_application_settings(self):
        """Load application settings from persistent storage."""
        settings = QSettings("SRP", "ScrapeEngine")
        
        # Restore window geometry
        if settings.contains("windowGeometry"):
            self.restoreGeometry(settings.value("windowGeometry"))
        
        if settings.contains("windowState"):
            self.restoreState(settings.value("windowState"))
        
        # Restore last workspace
        if settings.contains("currentWorkspace"):
            self.current_workspace = settings.value("currentWorkspace")
    
    def save_application_settings(self):
        """Save application settings to persistent storage."""
        settings = QSettings("SRP", "ScrapeEngine")
        
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("currentWorkspace", self.current_workspace)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_application_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    # Application entry point
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create service registry and backend
    service_registry = ServiceRegistry()
    backend = BackendServiceAdapter(service_registry)
    
    # Create main window
    main_window = SRPMainWindow(service_registry, backend)
    main_window.show()
    
    sys.exit(app.exec())
