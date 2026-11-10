"""
Reports View (placeholder)
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ReportsView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        layout = QVBoxLayout(self)
        label = QLabel("Reports")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
