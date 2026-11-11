"""
Entities View
Browse and analyze extracted entities.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, 
    QPushButton, QTextEdit, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import sys
import os

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from extraction import EntityExtractor
except Exception as e:
    print(f"[DEBUG] entities_view: Import failed: {e}", file=sys.stderr)
    EntityExtractor = None

class EntitiesView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.entity_extractor = EntityExtractor() if EntityExtractor else None
        self.init_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_entities)
        self.refresh_timer.start(10000)
        
        self.refresh_entities()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and filters
        header_layout = QHBoxLayout()
        title = QLabel("Entities")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter entities...")
        self.filter_input.textChanged.connect(self.apply_filter)
        self.filter_input.setMaximumWidth(250)
        header_layout.addWidget(self.filter_input)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "PERSON", "ORG", "LOC", "DATE", "MONEY", "TECH", "PRODUCT", "URL", "EMAIL", "PHONE", "CODE", "VERSION", "FILEPATH", "HASH"])
        self.type_filter.currentTextChanged.connect(self.apply_filter)
        self.type_filter.setMaximumWidth(150)
        header_layout.addWidget(self.type_filter)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_entities)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Entity table
        self.entity_table = QTableWidget()
        self.entity_table.setColumnCount(5)
        self.entity_table.setHorizontalHeaderLabels([
            "Entity", "Type", "Count", "Avg Confidence", "Sample Context"
        ])
        self.entity_table.horizontalHeader().setStretchLastSection(True)
        self.entity_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.entity_table.setAlternatingRowColors(True)
        self.entity_table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.entity_table)
        
        # Detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        detail_header = QLabel("Entity Details")
        detail_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(detail_header)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Monospace", 10))
        detail_layout.addWidget(self.detail_text)
        
        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        # Stats
        self.stats_label = QLabel("Loading...")
        layout.addWidget(self.stats_label)
        
        self._all_entities = []
    
    def refresh_entities(self):
        """Extract and load entities from database."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db or not self.entity_extractor:
            self.stats_label.setText("No database or extractor available")
            return
        
        try:
            c = db.conn.cursor()
            c.execute("SELECT url, title, text FROM pages WHERE http_status = 200 AND text IS NOT NULL AND text != ''")
            pages = c.fetchall()
            
            # Extract entities from all pages
            entity_counts = {}
            entity_contexts = {}
            entity_confidences = {}
            
            for url, title, text in pages:
                if not text:
                    continue
                # Combine title and text
                full_text = f"{title or ''}\n{text}"
                mentions = self.entity_extractor.process_text(full_text, "general", url)
                
                for mention in mentions:
                    key = (mention.text.lower(), mention.entity_type)
                    if key not in entity_counts:
                        entity_counts[key] = 0
                        entity_contexts[key] = []
                        entity_confidences[key] = []
                    
                    entity_counts[key] += 1
                    entity_confidences[key].append(mention.confidence)
                    
                    # Store context (first 200 chars around mention)
                    section = mention.section.text if mention.section else ""
                    if mention.position:
                        start_pos, end_pos = mention.position
                        context = full_text[max(0, start_pos-100):end_pos+100]
                    else:
                        context = section[:200] if section else full_text[:200]
                    entity_contexts[key].append(context)
            
            # Convert to list
            self._all_entities = []
            for (text, etype), count in sorted(entity_counts.items(), key=lambda x: -x[1]):
                avg_conf = sum(entity_confidences[key]) / len(entity_confidences[key])
                sample_ctx = entity_contexts[key][0] if entity_contexts[key] else ""
                self._all_entities.append({
                    "text": text,
                    "type": etype,
                    "count": count,
                    "avg_confidence": avg_conf,
                    "contexts": entity_contexts[key],
                    "sample_context": sample_ctx
                })
            
            self.apply_filter()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.stats_label.setText(f"Error: {e}")
    
    def apply_filter(self):
        """Apply filters to entity table."""
        filter_text = self.filter_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        filtered = []
        for ent in self._all_entities:
            if filter_text and filter_text not in ent["text"].lower():
                continue
            if type_filter != "All Types" and ent["type"] != type_filter:
                continue
            filtered.append(ent)
        
        self.entity_table.setRowCount(len(filtered))
        
        for row, ent in enumerate(filtered):
            self.entity_table.setItem(row, 0, QTableWidgetItem(ent["text"]))
            self.entity_table.setItem(row, 1, QTableWidgetItem(ent["type"]))
            self.entity_table.setItem(row, 2, QTableWidgetItem(str(ent["count"])))
            self.entity_table.setItem(row, 3, QTableWidgetItem(f"{ent['avg_confidence']:.2f}"))
            self.entity_table.setItem(row, 4, QTableWidgetItem(ent["sample_context"][:100] + "..."))
            
            # Store full entity data
            self.entity_table.item(row, 0).setData(Qt.UserRole, ent)
        
        self.stats_label.setText(f"Showing {len(filtered)} of {len(self._all_entities)} entities")
    
    def on_selection_changed(self):
        selected = self.entity_table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self.entity_table.item(row, 0)
            if item:
                ent = item.data(Qt.UserRole)
                if ent:
                    detail = f"Entity: {ent['text']}\n"
                    detail += f"Type: {ent['type']}\n"
                    detail += f"Total Mentions: {ent['count']}\n"
                    detail += f"Average Confidence: {ent['avg_confidence']:.2f}\n\n"
                    detail += "Contexts:\n"
                    detail += "=" * 60 + "\n"
                    for i, ctx in enumerate(ent['contexts'][:10]):
                        detail += f"\n--- Mention {i+1} ---\n{ctx}\n"
                    if len(ent['contexts']) > 10:
                        detail += f"\n... and {len(ent['contexts']) - 10} more mentions"
                    
                    self.detail_text.setPlainText(detail)