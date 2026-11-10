"""
Search View
Full search interface with multiple search modes and filters.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTextEdit, QPushButton, QFrame, QListWidget, QTabWidget, QTableView,
    QSplitter
)
from PySide6.QtCore import Qt

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter

class SearchView(QWidget):
    """Search workspace for advanced search functionality."""
    
    def __init__(self, service_registry: ServiceRegistry, backend: BackendServiceAdapter):
        super().__init__()
        self.service_registry = service_registry
        self.backend = backend
        
        self.parser = service_registry.get("natural_language_parser_class")()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize search UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Search")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Main search area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Search interface
        search_panel = self.create_search_panel()
        main_splitter.addWidget(search_panel)
        
        # Right panel - Results
        results_panel = self.create_results_panel()
        main_splitter.addWidget(results_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([300, 500])
        
        layout.addWidget(main_splitter)
    
    def create_search_panel(self):
        """Create the left search panel."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Search mode section
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(15, 15, 15, 15)
        
        # Search mode header
        mode_label = QLabel("Search Mode")
        mode_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        search_layout.addWidget(mode_label)
        
        # Search mode tabs
        self.mode_tabs = QTabWidget()
        
        # Natural language tab
        nl_tab = self.create_natural_language_tab()
        self.mode_tabs.addTab(nl_tab, "Natural Language")
        
        # Exact phrase tab
        exact_tab = self.create_exact_phrase_tab()
        self.mode_tabs.addTab(exact_tab, "Exact Phrase")
        
        # Substring tab
        sub_tab = self.create_substring_tab()
        self.mode_tabs.addTab(sub_tab, "Substring")
        
        # Regex tab
        regex_tab = self.create_regex_tab()
        self.mode_tabs.addTab(regex_tab, "Regular Expression")
        
        search_layout.addWidget(self.mode_tabs)
        
        # Search filters
        filter_frame = QFrame()
        filter_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        
        filter_title = QLabel("Search Filters")
        filter_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        filter_layout.addWidget(filter_title)
        
        # Filter controls
        filters_layout = QHBoxLayout()
        
        domain_input = QLineEdit()
        domain_input.setPlaceholderText("Domain...")
        filters_layout.addWidget(QLabel("Domain:"))
        filters_layout.addWidget(domain_input)
        
        language_combo = QComboBox()
        language_combo.addItems(["Any Language", "English", "French", "German", "Spanish"])
        filters_layout.addWidget(QLabel("Language:"))
        filters_layout.addWidget(language_combo)
        
        date_range_input = QLineEdit()
        date_range_input.setPlaceholderText("Date range...")
        filters_layout.addWidget(QLabel("Date Range:"))
        filters_layout.addWidget(date_range_input)
        
        content_type_combo = QComboBox()
        content_type_combo.addItems(["Any Type", "HTML", "Text", "PDF", "JSON"])
        filters_layout.addWidget(QLabel("Content Type:"))
        filters_layout.addWidget(content_type_combo)
        
        filter_layout.addLayout(filters_layout)
        
        search_layout.addWidget(filter_frame)
        
        # Search actions
        action_layout = QHBoxLayout()
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1e6391;
            }
        """)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7a89;
            }
        """)
        
        action_layout.addWidget(self.search_button)
        action_layout.addWidget(self.clear_button)
        
        search_layout.addLayout(action_layout)
        
        panel_layout.addWidget(search_frame)
        
        return panel
    
    def create_natural_language_tab(self):
        """Create natural language search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        input_label = QLabel("Enter natural-language query:")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)
        
        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("e.g., 'Find technical articles about ESP32 firmware updates'")
        layout.addWidget(self.nl_input)
        
        preview_label = QLabel("Query Preview:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(preview_label)
        
        self.nl_preview = QTextEdit()
        self.nl_preview.setPlaceholderText("Query will be parsed here...")
        self.nl_preview.setMaximumHeight(100)
        self.nl_preview.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.nl_preview.setReadOnly(True)
        layout.addWidget(self.nl_preview)
        
        return tab
    
    def create_exact_phrase_tab(self):
        """Create exact phrase search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        input_label = QLabel("Exact phrase to search:")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)
        
        self.exact_input = QLineEdit()
        self.exact_input.setPlaceholderText('e.g., "ambient noise floor"')
        layout.addWidget(self.exact_input)
        
        return tab
    
    def create_substring_tab(self):
        """Create substring search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        input_label = QLabel("Text substring to search:")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)
        
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText('e.g., "AttributeError"')
        layout.addWidget(self.sub_input)
        
        case_label = QLabel("Case Sensitive:")
        case_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(case_label)
        
        self.case_combo = QComboBox()
        self.case_combo.addItems(["Yes", "No"])
        layout.addWidget(self.case_combo)
        
        return tab
    
    def create_regex_tab(self):
        """Create regex search tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        input_label = QLabel("Regular expression pattern:")
        input_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(input_label)
        
        self.regex_input = QLineEdit()
        self.regex_input.setPlaceholderText('e.g., "0x[0-9A-Fa-f]+"')
        layout.addWidget(self.regex_input)
        
        return tab
    
    def create_results_panel(self):
        """Create the right results panel."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Results header
        results_title = QLabel("Search Results")
        results_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        panel_layout.addWidget(results_title)
        
        # Results table
        self.results_table = QTableView()
        self.results_table.setEditTriggers(QTableView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableView.SelectRows)
        self.results_table.setSelectionMode(QTableView.SingleSelection)
        self.setup_results_table()
        panel_layout.addWidget(self.results_table)
        
        # Result details
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(15, 15, 15, 15)
        
        details_title = QLabel("Result Details")
        details_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        details_layout.addWidget(details_title)
        
        self.result_details = QTextEdit()
        self.result_details.setPlaceholderText("Select a result to see details...")
        self.result_details.setReadOnly(True)
        self.result_details.setMaximumHeight(150)
        details_layout.addWidget(self.result_details)
        
        panel_layout.addWidget(details_frame)
        
        return panel
    
    def setup_results_table(self):
        """Set up the results table model."""
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        
        self.results_model = QStandardItemModel()
        headers = ["Title", "URL", "Match", "Context", "Position", "Relevance"]
        self.results_model.setHorizontalHeaderLabels(headers)
        
        # Add example results
        example_item = QStandardItem("API Documentation")
        example_item.setChild(0, QStandardItem("https://example.com/docs/api/"))
        example_item.setChild(0, 2, QStandardItem("API documentation"))
        example_item.setChild(0, 3, QStandardItem("API documentation for ESP32"))
        example_item.setChild(0, 4, QStandardItem("42"))
        example_item.setChild(0, 5, QStandardItem("0.95"))
        
        self.results_model.appendRow(example_item)
        
        self.results_table.setModel(self.results_model)
        
        # Connect selection
        self.results_table.selectionModel().selectionChanged.connect(self.on_result_selected)
    
    def on_result_selected(self, selected, deselected):
        """Handle result selection changes."""
        # Update result details
        if self.results_table.selectionModel().hasSelection():
            index = self.results_table.selectionModel().currentIndex()
            if index.isValid():
                model = self.results_table.model()
                item = model.itemFromIndex(index)
                if item:
                    self.update_result_details(item)
    
    def update_result_details(self, item):
        """Update result details display."""
        # Example details - would integrate with actual result data
        details = f"""
Title: {item.text()}
URL: https://example.com/docs/api/
Match: API documentation
Context: API documentation for ESP32 firmware
Position: 42 characters from start
Relevance: 0.95
Source: example.com
Date: 2024-01-15
Status: 200 OK
        """.strip()
        
        self.result_details.setText(details)
    
    def perform_search(self):
        """Perform search based on current inputs."""
        # Get search parameters
        search_mode = self.mode_tabs.tabText(self.mode_tabs.currentIndex())
        
        if search_mode == "Natural Language":
            self.perform_natural_language_search()
        elif search_mode == "Exact Phrase":
            self.perform_exact_phrase_search()
        elif search_mode == "Substring":
            self.perform_substring_search()
        elif search_mode == "Regular Expression":
            self.perform_regex_search()
    
    def perform_natural_language_search(self):
        """Perform natural language search."""
        query = self.nl_input.text().strip()
        if not query:
            return
        
        try:
            # Parse the query
            structured_query = self.parser.parse(query)
            
            # Update preview
            preview = f"Subject: {structured_query.subject}\n"
            if structured_query.exact_phrase:
                preview += f"Exact: {structured_query.exact_phrase}\n"
            if structured_query.required_phrases:
                preview += f"Required: {', '.join(structured_query.required_phrases)}\n"
            
            self.nl_preview.setText(preview)
            
            # Perform search using backend
            results = self.backend.get_search_service().search_content(query)
            
            self.update_results_table(results)
            
        except Exception as e:
            print(f"Search error: {e}")
    
    def perform_exact_phrase_search(self):
        """Perform exact phrase search."""
        phrase = self.exact_input.text().strip()
        if not phrase:
            return
        
        # Use search service to find exact phrase matches
        results = self.backend.get_search_service().search_content(f'"{phrase}"')
        
        self.update_results_table(results)
    
    def perform_substring_search(self):
        """Perform substring search."""
        substring = self.sub_input.text().strip()
        if not substring:
            return
        
        # Determine case sensitivity
        case_sensitive = self.case_combo.currentText() == "Yes"
        
        # Use search service to find substring matches
        results = self.backend.get_search_service().search_content(substring)
        
        self.update_results_table(results)
    
    def perform_regex_search(self):
        """Perform regex search."""
        pattern = self.regex_input.text().strip()
        if not pattern:
            return
        
        # This would integrate with regex search functionality
        # For now, show a message
        QMessageBox.information(
            self,
            "Regex Search",
            f"Regex search for pattern: {pattern}\n\nNote: This feature requires integration with backend regex search."
        )
    
    def update_results_table(self, results):
        """Update the results table with search results."""
        if not results:
            self.results_model.clear()
            self.results_model.setHorizontalHeaderLabels(["Title", "URL", "Match", "Context", "Position", "Relevance"])
            return
        
        self.results_model.clear()
        self.results_model.setHorizontalHeaderLabels(["Title", "URL", "Match", "Context", "Position", "Relevance"])
        
        for result in results:
            title_item = QStandardItem(result.get("title", "") or "")
            url_item = QStandardItem(result.get("url", "") or "")
            match_item = QStandardItem(result.get("match", "") or "")
            context_item = QStandardItem(f"{result.get('context_before', '')} ... {result.get('context_after', '')}")
            position_item = QStandardItem(str(result.get("position", "")) or "")
            relevance_item = QStandardItem(str(result.get("relevance", 0.0)) or "0.0")
            
            result_item = QStandardItem()
            result_item.appendRow([title_item, url_item, match_item, context_item, position_item, relevance_item])
            self.results_model.appendRow(result_item)
    
    def clear_search(self):
        """Clear search results."""
        self.nl_input.clear()
        self.exact_input.clear()
        self.sub_input.clear()
        self.regex_input.clear()
        
        self.nl_preview.clear()
        
        self.results_model.clear()
        self.result_details.clear()

from PySide6.QtWidgets import QMessageBox