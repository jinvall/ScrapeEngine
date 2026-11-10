"""
Research Dialog Widget
Dialog for creating and configuring research sessions.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QFormLayout, QTextEdit, QPushButton, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter
from extraction import CollectionProfile

class ResearchDialog(QDialog):
    """Dialog for creating and configuring research sessions."""
    
    def __init__(self, service_registry=None, parent=None):
        # If first arg is a parent (QWidget), handle compatibility
        if service_registry is not None and hasattr(service_registry, 'parent') and not isinstance(service_registry, ServiceRegistry):
            parent = service_registry
            service_registry = None
        if parent is None and hasattr(service_registry, 'setWindowTitle'):  # might be passed differently
            pass
        # Try to get from parent
        if service_registry is None and parent is not None:
            try:
                service_registry = getattr(parent, 'service_registry', None)
            except:
                pass
        super().__init__(parent)
        self.service_registry = service_registry
        try:
            self.backend = BackendServiceAdapter(service_registry) if service_registry is not None else None
        except Exception as e:
            import traceback
            print(f"[DEBUG] ResearchDialog: Failed to create backend: {e}", file=__import__('sys').stderr)
            traceback.print_exc()
            self.backend = None
        
        self.setWindowTitle("New Research Session")
        self.setFixedSize(600, 500)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("New Research Session")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # Subject
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter research subject or topic...")
        self.subject_input.textChanged.connect(self.update_preview)
        form_layout.addRow("Subject/Topic:", self.subject_input)
        
        # Profile
        self.profile_combo = QComboBox()
        for profile in CollectionProfile:
            self.profile_combo.addItem(f"{profile.value.title().replace('_', ' ')}")
        self.profile_combo.currentIndexChanged.connect(self.update_preview)
        form_layout.addRow("Collection Profile:", self.profile_combo)
        
        # Provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Auto", "Google", "DuckDuckGo", "Bing", "Custom"])
        self.provider_combo.currentIndexChanged.connect(self.update_preview)
        form_layout.addRow("Search Provider:", self.provider_combo)
        
        # Domain
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com (leave empty for all domains)")
        self.domain_input.textChanged.connect(self.update_preview)
        form_layout.addRow("Domain Restriction:", self.domain_input)
        
        # Depth
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["1", "2", "3", "4", "5", "Deep (Unlimited)"])
        self.depth_combo.currentIndexChanged.connect(self.update_preview)
        form_layout.addRow("Crawl Depth:", self.depth_combo)
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Any Language", "English", "French", "German", "Spanish", "Chinese", "Japanese"])
        self.language_combo.currentIndexChanged.connect(self.update_preview)
        form_layout.addRow("Language:", self.language_combo)
        
        # Source preference
        self.source_preference = QComboBox()
        self.source_preference.addItems(["Normal", "Primary Sources Only", "Scholarly Sources Only"])
        self.source_preference.currentIndexChanged.connect(self.update_preview)
        form_layout.addRow("Source Preference:", self.source_preference)
        
        layout.addLayout(form_layout)
        
        # Preview section
        preview_label = QLabel("Generated Command:")
        preview_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(preview_label)
        
        self.command_preview = QTextEdit()
        self.command_preview.setPlaceholderText("Command will appear here...")
        self.command_preview.setMaximumHeight(80)
        self.command_preview.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.command_preview.setReadOnly(True)
        layout.addWidget(self.command_preview)
        
        # Button box
        button_box = QDialogButtonBox()
        
        self.ok_button = QPushButton("Start Research")
        self.ok_button.clicked.connect(self.accept)
        button_box.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_box.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        
        layout.addWidget(button_box)
        
        # Update preview with initial values
        self.update_preview()
    
    def update_preview(self):
        """Update command preview based on current inputs."""
        subject = self.subject_input.text().strip()
        if not subject:
            self.command_preview.clear()
            return
        
        # Build command
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
        
        if self.depth_combo.currentIndex() in depth_map:
            command_parts.append(depth_map[self.depth_combo.currentIndex()])
        
        if self.language_combo.currentIndex() > 0:
            lang = self.language_combo.currentText().lower()
            if lang != "any language":
                command_parts.append(f"--language {lang}")
        
        if self.source_preference.currentIndex() > 0:
            source_type = self.source_preference.currentText().lower().replace(" ", "-")
            command_parts.append(f"--primary-sources" if "primary" in source_type else "")
        
        command = " ".join(command_parts)
        self.command_preview.setText(command)
    
    def get_research_command(self):
        """Get the generated research command."""
        return self.command_preview.toPlainText()

