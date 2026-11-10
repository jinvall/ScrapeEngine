"""
Settings Dialog Widget
Dialog for application settings.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    """Dialog for application settings."""
    
    def __init__(self, service_registry=None, parent=None):
        if service_registry is not None and parent is None and hasattr(service_registry, 'show'):
            parent = service_registry
            service_registry = None
        
        if service_registry is None and parent is not None:
            try:
                service_registry = getattr(parent, 'service_registry', None)
            except:
                pass
        
        super().__init__(parent)
        self.service_registry = service_registry
        
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 300)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Settings")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Content placeholder
        content_label = QLabel("Settings configuration coming soon...")
        content_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(content_label)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
