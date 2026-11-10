"""
Crawl Dialog Widget
Dialog for configuring crawl operations.
"""

import sys
import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QFormLayout, QPushButton, QDialogButtonBox, QMessageBox, 
    QSpinBox, QTextEdit
)
from PySide6.QtCore import Qt

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from scrape_engine import ScraperEngine, ScraperConfig, DatabaseManager
    from crawl_controller import CrawlController
    from crawl_nlp import CrawlNLPProcessor
except Exception as e:
    print(f"[DEBUG] crawl_dialog: Import failed: {e}", file=sys.stderr)

class CrawlDialog(QDialog):
    """Dialog for creating and configuring crawl sessions."""
    
    def __init__(self, service_registry=None, parent=None):
        # Handle compatibility
        if service_registry is not None and parent is None and hasattr(service_registry, 'show'):
            # First arg might be parent
            parent = service_registry
            service_registry = None
        
        if service_registry is None and parent is not None:
            try:
                service_registry = getattr(parent, 'service_registry', None)
            except Exception:
                pass
        
        super().__init__(parent)
        self.service_registry = service_registry
        self.config_file = os.path.expanduser('~/.kilo/crawl_config.json')
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        except Exception:
            pass
        
        self.setWindowTitle("New Crawl Session")
        self.setMinimumSize(600, 500)
        self.resize(600, 550)
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("New Crawl Session")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form_layout.addRow("Start URL:", self.url_input)
        
        # Natural Language Instructions
        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText(
            "Describe what you want to find, what information should be extracted, "
            "which keywords or phrases matter, and what types of pages should be "
            "prioritized or excluded. For example: Find technical information about "
            "ESP32 audio streaming. Prioritize UDP and TCP transmission, microphone "
            "sensitivity, low-latency processing, noise reduction, and audio compression. "
            "Extract technical specifications, code examples, configuration values, "
            "and useful external references."
        )
        self.instructions_input.setMinimumHeight(150)
        form_layout.addRow("Natural Language Instructions:", self.instructions_input)
        
        # Depth
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(2)
        form_layout.addRow("Crawl Depth:", self.depth_spin)
        
        # Max pages
        self.max_pages_spin = QSpinBox()
        self.max_pages_spin.setRange(1, 10000)
        self.max_pages_spin.setValue(100)
        form_layout.addRow("Max Pages:", self.max_pages_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.start_crawl)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def start_crawl(self):
        """Start the crawl with configuration."""
        config = self.get_config()
        url = config['start_url']
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a start URL")
            return
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
            return
        if config['max_depth'] < 0 or config['max_pages'] < 1:
            QMessageBox.warning(self, "Invalid Parameters", "Please check depth and page limits")
            return
        
        try:
            # Save config
            self.save_config()
            # Process instructions
            nlp = CrawlNLPProcessor() if 'CrawlNLPProcessor' in globals() else None
            if nlp and config['instructions']:
                objectives = nlp.process_instructions(config['instructions'])
                print(f"[DEBUG] crawl_dialog: Starting crawl with {len(objectives.required_keywords)} keywords", file=__import__('sys').stderr)
            
            # Create scraper config
            scraper_config = ScraperConfig(
                start_url=url,
                max_depth=config['max_depth'],
                max_pages=config['max_pages'],
                instructions=config['instructions']
            )
            
            QMessageBox.information(self, "Crawl Started", 
                                   f"Crawl started for {url}\nInstructions: {config['instructions'][:50]}..." if config['instructions'] else f"Crawl started for {url}")
            self.accept()
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Error starting crawl: {e}", file=__import__('sys').stderr)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start crawl: {e}")
    
    def get_config(self):
        """Get the crawl configuration."""
        return {
            "start_url": self.url_input.text().strip(),
            "instructions": self.instructions_input.toPlainText().strip(),
            "max_depth": self.depth_spin.value(),
            "max_pages": self.max_pages_spin.value()
        }

    def load_config(self):
        """Load saved crawl configuration."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                if 'start_url' in config:
                    self.url_input.setText(config['start_url'])
                if 'instructions' in config:
                    self.instructions_input.setPlainText(config['instructions'])
                if 'max_depth' in config:
                    self.depth_spin.setValue(int(config['max_depth']))
                if 'max_pages' in config:
                    self.max_pages_spin.setValue(int(config['max_pages']))
                print("[DEBUG] crawl_dialog: Loaded saved config", file=__import__('sys').stderr)
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Failed to load config: {e}", file=__import__('sys').stderr)
    
    def save_config(self):
        """Save crawl configuration."""
        try:
            config = self.get_config()
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print("[DEBUG] crawl_dialog: Saved config", file=__import__('sys').stderr)
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Failed to save config: {e}", file=__import__('sys').stderr)

