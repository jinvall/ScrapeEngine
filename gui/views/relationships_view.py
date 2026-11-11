"""
Relationships View
Visualize entity relationships and co-occurrences.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, 
    QPushButton, QTextEdit, QSplitter, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import sys
import os

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from extraction import EntityExtractor
except Exception as e:
    print(f"[DEBUG] relationships_view: Import failed: {e}", file=sys.stderr)
    EntityExtractor = None

class RelationshipsView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.entity_extractor = EntityExtractor() if EntityExtractor else None
        self.init_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_relationships)
        self.refresh_timer.start(15000)
        
        self.refresh_relationships()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and filters
        header_layout = QHBoxLayout()
        title = QLabel("Entity Relationships")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.min_cooccur = QSpinBox()
        self.min_cooccur.setRange(1, 50)
        self.min_cooccur.setValue(2)
        self.min_cooccur.setPrefix("Min co-occurrences: ")
        self.min_cooccur.valueChanged.connect(self.refresh_relationships)
        header_layout.addWidget(self.min_cooccur)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_relationships)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export GraphML")
        export_btn.clicked.connect(self.export_graphml)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Relationships table
        self.rel_table = QTableWidget()
        self.rel_table.setColumnCount(6)
        self.rel_table.setHorizontalHeaderLabels([
            "Entity A", "Type A", "Entity B", "Type B", "Co-occurrences", "Relationship"
        ])
        self.rel_table.horizontalHeader().setStretchLastSection(True)
        self.rel_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rel_table.setAlternatingRowColors(True)
        splitter.addWidget(self.rel_table)
        
        # Detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        detail_header = QLabel("Relationship Details")
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
        
        self._all_relationships = []
    
    def refresh_relationships(self):
        """Extract and compute entity relationships."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db or not self.entity_extractor:
            self.stats_label.setText("No database or extractor available")
            return
        
        try:
            c = db.conn.cursor()
            c.execute("SELECT url, title, text FROM pages WHERE http_status = 200 AND text IS NOT NULL AND text != ''")
            pages = c.fetchall()
            
            # Extract entities per page
            page_entities = []
            all_entities = set()
            
            for url, title, text in pages:
                if not text:
                    continue
                full_text = f"{title or ''}\n{text}"
                mentions = self.entity_extractor.process_text(full_text, "general", url)
                
                page_ents = {}
                for mention in mentions:
                    key = (mention.text.lower(), mention.entity_type)
                    all_entities.add(key)
                    if key not in page_ents:
                        page_ents[key] = mention
                page_entities.append(page_ents)
            
            # Compute co-occurrences
            from collections import defaultdict
            cooccur = defaultdict(int)
            
            for page_ents in page_entities:
                ents = list(page_ents.keys())
                for i, e1 in enumerate(ents):
                    for e2 in ents[i+1:]:
                        # Sort to ensure consistent ordering
                        pair = tuple(sorted([e1, e2]))
                        cooccur[pair] += 1
            
            # Filter by minimum co-occurrence
            min_co = self.min_cooccur.value()
            self._all_relationships = []
            
            for (e1, e2), count in sorted(cooccur.items(), key=lambda x: -x[1]):
                if count < min_co:
                    continue
                
                text1, type1 = e1
                text2, type2 = e2
                
                # Determine relationship type
                rel_type = "co-occurs"
                if type1 == type2:
                    rel_type = f"same-type ({type1})"
                
                self._all_relationships.append({
                    "entity_a": text1, "type_a": type1,
                    "entity_b": text2, "type_b": type2,
                    "count": count, "relationship": rel_type
                })
            
            self.apply_filter()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.stats_label.setText(f"Error: {e}")
    
    def apply_filter(self):
        """Display relationships in table."""
        self.rel_table.setRowCount(len(self._all_relationships))
        
        for row, rel in enumerate(self._all_relationships):
            self.rel_table.setItem(row, 0, QTableWidgetItem(rel["entity_a"]))
            self.rel_table.setItem(row, 1, QTableWidgetItem(rel["type_a"]))
            self.rel_table.setItem(row, 2, QTableWidgetItem(rel["entity_b"]))
            self.rel_table.setItem(row, 3, QTableWidgetItem(rel["type_b"]))
            self.rel_table.setItem(row, 3, QTableWidgetItem(str(rel["count"])))
            self.rel_table.setItem(row, 4, QTableWidgetItem(rel["relationship"]))
            
            self.rel_table.item(row, 0).setData(Qt.UserRole, rel)
        
        self.stats_label.setText(f"Found {len(self._all_relationships)} relationships (min {self.min_cooccur.value()} co-occurrences)")
    
    def export_graphml(self):
        """Export relationships as GraphML for Gephi/Cytoscape."""
        from PySide6.QtWidgets import QFileDialog
        fname, _ = QFileDialog.getSaveFileName(self, "Export GraphML", "relationships.graphml", "GraphML Files (*.graphml)")
        if not fname:
            return
        
        try:
            lines = ['<?xml version="1.0" encoding="UTF-8"?>']
            lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
            lines.append('  <key id="type" for="node" attr.name="type" attr.type="string"/>')
            lines.append('  <key id="count" for="edge" attr.name="count" attr.type="int"/>')
            lines.append('  <key id="relationship" for="edge" attr.name="relationship" attr.type="string"/>')
            lines.append('  <graph id="G" edgedefault="undirected">')
            
            # Collect unique nodes
            nodes = set()
            for rel in self._all_relationships:
                nodes.add((rel["entity_a"], rel["type_a"]))
                nodes.add((rel["entity_b"], rel["type_b"]))
            
            for text, etype in nodes:
                safe_id = text.replace(" ", "_").replace(".", "_").replace(",", "").replace("(", "").replace(")", "")
                lines.append(f'    <node id="{safe_id}">')
                lines.append(f'      <data key="type">{etype}</data>')
                lines.append(f'    </node>')
            
            for rel in self._all_relationships:
                safe_a = rel["entity_a"].replace(" ", "_").replace(".", "_").replace(",", "").replace("(", "").replace(")", "")
                safe_b = rel["entity_b"].replace(" ", "_").replace(".", "_").replace(",", "").replace("(", "").replace(")", "")
                lines.append(f'    <edge source="{safe_a}" target="{safe_b}">')
                lines.append(f'      <data key="count">{rel["count"]}</data>')
                lines.append(f'      <data key="relationship">{rel["relationship"]}</data>')
                lines.append(f'    </edge>')
            
            lines.append('  </graph>')
            lines.append('</graphml>')
            
            with open(fname, 'w') as f:
                f.write('\n'.join(lines))
            
            QMessageBox.information(self, "Exported", f"GraphML exported to {fname}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Export failed: {e}")