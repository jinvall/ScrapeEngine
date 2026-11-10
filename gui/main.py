#!/usr/bin/env python3
"""
Main GUI Application for ScrapeEngine
Qt6/PySide6 desktop research workstation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import (
    QCoreApplication, QSettings, QSize, Qt, QThreadPool, QRunnable,
    QTimer, QRect, Signal, Slot, QFileInfo
)
from PySide6.QtGui import (
    QIcon, QPixmap, QFont, QPalette, QColor, QLinearGradient,
    QBrush, QPainter, QTextCursor, QTextCharFormat, QMouseEvent
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QSplitter, QTreeView, QTableView,
    QTextEdit, QLineEdit, QPushButton, QToolBar, QMenuBar, QVBoxLayout,
    QHBoxLayout, QWidget, QLabel, QFrame, QMessageBox, QProgressBar,
    QTabWidget, QListWidget, QListWidgetItem, QHeaderView, QAbstractItemView,
    QStyleFactory, QSizePolicy, QSpacerItem, QScrollArea, QStackedWidget,
    QGridLayout, QFormLayout, QDial, QGroupBox, QRadioButton, QCheckBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog, QSplineItemDelegate,
    QStyledItemDelegate, QAbstractTextDocumentLayout, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsEllipseItem, QGraphicsPathItem
)

from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Import existing backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction import CollectionProfile, ExtractionType
from query_parser import NaturalLanguageParser, StructuredQuery
from sitemap_module import SitemapEntry, URLNode

class ServiceRegistry:
    """Registry for backend services used by GUI components."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
    
    def get(self, name: str) -> Any:
        """Get a service by name. Returns None if not found."""
        return self._services.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services
class BackendServiceAdapter:
    """Adapter layer for integrating existing backend with GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self._setup_backend_services()
    
    def _setup_backend_services(self):
        """Set up backend service adapters."""
        print("[DEBUG] BackendServiceAdapter: Setting up backend services...", file=__import__("sys").stderr)
        # Adapt existing modules to service interfaces
        try:
            from scrape_engine import DatabaseManager, ScraperEngine, ScraperConfig
            print("[DEBUG] BackendServiceAdapter: Importing scrape_engine...", file=__import__("sys").stderr)
            self.service_registry.register("database", DatabaseManager())
            self.service_registry.register("scraper", ScraperEngine)
            self.service_registry.register("scraper_config", ScraperConfig)
            print("[DEBUG] BackendServiceAdapter: Registered scrape_engine services", file=__import__("sys").stderr)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: scrape_engine backend not available: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            from extraction import StructuredHTMLParser, EntityExtractor
            print("[DEBUG] BackendServiceAdapter: Importing extraction...", file=__import__("sys").stderr)
            self.service_registry.register("extractor", StructuredHTMLParser())
            self.service_registry.register("entity_extractor", EntityExtractor())
            print("[DEBUG] BackendServiceAdapter: Registered extraction services", file=__import__("sys").stderr)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: extraction backend not available: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            from sitemap_module import SitemapParser, URLHierarchy
            print("[DEBUG] BackendServiceAdapter: Importing sitemap_module...", file=__import__("sys").stderr)
            self.service_registry.register("sitemap", SitemapParser())
            self.service_registry.register("url_hierarchy", URLHierarchy())
            print("[DEBUG] BackendServiceAdapter: Registered sitemap services", file=__import__("sys").stderr)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: sitemap_module backend not available: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            from storage_manager import StorageManager
            print("[DEBUG] BackendServiceAdapter: Importing storage_manager...", file=__import__("sys").stderr)
            self.service_registry.register("storage", StorageManager())
            print("[DEBUG] BackendServiceAdapter: Registered storage_manager services", file=__import__("sys").stderr)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: storage_manager backend not available: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
    
    def get_research_service(self):
        """Get research service adapter."""
        # This would integrate research capabilities from existing backend
        return ResearchServiceAdapter(self.service_registry)
    
    def get_search_service(self):
        """Get search service adapter."""
        return SearchServiceAdapter(self.service_registry)
    
    def get_crawl_service(self):
        """Get crawl service adapter."""
        return CrawlServiceAdapter(self.service_registry)
    
    def get_extraction_service(self):
        """Get extraction service adapter."""
        return ExtractionServiceAdapter(self.service_registry)
    
    def get_document_service(self):
        """Get document service adapter."""
        return DocumentServiceAdapter(self.service_registry)
    
    def get_entity_service(self):
        """Get entity service adapter."""
        return EntityServiceAdapter(self.service_registry)
    
    def get_storage_service(self):
        """Get storage service adapter."""
        return StorageServiceAdapter(self.service_registry)
    
    def get_report_service(self):
        """Get report service adapter."""
        return ReportServiceAdapter(self.service_registry)
class ResearchServiceAdapter:
    """Research service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.db = service_registry.get("database")
        self.parser = NaturalLanguageParser()
    
    def create_research_session(self, query: str) -> Dict:
        """Create a research session from a query."""
        structured_query = self.parser.parse(query)
        
        # Store research session in database
        session_id = f"research_{datetime.now().timestamp()}"
        
        return {
            "id": session_id,
            "query": structured_query,
            "created": datetime.now().isoformat(),
            "status": "active"
        }
    
    def get_research_results(self, session_id: str) -> List[Dict]:
        """Get results for a research session."""
        # Would integrate with actual research engine
        return []
    
    def pause_research(self, session_id: str) -> bool:
        """Pause a research session."""
        return True
    
    def resume_research(self, session_id: str) -> bool:
        """Resume a research session."""
        return True
class SearchServiceAdapter:
    """Search service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.db = service_registry.get("database")
        self.parser = NaturalLanguageParser()
    
    def search_content(self, query: str, filters: Dict = None) -> List[Dict]:
        """Search content based on query and filters."""
        if not self.db:
            return []
        
        structured_query = self.parser.parse(query)
        
        # Perform searches based on query type
        results = []
        
        # Search exact phrase if specified
        if structured_query.exact_phrase:
            results.extend(self.db.search_exact_phrase(
                structured_query.exact_phrase,
                domain=structured_query.domains[0] if structured_query.domains else None,
                case_insensitive=True
            ))
        
        # Search literal substring if specified
        if structured_query.required_phrases and not structured_query.exact_phrase:
            for phrase in structured_query.required_phrases[:1]:  # Simple first phrase for demo
                results.extend(self.db.search_literal_substring(
                    phrase,
                    domain=structured_query.domains[0] if structured_query.domains else None,
                    case_insensitive=True
                ))
        
        return results
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on partial query."""
        # Would integrate with actual search suggestions
        return [
            f"Search for {partial_query}...",
            f"Scrape {partial_query} website...",
            f"Analyze {partial_query} content..."
        ]
class CrawlServiceAdapter:
    """Crawl service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.db = service_registry.get("database")
    
    def start_crawl(self, url: str, config: Dict = None) -> str:
        """Start a crawl job."""
        job_id = f"crawl_{datetime.now().timestamp()}"
        # Would integrate with actual crawler
        return job_id
    
    def get_crawl_status(self, job_id: str) -> Dict:
        """Get crawl job status."""
        return {
            "id": job_id,
            "status": "running",
            "progress": 50,
            "pages_crawled": 25,
            "total_pages": 50
        }
class ExtractionServiceAdapter:
    """Extraction service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.extractor = service_registry.get("extractor")
        self.entity_extractor = service_registry.get("entity_extractor")
    
    def extract_content(self, url: str, profile: str = "main_text") -> Dict:
        """Extract content from a URL using specified profile."""
        # Would integrate with actual extraction
        return {
            "url": url,
            "title": "Extracted Title",
            "text": "Extracted content would appear here...",
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        }
    
    def extract_entities(self, text: str, url: str = "") -> List[Dict]:
        """Extract entities from text."""
        if not self.entity_extractor:
            return []
        
        mentions = self.entity_extractor.process_text(text, "general", url)
        return [
            {
                "text": mention.text,
                "type": mention.entity_type,
                "confidence": mention.confidence,
                "section": mention.section.text if mention.section else ""
            }
            for mention in mentions
        ]
class DocumentServiceAdapter:
    """Document service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.db = service_registry.get("database")
    
    def get_documents(self, filters: Dict = None) -> List[Dict]:
        """Get list of documents."""
        if not self.db:
            return []
        
        # Would query database for documents
        return []
    
    def get_document_content(self, url: str) -> Dict:
        """Get full document content."""
        if not self.db:
            return {}
        
        # Would retrieve document from database
        return {}
class EntityServiceAdapter:
    """Entity service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.entity_extractor = service_registry.get("entity_extractor")
    
    def get_entities(self, filters: Dict = None) -> List[Dict]:
        """Get entities."""
        # Would retrieve entities from entity extractor
        return []
    
    def get_entity_details(self, entity_name: str) -> Dict:
        """Get detailed information about an entity."""
        # Would retrieve entity details
        return {
            "name": entity_name,
            "type": "person",  # placeholder
            "aliases": [],
            "mentions": []
        }
class StorageServiceAdapter:
    """Storage service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.storage = service_registry.get("storage")
    
    def get_storage_status(self) -> Dict:
        """Get storage usage and quota information."""
        if not self.storage:
            return {
                "total_bytes": 0,
                "hard_ceiling_bytes": 5 * 1024**3,
                "available_bytes": 5 * 1024**3,
                "pct_used": 0.0
            }
        
        return self.storage.get_usage_report()
    
    def get_storage_breakdown(self) -> Dict:
        """Get detailed storage breakdown."""
        if not self.storage:
            return {}
        
        return self.storage.get_usage_report()
class ReportServiceAdapter:
    """Report service adapter for GUI."""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.db = service_registry.get("database")
        self.storage = service_registry.get("storage")
    
    def generate_research_report(self, research_id: str, format: str = "markdown") -> str:
        """Generate a research report."""
        # Would generate actual report
        return f"# Research Report: {research_id}\n\nContent would appear here..."
    
    def generate_crawl_report(self, crawl_id: str, format: str = "markdown") -> str:
        """Generate a crawl report."""
        return f"# Crawl Report: {crawl_id}\n\nContent would appear here..."
    
    def generate_storage_report(self, format: str = "markdown") -> str:
        """Generate a storage report."""
        return f"# Storage Report\n\nContent would appear here..."
class KiloMainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__()
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("Kilo - Web Research Workstation")
        self.setMinimumSize(1200, 800)
        
        # Create central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
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
        
        # Load default workspace
        self.show_overview_workspace()
    
    def create_navigation_panel(self):
        """Create the left navigation panel."""
        # This will be implemented in a separate method
        pass
    
    def create_workspace_area(self):
        """Create the central workspace area."""
        # This will be implemented in a separate method
        pass
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = self.statusBar()
        
        self.storage_indicator = QLabel("Storage: 0/5 GiB (0%)")
        self.status_bar.addWidget(self.storage_indicator)
        
        self.progress_label = QLabel("Ready")
        self.status_bar.addWidget(self.progress_label)
        
        self.worker_count_label = QLabel("Workers: 0")
        self.status_bar.addWidget(self.worker_count_label)
    
    def create_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add command button
        self.command_button = QPushButton("Command")
        toolbar.addWidget(self.command_button)
        
        # Add research button
        self.research_button = QPushButton("New Research")
        toolbar.addWidget(self.research_button)
        
        # Add crawl button
        self.crawl_button = QPushButton("New Crawl")
        toolbar.addWidget(self.crawl_button)
        
        toolbar.addSeparator()
        
        # Add search button
        self.search_button = QPushButton("Search")
        toolbar.addWidget(self.search_button)
        
        # Add explore button
        self.explore_button = QPushButton("Explore")
        toolbar.addWidget(self.explore_button)
    
    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Research Session", self.show_new_research_dialog)
        file_menu.addAction("Save", self.save_session)
        file_menu.addAction("Export", self.export_results)
        file_menu.addSeparator()
        file_menu.addAction("Settings", self.show_settings_workspace)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # Workspace menu
        workspace_menu = menubar.addMenu("Workspaces")
        workspace_menu.addAction("Overview", self.show_overview_workspace)
        workspace_menu.addAction("Research", self.show_research_workspace)
        workspace_menu.addAction("Web Discovery", self.show_discovery_workspace)
        workspace_menu.addAction("Site Explorer", self.show_site_explorer_workspace)
        workspace_menu.addAction("Search", self.show_search_workspace)
        workspace_menu.addAction("Documents", self.show_documents_workspace)
        workspace_menu.addAction("Entities", self.show_entities_workspace)
        workspace_menu.addAction("Relationships", self.show_relationships_workspace)
        workspace_menu.addAction("Collections", self.show_collections_workspace)
        workspace_menu.addAction("Crawl Queue", self.show_crawl_queue_workspace)
        workspace_menu.addAction("Reports", self.show_reports_workspace)
        workspace_menu.addAction("Storage", self.show_storage_workspace)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about_dialog)
    
    def load_settings(self):
        """Load application settings."""
        settings = QSettings("Kilo", "ScrapeEngine")
        
        # Restore window geometry
        if settings.contains("windowGeometry"):
            self.restoreGeometry(settings.value("windowGeometry"))
        
        if settings.contains("windowState"):
            self.restoreState(settings.value("windowState"))
        
        # Restore last workspace
        self.current_workspace = settings.value("currentWorkspace", "overview")
    
    def save_settings(self):
        """Save application settings."""
        settings = QSettings("Kilo", "ScrapeEngine")
        
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("currentWorkspace", self.current_workspace)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        event.accept()
    
    # Workspace methods
    def show_overview_workspace(self):
        """Show the overview workspace."""
        self.current_workspace = "overview"
        self.update_status("Overview workspace shown")
    
    def show_research_workspace(self):
        """Show the research workspace."""
        self.current_workspace = "research"
        self.update_status("Research workspace shown")
    
    def show_discovery_workspace(self):
        """Show the web discovery workspace."""
        self.current_workspace = "discovery"
        self.update_status("Web Discovery workspace shown")
    
    def show_site_explorer_workspace(self):
        """Show the site explorer workspace."""
        self.current_workspace = "site_explorer"
        self.update_status("Site Explorer workspace shown")
    
    def show_search_workspace(self):
        """Show the search workspace."""
        self.current_workspace = "search"
        self.update_status("Search workspace shown")
    
    def show_documents_workspace(self):
        """Show the documents workspace."""
        self.current_workspace = "documents"
        self.update_status("Documents workspace shown")
    
    def show_entities_workspace(self):
        """Show the entities workspace."""
        self.current_workspace = "entities"
        self.update_status("Entities workspace shown")
    
    def show_relationships_workspace(self):
        """Show the relationships workspace."""
        self.current_workspace = "relationships"
        self.update_status("Relationships workspace shown")
    
    def show_collections_workspace(self):
        """Show the collections workspace."""
        self.current_workspace = "collections"
        self.update_status("Collections workspace shown")
    
    def show_crawl_queue_workspace(self):
        """Show the crawl queue workspace."""
        self.current_workspace = "crawl_queue"
        self.update_status("Crawl Queue workspace shown")
    
    def show_reports_workspace(self):
        """Show the reports workspace."""
        self.current_workspace = "reports"
        self.update_status("Reports workspace shown")
    
    def show_storage_workspace(self):
        """Show the storage workspace."""
        self.current_workspace = "storage"
        self.update_status("Storage workspace shown")
    
    def update_status(self, message: str):
        """Update status bar message."""
        self.progress_label.setText(message)
        
        # Update storage indicator if available
        storage_service = self.backend.get_storage_service()
        if storage_service:
            status = storage_service.get_storage_status()
            self.storage_indicator.setText(
                f"Storage: {status.get('available_bytes', 0) / (1024**3):.1f}/{status.get('hard_ceiling_bytes', 0) / (1024**3):.0f} GiB "
                f"({status.get('pct_used', 0):.1f}%)"
            )
class CommandInterface(QWidget):
    """Universal command/search interface."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__()
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        self.parser = NaturalLanguageParser()
        self.init_ui()
    
    def init_ui(self):
        """Initialize command interface UI."""
        layout = QVBoxLayout(self)
        
        # Command input area
        command_frame = QFrame()
        command_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        command_layout = QVBoxLayout(command_frame)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter natural-language command (e.g., 'Research Ursula K. Le Guin')")
        self.command_input.returnPressed.connect(self.execute_command)
        
        # Command suggestions
        self.suggestions_list = QListWidget()
        self.suggestions_list.itemClicked.connect(self.suggestion_clicked)
        
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.suggestions_list)
        
        # Query preview area
        self.query_preview = QTextEdit()
        self.query_preview.setPlaceholderText("Query interpretation preview...")
        self.query_preview.setMaximumHeight(150)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.execute_command)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_command)
        self.cancel_button.setEnabled(False)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_command)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.clear_button)
        
        # Assemble layout
        layout.addWidget(command_frame)
        layout.addWidget(QLabel("Query Interpretation:"))
        layout.addWidget(self.query_preview)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect suggestions
        self.command_input.textChanged.connect(self.update_suggestions)
    
    def update_suggestions(self):
        """Update command suggestions based on input."""
        text = self.command_input.text().strip()
        if text:
            suggestions = self.backend.get_search_service().get_search_suggestions(text)
            self.suggestions_list.clear()
            for suggestion in suggestions:
                item = QListWidgetItem(suggestion)
                self.suggestions_list.addItem(item)
        else:
            self.suggestions_list.clear()
    
    def suggestion_clicked(self, item):
        """Handle suggestion item click."""
        self.command_input.setText(item.text())
        self.update_suggestions()
    
    def execute_command(self):
        """Execute the current command."""
        command = self.command_input.text().strip()
        if not command:
            return
        
        # Parse the command
        try:
            structured_query = self.parser.parse(command)
            
            # Show query preview
            preview_text = self.format_query_preview(structured_query)
            self.query_preview.setText(preview_text)
            
            # Execute based on command type
            if structured_query.subject.lower() in ["research", "find", "search"]:
                self.execute_research_command(structured_query)
            elif structured_query.subject.lower() in ["scrape", "crawl"]:
                self.execute_crawl_command(structured_query)
            elif structured_query.subject.lower() in ["find articles", "find documents"]:
                self.execute_search_command(structured_query)
            elif structured_query.subject.lower() in ["explore", "discover"]:
                self.execute_explore_command(structured_query)
            else:
                self.execute_general_command(structured_query)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error parsing command: {str(e)}")
    
    def format_query_preview(self, query: StructuredQuery) -> str:
        """Format structured query for preview."""
        preview = []
        preview.append(f"Subject: {query.subject}")
        
        if query.required_phrases:
            preview.append(f"Required phrases: {', '.join(query.required_phrases)}")
        
        if query.excluded_phrases:
            preview.append(f"Excluded phrases: {', '.join(query.excluded_phrases)}")
        
        if query.exact_phrase:
            preview.append(f"Exact phrase: {query.exact_phrase}")
        
        if query.domains:
            preview.append(f"Domains: {', '.join(query.domains)}")
        
        if query.content_types:
            preview.append(f"Content types: {', '.join(query.content_types)}")
        
        if query.profile:
            preview.append(f"Profile: {query.profile.value}")
        
        preview.append(f"Max results: {query.max_results}")
        preview.append(f"Max depth: {query.max_depth}")
        
        return "\n".join(preview)
    
    def execute_research_command(self, query: StructuredQuery):
        """Execute a research command."""
        self.update_status(f"Starting research on: {query.subject}")
        
        # Create research session
        session = self.backend.get_research_service().create_research_session(query)
        
        # Update UI to show research session
        print(f"Research session created: {session}")
    
    def execute_crawl_command(self, query: StructuredQuery):
        """Execute a crawl command."""
        self.update_status(f"Starting crawl on: {query.subject}")
        
        # Would start crawl using backend service
        print(f"Crawl command: {query.subject}")
    
    def execute_search_command(self, query: StructuredQuery):
        """Execute a search command."""
        self.update_status(f"Searching for: {query.subject}")
        
        # Use search service to find content
        results = self.backend.get_search_service().search_content(query.subject)
        
        print(f"Found {len(results)} results")
    
    def execute_explore_command(self, query: StructuredQuery):
        """Execute an explore command."""
        self.update_status(f"Exploring: {query.subject}")
        
        print(f"Explore command: {query.subject}")
    
    def execute_general_command(self, query: StructuredQuery):
        """Execute a general command."""
        self.update_status(f"Executing command: {query.subject}")
        
        print(f"General command: {query.subject}")
    
    def cancel_command(self):
        """Cancel the current command."""
        self.update_status("Command cancelled")
        self.cancel_button.setEnabled(False)
    
    def clear_command(self):
        """Clear the current command."""
        self.command_input.clear()
        self.query_preview.clear()
        self.update_status("Command cleared")
    
    def update_status(self, message: str):
        """Update status message."""
        print(f"Command Interface: {message}")  # For now, just print to console
class OverviewWorkspace(QWidget):
    """Overview workspace widget."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__()
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        self.init_ui()
    
    def init_ui(self):
        """Initialize overview workspace UI."""
        layout = QVBoxLayout(self)
        
        # Overview content
        overview_text = QTextEdit()
        overview_text.setReadOnly(True)
        overview_text.setText(self.get_overview_text())
        
        layout.addWidget(QLabel("Overview:"))
        layout.addWidget(overview_text)
    
    def get_overview_text(self) -> str:
        """Get overview text from backend."""
        storage_service = self.backend.get_storage_service()
        
        overview = []
        overview.append("=== Kilo Web Research Workstation Overview ===\n")
        
        if storage_service:
            status = storage_service.get_storage_status()
            overview.append(f"Storage Status: {status.get('pct_used', 0):.1f}% used ({status.get('available_bytes', 0) / (1024**3):.1f} GiB available)")
        
        overview.append(f"Total Usage: {storage_service.get_storage_status().get('total_bytes', 0) / (1024**3):.1f} GiB")
        overview.append("\nActive Sessions:")
        overview.append("- Research sessions: 0")
        overview.append("- Crawl jobs: 0")
        overview.append("- Search queries: 0")
        
        overview.append("\nRecent Activity:")
        overview.append("- Last crawl: Never")
        overview.append("- Last search: Never")
        overview.append("- Last extraction: Never")
        
        return "\n".join(overview)
class ResearchWorkspace(QWidget):
    """Research workspace widget."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__()
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        self.init_ui()
    
    def init_ui(self):
        """Initialize research workspace UI."""
        layout = QVBoxLayout(self)
        
        # Research form
        form_layout = QFormLayout()
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter research subject or topic...")
        
        self.profile_combo = QComboBox()
        for profile in CollectionProfile:
            self.profile_combo.addItem(profile.value)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Auto", "Google", "DuckDuckGo", "Bing", "Custom"])
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com (leave empty for all domains)")
        
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(1, 10)
        self.max_depth_spin.setValue(2)
        
        self.results_list = QListWidget()
        
        form_layout.addRow("Subject:", self.subject_input)
        form_layout.addRow("Profile:", self.profile_combo)
        form_layout.addRow("Provider:", self.provider_combo)
        form_layout.addRow("Domain:", self.domain_input)
        form_layout.addRow("Max Depth:", self.max_depth_spin)
        
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.results_list)
        
        # Button row
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Research")
        self.start_button.clicked.connect(self.start_research)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_research)
        self.pause_button.setEnabled(False)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_research)
        self.resume_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_research)
        self.cancel_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def start_research(self):
        """Start research with current inputs."""
        subject = self.subject_input.text().strip()
        if not subject:
            return
        
        # Create query from inputs
        query = f"Research {subject}"
        if self.domain_input.text().strip():
            query += f" --domain {self.domain_input.text().strip()}"
        
        query += f" --depth {self.max_depth_spin.value()}"
        
        # Start research
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        self.backend.get_research_service().create_research_session(query)
        self.update_status(f"Research started on: {subject}")
    
    def pause_research(self):
        """Pause research."""
        self.update_status("Research paused")
    
    def resume_research(self):
        """Resume research."""
        self.update_status("Research resumed")
    
    def cancel_research(self):
        """Cancel research."""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        self.update_status("Research cancelled")
    
    def update_status(self, message: str):
        """Update status message."""
        print(f"Research: {message}")
class SiteExplorerWorkspace(QWidget):
    """Site Explorer workspace with four synchronized views."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__()
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        self.init_ui()
    
    def init_ui(self):
        """Initialize site explorer workspace UI."""
        main_layout = QHBoxLayout(self)
        
        # Create splitter for adjustable panes
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Domain/Sitemap tree
        domain_panel = QWidget()
        domain_layout = QVBoxLayout(domain_panel)
        
        domain_layout.addWidget(QLabel("Domain/Sitemap Tree:"))
        
        self.domain_tree = QTreeView()
        self.domain_tree.setHeaderHidden(False)
        domain_layout.addWidget(self.domain_tree)
        
        # Center panel - URL Path tree
        path_panel = QWidget()
        path_layout = QVBoxLayout(path_panel)
        
        path_layout.addWidget(QLabel("URL Path Tree:"))
        
        self.path_tree = QTreeView()
        self.path_tree.setHeaderHidden(False)
        path_layout.addWidget(self.path_tree)
        
        # Right panel - URL Inventory
        inventory_panel = QWidget()
        inventory_layout = QVBoxLayout(inventory_panel)
        
        inventory_layout.addWidget(QLabel("URL Inventory:"))
        
        self.url_inventory = QTableView()
        self.url_inventory.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.url_inventory.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.url_inventory.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Set up table columns
        headers = ["URL", "Title", "Domain", "Path", "Discovery Method", 
                  "Sitemap Membership", "Crawl Status", "HTTP Status"]
        self.url_inventory.setColumnCount(len(headers))
        self.url_inventory.setHorizontalHeaderLabels(headers)
        
        inventory_layout.addWidget(self.url_inventory)
        
        # Add panels to splitter
        splitter.addWidget(domain_panel)
        splitter.addWidget(path_panel)
        splitter.addWidget(inventory_panel)
        
        # Set initial sizes
        splitter.setSizes([300, 300, 400])
        
        main_layout.addWidget(splitter)
        
        # Set up item models for the views
        self.setup_models()
    
    def setup_models(self):
        """Set up data models for the views."""
        # Domain model (placeholder)
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        
        self.domain_model = QStandardItemModel()
        self.domain_model.setHorizontalHeaderLabels(["Domain", "Sitemaps", "URLs"])
        
        # Add example domain
        domain_item = QStandardItem("example.com")
        domain_item.setChild(0, QStandardItem("sitemap.xml"))
        domain_item.setChild(0, 1, QStandardItem("/"))
        self.domain_model.appendRow(domain_item)
        
        self.domain_tree.setModel(self.domain_model)
        
        # Path model (placeholder)
        self.path_model = QStandardItemModel()
        self.path_model.setHorizontalHeaderLabels(["Path", "Type", "Status"])
        
        path_item = QStandardItem("docs/api/")
        path_item.setChild(0, QStandardItem("directory"))
        path_item.setChild(0, 1, QStandardItem("visited"))
        self.path_model.appendRow(path_item)
        
        self.path_tree.setModel(self.path_model)
        
        # Inventory model (placeholder)
        self.inventory_model = QStandardItemModel()
        headers = ["URL", "Title", "Domain", "Path", "Discovery Method", 
                  "Sitemap Membership", "Crawl Status", "HTTP Status"]
        self.inventory_model.setHorizontalHeaderLabels(headers)
        
        inventory_item = QStandardItem("https://example.com/docs/api/")
        inventory_item.setChild(0, QStandardItem("API Documentation"))
        inventory_item.setChild(0, 1, QStandardItem("example.com"))
        inventory_item.setChild(0, 2, QStandardItem("/docs/api/"))
        inventory_item.setChild(0, 3, QStandardItem("internal_link"))
        inventory_item.setChild(0, 4, QStandardItem("sitemap.xml"))
        inventory_item.setChild(0, 5, QStandardItem("completed"))
        inventory_item.setChild(0, 6, QStandardItem("200"))
        
        self.inventory_model.appendRow(inventory_item)
        
        self.url_inventory.setModel(self.inventory_model)
    
    def synchronize_views(self, selected_index):
        """Synchronize views based on selection."""
        # Implementation would synchronize the four views
        pass
def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Create service registry and backend
    service_registry = ServiceRegistry()
    backend = BackendServiceAdapter(service_registry)
    
    # Create main window
    main_window = KiloMainWindow(service_registry)
    
    # Create and set up command interface
    command_interface = CommandInterface(service_registry)
    
    # Create workspaces
    overview_workspace = OverviewWorkspace(service_registry)
    research_workspace = ResearchWorkspace(service_registry)
    site_explorer_workspace = SiteExplorerWorkspace(service_registry)
    
    # Show main window
    main_window.show()
    
    # Run application
    return app.exec()
if __name__ == "__main__":
    sys.exit(main())
