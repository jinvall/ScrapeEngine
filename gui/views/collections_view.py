"""
Collections View
Manage document collections with profiles.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, 
    QPushButton, QTextEdit, QSplitter, QMessageBox, QInputDialog,
    QListWidget, QListWidgetItem, QAbstractItemView, QFormLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from extraction import CollectionProfile
except Exception as e:
    print(f"[DEBUG] collections_view: Import failed: {e}", file=sys.stderr)
    CollectionProfile = None

class CollectionsView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.collections_file = os.path.expanduser('~/.kilo/collections.json')
        self.init_ui()
        
        # Load collections
        self.load_collections()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and toolbar
        header_layout = QHBoxLayout()
        title = QLabel("Collections")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        new_btn = QPushButton("New Collection")
        new_btn.clicked.connect(self.create_collection)
        header_layout.addWidget(new_btn)
        
        delete_btn = QPushButton("Delete Collection")
        delete_btn.clicked.connect(self.delete_collection)
        header_layout.addWidget(delete_btn)
        
        layout.addLayout(header_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Collections list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("Collections"))
        
        self.collection_list = QListWidget()
        self.collection_list.currentItemChanged.connect(self.on_collection_selected)
        left_layout.addWidget(self.collection_list)
        
        splitter.addWidget(left_widget)
        
        # Right side - collection details and documents
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Collection info
        info_layout = QFormLayout()
        self.coll_name = QLabel("-")
        self.coll_profile = QLabel("-")
        self.coll_created = QLabel("-")
        self.coll_count = QLabel("-")
        info_layout.addRow("Name:", self.coll_name)
        info_layout.addRow("Profile:", self.coll_profile)
        info_layout.addRow("Created:", self.coll_created)
        info_layout.addRow("Documents:", self.coll_count)
        right_layout.addLayout(info_layout)
        
        # Documents in collection
        right_layout.addWidget(QLabel("Documents"))
        
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels([
            "Title", "URL", "Status", "Crawled", "Actions"
        ])
        self.doc_table.horizontalHeader().setStretchLastSection(True)
        self.doc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.doc_table.setAlternatingRowColors(True)
        right_layout.addWidget(self.doc_table)
        
        # Document actions
        doc_actions = QHBoxLayout()
        add_doc_btn = QPushButton("Add Document")
        add_doc_btn.clicked.connect(self.add_document)
        doc_actions.addWidget(add_doc_btn)
        
        remove_doc_btn = QPushButton("Remove Selected")
        remove_doc_btn.clicked.connect(self.remove_document)
        doc_actions.addWidget(remove_doc_btn)
        
        export_btn = QPushButton("Export Collection")
        export_btn.clicked.connect(self.export_collection)
        doc_actions.addWidget(export_btn)
        
        right_layout.addLayout(doc_actions)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        self.collections = {}
    
    def load_collections(self):
        """Load collections from file."""
        try:
            if os.path.exists(self.collections_file):
                with open(self.collections_file, 'r') as f:
                    self.collections = json.load(f)
            else:
                self.collections = {}
        except Exception as e:
            print(f"[DEBUG] collections_view: Failed to load: {e}", file=sys.stderr)
            self.collections = {}
        
        self.refresh_list()
    
    def save_collections(self):
        """Save collections to file."""
        try:
            os.makedirs(os.path.dirname(self.collections_file), exist_ok=True)
            with open(self.collections_file, 'w') as f:
                json.dump(self.collections, f, indent=2)
        except Exception as e:
            print(f"[DEBUG] collections_view: Failed to save: {e}", file=sys.stderr)
    
    def refresh_list(self):
        """Refresh collection list widget."""
        self.collection_list.clear()
        for name, coll in self.collections.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.collection_list.addItem(item)
    
    def on_collection_selected(self, current, previous):
        """Show collection details."""
        if not current:
            self.clear_details()
            return
        
        name = current.data(Qt.UserRole)
        coll = self.collections.get(name, {})
        
        self.coll_name.setText(name)
        self.coll_profile.setText(coll.get("profile", "main_text"))
        self.coll_created.setText(coll.get("created", "Unknown"))
        self.coll_count.setText(str(len(coll.get("documents", []))))
        
        # Populate document table
        docs = coll.get("documents", [])
        self.doc_table.setRowCount(len(docs))
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels(["Title", "URL", "Status", "Crawled", "Actions"])
        
        for row, doc in enumerate(docs):
            self.doc_table.setItem(row, 0, QTableWidgetItem(doc.get("title", "")))
            self.doc_table.setItem(row, 1, QTableWidgetItem(doc.get("url", "")))
            self.doc_table.setItem(row, 2, QTableWidgetItem(str(doc.get("status", ""))))
            self.doc_table.setItem(row, 3, QTableWidgetItem(doc.get("crawled_at", "")))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            remove_btn = QPushButton("Remove")
            remove_btn.setMaximumWidth(80)
            remove_btn.clicked.connect(lambda checked, n=name, u=doc.get("url"): self.remove_document_from_collection(n, u))
            actions_layout.addWidget(remove_btn)
            
            self.doc_table.setCellWidget(row, 4, actions_widget)
    
    def clear_details(self):
        self.coll_name.setText("-")
        self.coll_profile.setText("-")
        self.coll_created.setText("-")
        self.coll_count.setText("-")
        self.doc_table.setRowCount(0)
    
    def create_collection(self):
        """Create a new collection."""
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        if name in self.collections:
            QMessageBox.warning(self, "Exists", "Collection already exists")
            return
        
        # Select profile
        profile, ok = QInputDialog.getItem(self, "Profile", "Collection profile:", 
            ["main_text", "technical_spec", "product_page", "news_article", "documentation", 
             "academic_paper", "forum_thread", "faq_page", "contact_page", "event_page", 
             "job_posting", "review_page", "landing_page"], 0, False)
        if not ok:
            return
        
        self.collections[name] = {
            "profile": profile,
            "created": datetime.now().isoformat(),
            "documents": []
        }
        self.save_collections()
        self.refresh_list()
    
    def delete_collection(self):
        """Delete selected collection."""
        current = self.collection_list.currentItem()
        if not current:
            return
        
        name = current.data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", f"Delete collection '{name}'?") == QMessageBox.Yes:
            del self.collections[name]
            self.save_collections()
            self.refresh_list()
            self.clear_details()
    
    def add_document(self):
        """Add document from database to collection."""
        current = self.collection_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Collection", "Select a collection first")
            return
        
        name = current.data(Qt.UserRole)
        
        # Get documents from database
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db:
            QMessageBox.warning(self, "No Database", "Database not available")
            return
        
        try:
            c = db.conn.cursor()
            c.execute("SELECT url, title, http_status, crawl_timestamp FROM pages ORDER BY crawl_timestamp DESC LIMIT 100")
            pages = c.fetchall()
            
            # Show selection dialog
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Documents")
            dialog.resize(600, 400)
            layout = QVBoxLayout(dialog)
            
            list_widget = QListWidget()
            list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
            for url, title, status, timestamp in pages:
                item = QListWidgetItem(f"{title or 'No title'} - {url[:80]}")
                item.setData(Qt.UserRole, {"url": url, "title": title, "status": status, "crawled_at": timestamp})
                list_widget.addItem(item)
            
            layout.addWidget(list_widget)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            if dialog.exec() == QDialog.Accepted:
                for item in list_widget.selectedItems():
                    doc = item.data(Qt.UserRole)
                    if doc["url"] not in [d["url"] for d in self.collections[name]["documents"]]:
                        self.collections[name]["documents"].append(doc)
                
                self.save_collections()
                self.on_collection_selected(current, None)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add documents: {e}")
    
    def remove_document(self):
        """Remove selected document from collection."""
        current = self.collection_list.currentItem()
        if not current:
            return
        
        name = current.data(Qt.UserRole)
        selected = self.doc_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        url = self.doc_table.item(row, 1).text()
        
        self.collections[name]["documents"] = [d for d in self.collections[name]["documents"] if d["url"] != url]
        self.save_collections()
        self.on_collection_selected(current, None)
    
    def remove_document_from_collection(self, coll_name, url):
        """Remove document from collection (from button)."""
        self.collections[coll_name]["documents"] = [d for d in self.collections[coll_name]["documents"] if d["url"] != url]
        self.save_collections()
        current = self.collection_list.currentItem()
        if current and current.data(Qt.UserRole) == coll_name:
            self.on_collection_selected(current, None)
    
    def export_collection(self):
        """Export collection to JSON."""
        current = self.collection_list.currentItem()
        if not current:
            return
        
        from PySide6.QtWidgets import QFileDialog
        name = current.data(Qt.UserRole)
        coll = self.collections[name]
        
        fname, _ = QFileDialog.getSaveFileName(self, "Export Collection", f"{name}.json", "JSON Files (*.json)")
        if fname:
            export_data = {
                "name": name,
                "profile": coll["profile"],
                "created": coll["created"],
                "exported": datetime.now().isoformat(),
                "documents": coll["documents"]
            }
            with open(fname, 'w') as f:
                json.dump(export_data, f, indent=2)
            QMessageBox.information(self, "Exported", f"Collection exported to {fname}")