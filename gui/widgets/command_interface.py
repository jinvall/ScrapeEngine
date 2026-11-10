"""
Command Interface Widget
Universal command and search interface for the GUI.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QTextEdit, QPushButton, QFrame, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter

class CommandInterface(QWidget):
    """Universal command/search interface widget."""
    
    def __init__(self, service_registry: ServiceRegistry, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        
        self.parser = service_registry.get("natural_language_parser_class")()
        self.current_command = None
        self.command_timer = QTimer()
        self.command_timer.timeout.connect(self.check_command_status)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize command interface UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Command input section
        command_frame = QFrame()
        command_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        command_layout = QVBoxLayout(command_frame)
        command_layout.setContentsMargins(15, 15, 15, 15)
        
        # Input header
        input_header = QLabel("Command Input")
        input_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        command_layout.addWidget(input_header)
        
        # Command input field
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Enter natural-language command (e.g., 'Research Ursula K. Le Guin')"
        )
        self.command_input.textChanged.connect(self.on_command_text_changed)
        self.command_input.returnPressed.connect(self.execute_command)
        command_layout.addWidget(self.command_input)
        
        # Suggestions list
        suggestions_label = QLabel("Suggestions:")
        suggestions_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        command_layout.addWidget(suggestions_label)
        
        self.suggestions_list = QListWidget()
        self.suggestions_list.itemClicked.connect(self.on_suggestion_clicked)
        self.suggestions_list.setMaximumHeight(100)
        command_layout.addWidget(self.suggestions_list)
        
        command_layout.addSpacing(10)
        
        # Query preview section
        preview_label = QLabel("Query Preview:")
        preview_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        command_layout.addWidget(preview_label)
        
        self.query_preview = QTextEdit()
        self.query_preview.setPlaceholderText("Query interpretation preview will appear here...")
        self.query_preview.setMaximumHeight(120)
        self.query_preview.setStyleSheet("font-family: monospace; font-size: 11px;")
        command_layout.addWidget(self.query_preview)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.execute_command)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_command)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #962d22;
            }
        """)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_command)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7a89;
            }
        """)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.clear_button)
        
        command_layout.addLayout(button_layout)
        
        layout.addWidget(command_frame)
        
        # Status section
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 15, 15, 15)
        
        status_label = QLabel("Status")
        status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        status_layout.addWidget(status_label)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_frame)
    
    def on_command_text_changed(self):
        """Handle command text changes."""
        text = self.command_input.text().strip()
        if text:
            self.update_suggestions(text)
        else:
            self.suggestions_list.clear()
            self.query_preview.clear()
    
    def update_suggestions(self, text: str):
        """Update command suggestions based on input."""
        try:
            suggestions = self.backend.get_search_service().get_search_suggestions(text)
            self.suggestions_list.clear()
            
            for suggestion in suggestions:
                item = QListWidgetItem(suggestion)
                item.setToolTip(f"Click to use: {suggestion}")
                self.suggestions_list.addItem(item)
                
        except Exception as e:
            self.suggestions_list.clear()
            self.suggestions_list.addItem(QListWidgetItem(f"Error: {str(e)}"))
    
    def on_suggestion_clicked(self, item):
        """Handle suggestion item click."""
        suggestion_text = item.text()
        if suggestion_text.startswith("Error:"):
            return
            
        self.command_input.setText(suggestion_text)
        self.update_suggestions(suggestion_text)
    
    def execute_command(self):
        """Execute the current command."""
        command = self.command_input.text().strip()
        if not command:
            return
        
        try:
            # Parse the command
            structured_query = self.parser.parse(command)
            
            # Show query preview
            preview_text = self.format_query_preview(structured_query)
            self.query_preview.setText(preview_text)
            
            # Execute based on command type
            result = self.execute_parsed_command(structured_query)
            
            if result:
                self.update_status(f"Command executed successfully")
                self.current_command = None
                self.cancel_button.setEnabled(False)
            else:
                self.update_status(f"Command failed to execute")
                
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            QMessageBox.critical(
                self,
                "Command Error",
                f"Failed to execute command: {str(e)}"
            )
    
    def format_query_preview(self, query):
        """Format structured query for preview display."""
        preview_lines = []
        preview_lines.append("=== Parsed Command ===")
        preview_lines.append(f"Subject: {query.subject}")
        preview_lines.append(f"Exact Phrase: {query.exact_phrase}")
        
        if query.required_phrases:
            preview_lines.append(f"Required: {', '.join(query.required_phrases)}")
        
        if query.excluded_phrases:
            preview_lines.append(f"Excluded: {', '.join(query.excluded_phrases)}")
        
        if query.domains:
            preview_lines.append(f"Domains: {', '.join(query.domains)}")
        
        if query.content_types:
            preview_lines.append(f"Types: {', '.join(query.content_types)}")
        
        if query.profile:
            preview_lines.append(f"Profile: {query.profile.value}")
        
        preview_lines.append(f"Max Results: {query.max_results}")
        preview_lines.append(f"Max Depth: {query.max_depth}")
        preview_lines.append(f"Language: {query.language or 'Any'}")
        preview_lines.append(f"Primary Sources: {query.primary_sources}")
        
        return "\n".join(preview_lines)
    
    def execute_parsed_command(self, query):
        """Execute a parsed structured query."""
        # Get research service
        research_service = self.backend.get_research_service()
        
        # Create research session
        session = research_service.create_research_session(query)
        
        # Emit signal for UI updates
        self.update_status(f"Research session created: {session.get('id')}")
        
        return True
    
    def cancel_command(self):
        """Cancel the current command."""
        self.current_command = None
        self.cancel_button.setEnabled(False)
        self.update_status("Command cancelled")
    
    def clear_command(self):
        """Clear the current command."""
        self.command_input.clear()
        self.query_preview.clear()
        self.suggestions_list.clear()
        self.update_status("Command cleared")
    
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.setText(message)
        print(f"Command Interface Status: {message}")
    
    def check_command_status(self):
        """Check if command execution is complete."""
        if self.current_command:
            # Would check command completion status here
            pass
class CommandInterfaceDialog(QWidget):
    """Dialog for the command interface (standalone version)."""
    
    def __init__(self, service_registry: ServiceRegistry, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = BackendServiceAdapter(service_registry)
        
        self.setWindowTitle("Kilo Command Interface")
        self.setFixedSize(800, 600)
        
        self.command_interface = CommandInterface(service_registry)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.command_interface)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)