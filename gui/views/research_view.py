"""
Research View
Dedicated research workspace with subject/topic input and profile selection.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QFormLayout, QTextEdit, QPushButton, QTabWidget, QListWidget,
    QSplitter, QFrame, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QTimer

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter
from extraction import CollectionProfile

class ResearchView(QWidget):
    """Research workspace for managing research sessions and results."""
    
    def __init__(self, service_registry: ServiceRegistry, backend: BackendServiceAdapter):
        super().__init__()
        self.service_registry = service_registry
        self.backend = backend
        
        self.parser = service_registry.get("natural_language_parser_class")()
        self.current_session = None
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_session_display)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize research workspace UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Research Workspace")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Research configuration
        left_panel = self.create_research_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Results and visualization
        right_panel = self.create_results_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([350, 500])
        
        layout.addWidget(main_splitter)
        
        # Status bar
        self.create_status_bar(layout)
    
    def create_research_panel(self):
        """Create the left research configuration panel."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Research configuration section
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(10)
        
        config_title = QLabel("Research Configuration")
        config_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        config_layout.addWidget(config_title)
        
        # Form layout for research parameters
        form_layout = QFormLayout()
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter research subject or topic...")
        self.subject_input.textChanged.connect(self.update_command_preview)
        
        self.profile_combo = QComboBox()
        for profile in CollectionProfile:
            self.profile_combo.addItem(f"{profile.value.title().replace('_', ' ')}")
        self.profile_combo.currentIndexChanged.connect(self.update_command_preview)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Auto", "Google", "DuckDuckGo", "Bing", "Custom"])
        self.provider_combo.currentIndexChanged.connect(self.update_command_preview)
        
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com (leave empty for all domains)")
        self.domain_input.textChanged.connect(self.update_command_preview)
        
        self.max_depth_spin = QComboBox()
        self.max_depth_spin.addItems(["1", "2", "3", "4", "5", "Deep (Unlimited)"])
        self.max_depth_spin.currentIndexChanged.connect(self.update_command_preview)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Any Language", "English", "French", "German", "Spanish", "Chinese", "Japanese"])
        self.language_combo.currentIndexChanged.connect(self.update_command_preview)
        
        self.primary_sources_check = QComboBox()
        self.primary_sources_check.addItems(["Normal", "Primary Sources Only", "Scholarly Sources Only"])
        self.primary_sources_check.currentIndexChanged.connect(self.update_command_preview)
        
        form_layout.addRow("Subject/Topic:", self.subject_input)
        form_layout.addRow("Collection Profile:", self.profile_combo)
        form_layout.addRow("Search Provider:", self.provider_combo)
        form_layout.addRow("Domain Restriction:", self.domain_input)
        form_layout.addRow("Crawl Depth:", self.max_depth_spin)
        form_layout.addRow("Language:", self.language_combo)
        form_layout.addRow("Source Preference:", self.primary_sources_check)
        
        config_layout.addLayout(form_layout)
        
        # Research actions
        action_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Research")
        self.start_button.clicked.connect(self.start_research)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1e6391;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_research)
        self.pause_button.setEnabled(False)
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_research)
        self.resume_button.setEnabled(False)
        self.resume_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_research)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #962d22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.pause_button)
        action_layout.addWidget(self.resume_button)
        action_layout.addWidget(self.cancel_button)
        
        config_layout.addLayout(action_layout)
        
        panel_layout.addWidget(config_frame)
        
        # Command preview section
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(15, 15, 15, 15)
        
        preview_title = QLabel("Command Preview")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        preview_layout.addWidget(preview_title)
        
        self.command_preview = QTextEdit()
        self.command_preview.setPlaceholderText("Parsed command will appear here...")
        self.command_preview.setMaximumHeight(150)
        self.command_preview.setStyleSheet("font-family: monospace; font-size: 12px;")
        self.command_preview.setReadOnly(True)
        preview_layout.addWidget(self.command_preview)
        
        panel_layout.addWidget(preview_frame)
        
        return panel
    
    def create_results_panel(self):
        """Create the right results panel."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Results header
        results_title = QLabel("Research Results")
        results_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        panel_layout.addWidget(results_title)
        
        # Results tabs
        self.results_tabs = QTabWidget()
        
        # Overview tab
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        self.overview_text.setPlaceholderText("Research overview will appear here...")
        overview_layout.addWidget(self.overview_text)
        
        self.results_tabs.addTab(overview_widget, "Overview")
        
        # Sources tab
        sources_widget = QWidget()
        sources_layout = QVBoxLayout(sources_widget)
        
        self.sources_list = QListWidget()
        sources_layout.addWidget(self.sources_list)
        
        self.results_tabs.addTab(sources_widget, "Sources")
        
        # Findings tab
        findings_widget = QWidget()
        findings_layout = QVBoxLayout(findings_widget)
        
        self.findings_text = QTextEdit()
        self.findings_text.setReadOnly(True)
        self.findings_text.setPlaceholderText("Key findings will appear here...")
        findings_layout.addWidget(self.findings_text)
        
        self.results_tabs.addTab(findings_widget, "Findings")
        
        panel_layout.addWidget(self.results_tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        panel_layout.addWidget(self.progress_bar)
        
        return panel
    
    def create_status_bar(self, parent_layout):
        """Create status bar and add to parent layout."""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        status_layout.addWidget(self.status_label)
        
        # Session info
        self.session_info_label = QLabel("No active session")
        self.session_info_label.setStyleSheet("color: #3498db; font-weight: bold;")
        status_layout.addWidget(self.session_info_label)
        
        # Progress info
        self.progress_info_label = QLabel("")
        self.progress_info_label.setStyleSheet("color: #f39c12;")
        status_layout.addWidget(self.progress_info_label)
        
        parent_layout.addWidget(status_frame)
    
    def update_command_preview(self):
        """Update the command preview based on current inputs."""
        subject = self.subject_input.text().strip()
        if not subject:
            self.command_preview.clear()
            return
        
        # Build command string
        command_parts = [f"Research {subject}"]
        
        if self.domain_input.text().strip():
            command_parts.append(f"--domain {self.domain_input.text().strip()}")
        
        depth_map = {
            0: "--deep",
            1: "--depth 1",
            2: "--depth 2", 
            3: "--depth 3",
            4: "--depth 4",
            5: "--depth 5"
        }
        
        if self.max_depth_spin.currentIndex() in depth_map:
            command_parts.append(depth_map[self.max_depth_spin.currentIndex()])
        
        if self.language_combo.currentIndex() > 0:
            lang = self.language_combo.currentText()
            if lang != "Any Language":
                command_parts.append(f"--language {lang.lower()}")
        
        if self.primary_sources_check.currentIndex() > 0:
            source_type = self.primary_sources_check.currentText().lower().replace(" ", "-")
            command_parts.append(f"--primary-sources" if "primary" in source_type else "")
        
        command = " ".join(command_parts)
        self.command_preview.setText(command)
    
    def start_research(self):
        """Start research with current configuration."""
        subject = self.subject_input.text().strip()
        if not subject:
            return
        
        # Build command
        command_parts = [f"Research {subject}"]
        
        if self.domain_input.text().strip():
            command_parts.append(f"--domain {self.domain_input.text().strip()}")
        
        if self.max_depth_spin.currentIndex() > 0:
            if self.max_depth_spin.currentIndex() == 0:
                command_parts.append("--deep")
            else:
                command_parts.append(f"--depth {self.max_depth_spin.currentIndex()}")
        
        if self.language_combo.currentIndex() > 0:
            lang = self.language_combo.currentText().lower()
            if lang != "any language":
                command_parts.append(f"--language {lang}")
        
        command = " ".join(command_parts)
        
        # Start research
        try:
            # Use research service to create session
            session = self.backend.get_research_service().create_research_session(command)
            
            self.current_session = session
            
            # Update UI
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            
            self.update_status(f"Research started: {subject}")
            self.session_info_label.setText(f"Session: {session.get('id', 'Unknown')}")
            
            # Update overview
            self.overview_text.setText(f"Research session created successfully.\n\n")
            self.overview_text.append(f"Subject: {subject}")
            self.overview_text.append(f"Command: {command}")
            self.overview_text.append(f"Profile: {self.profile_combo.currentText()}")
            self.overview_text.append(f"Created: {session.get('created', 'Unknown time')}")
            
        except Exception as e:
            self.update_status(f"Error starting research: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start research: {str(e)}")
    
    def pause_research(self):
        """Pause current research."""
        if self.current_session:
            try:
                self.backend.get_research_service().pause_research(self.current_session.get('id'))
                self.update_status("Research paused")
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(True)
            except Exception as e:
                self.update_status(f"Error pausing research: {str(e)}")
    
    def resume_research(self):
        """Resume current research."""
        if self.current_session:
            try:
                self.backend.get_research_service().resume_research(self.current_session.get('id'))
                self.update_status("Research resumed")
                self.pause_button.setEnabled(True)
                self.resume_button.setEnabled(False)
            except Exception as e:
                self.update_status(f"Error resuming research: {str(e)}")
    
    def cancel_research(self):
        """Cancel current research."""
        if self.current_session:
            self.update_status("Research cancelled")
            
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            
            self.current_session = None
            self.session_info_label.setText("No active session")
            self.overview_text.clear()
    
    def update_session_display(self):
        """Update session display periodically."""
        if self.current_session:
            # Update progress information
            # This would integrate with actual research progress updates
            self.update_status(f"Session active: {self.current_session.get('id', 'Unknown')}")
    
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.setText(message)
        print(f"Research Status: {message}")