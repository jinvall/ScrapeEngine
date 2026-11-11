"""
Documents View
Browse and manage all crawled documents.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLineEdit, QPushButton, 
    QComboBox, QTextEdit, QSplitter, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont

class DocumentsView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.init_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_documents)
        self.refresh_timer.start(5000)
        
        self.refresh_documents()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and toolbar
        header_layout = QHBoxLayout()
        title = QLabel("Documents")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Filter controls
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by URL, title...")
        self.filter_input.textChanged.connect(self.apply_filter)
        self.filter_input.setMaximumWidth(300)
        header_layout.addWidget(self.filter_input)
        
        self.domain_filter = QComboBox()
        self.domain_filter.addItem("All Domains")
        self.domain_filter.currentTextChanged.connect(self.apply_filter)
        self.domain_filter.setMaximumWidth(200)
        header_layout.addWidget(self.domain_filter)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "200 OK", "Errors", "Redirects"])
        self.status_filter.currentTextChanged.connect(self.apply_filter)
        self.status_filter.setMaximumWidth(150)
        header_layout.addWidget(self.status_filter)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_documents)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Splitter for table and detail view
        splitter = QSplitter(Qt.Vertical)
        
        # Document table
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(7)
        self.doc_table.setHorizontalHeaderLabels([
            "Title", "URL", "Status", "Depth", "Size", "Crawled", "Actions"
        ])
        self.doc_table.horizontalHeader().setStretchLastSection(True)
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.doc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.doc_table.setAlternatingRowColors(True)
        self.doc_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.doc_table.customContextMenuRequested.connect(self.show_context_menu)
        self.doc_table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.doc_table)
        
        # Detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(5, 5, 5, 5)
        
        detail_header = QLabel("Document Content")
        detail_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(detail_header)
        
        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        self.content_view.setFont(QFont("Monospace", 10))
        detail_layout.addWidget(self.content_view)
        
        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        # Status
        self.status_label = QLabel("Loading...")
        layout.addWidget(self.status_label)
        
        self._all_documents = []
    
    def refresh_documents(self):
        """Load documents from database."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db:
            self.status_label.setText("No database connection")
            return
        
        try:
            c = db.conn.cursor()
            c.execute("""
                SELECT url, title, description, text, http_status, crawl_depth, crawl_timestamp
                FROM pages
                ORDER BY crawl_timestamp DESC
            """)
            docs = c.fetchall()
            
            self._all_documents = docs
            
            # Update domain filter
            domains = set()
            for doc in docs:
                from urllib.parse import urlparse
                try:
                    domains.add(urlparse(doc[0]).netloc)
                except:
                    pass
            
            current = self.domain_filter.currentText()
            self.domain_filter.blockSignals(True)
            self.domain_filter.clear()
            self.domain_filter.addItem("All Domains")
            for domain in sorted(domains):
                self.domain_filter.addItem(domain)
            if current in [self.domain_filter.itemText(i) for i in range(self.domain_filter.count())]:
                self.domain_filter.setCurrentText(current)
            self.domain_filter.blockSignals(False)
            
            self.apply_filter()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error loading documents: {e}")
    
    def apply_filter(self):
        """Apply filters to document table."""
        filter_text = self.filter_input.text().lower()
        domain_filter = self.domain_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        filtered = []
        for doc in self._all_documents:
            url, title, desc, text, status, depth, timestamp = doc
            
            # Text filter
            if filter_text:
                if filter_text not in (url or "").lower() and filter_text not in (title or "").lower():
                    continue
            
            # Domain filter
            if domain_filter != "All Domains":
                from urllib.parse import urlparse
                try:
                    if urlparse(url).netloc != domain_filter:
                        continue
                except:
                    continue
            
            # Status filter
            if status_filter == "200 OK" and status != 200:
                continue
            elif status_filter == "Errors" and status == 200:
                continue
            elif status_filter == "Redirects" and status not in (301, 302, 303, 307, 308):
                continue
            
            filtered.append(doc)
        
        self.doc_table.setRowCount(len(filtered))
        
        for row, doc in enumerate(filtered):
            url, title, desc, text, status, depth, timestamp = doc
            
            # Title
            title_item = QTableWidgetItem(title or "(no title)")
            title_item.setData(Qt.UserRole, doc)  # Store full doc for detail view
            self.doc_table.setItem(row, 0, title_item)
            
            # URL (truncated)
            url_display = url[:80] + "..." if len(url) > 80 else url
            self.doc_table.setItem(row, 1, QTableWidgetItem(url_display))
            
            # Status
            status_item = QTableWidgetItem(str(status) if status else "N/A")
            if status == 200:
                status_item.setBackground(Qt.green)
            elif status and status >= 400:
                status_item.setBackground(Qt.red)
            elif status and status >= 300:
                status_item.setBackground(Qt.yellow)
            self.doc_table.setItem(row, 2, status_item)
            
            # Depth
            self.doc_table.setItem(row, 3, QTableWidgetItem(str(depth) if depth is not None else "N/A"))
            
            # Size
            size = len(text) if text else 0
            if size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} B"
            self.doc_table.setItem(row, 4, QTableWidgetItem(size_str))
            
            # Crawled
            self.doc_table.setItem(row, 5, QTableWidgetItem(timestamp or "N/A"))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("View")
            view_btn.setMaximumWidth(60)
            view_btn.clicked.connect(lambda checked, r=row: self.view_document(r))
            actions_layout.addWidget(view_btn)
            
            open_btn = QPushButton("Open")
            open_btn.setMaximumWidth(60)
            open_btn.clicked.connect(lambda checked, u=url: self.open_in_browser(u))
            actions_layout.addWidget(open_btn)
            
            self.doc_table.setCellWidget(row, 6, actions_widget)
        
        self.status_label.setText(f"Showing {len(filtered)} of {len(self._all_documents)} documents")
    
    def on_selection_changed(self):
        """Update detail view on selection."""
        selected = self.doc_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.view_document(row)
    
    def view_document(self, row):
        """Show document content in detail view."""
        item = self.doc_table.item(row, 0)
        if item:
            doc = item.data(Qt.UserRole)
            if doc:
                url, title, desc, text, status, depth, timestamp = doc
                
                content = f"URL: {url}\n"
                content += f"Title: {title}\n"
                content += f"Status: {status}\n"
                content += f"Depth: {depth}\n"
                content += f"Crawled: {timestamp}\n"
                content += f"Size: {len(text) if text else 0} bytes\n"
                content += f"{'='*80}\n\n"
                
                if desc:
                    content += f"Description: {desc}\n\n"
                
                if text:
                    content += text[:50000]  # Limit for performance
                    if len(text) > 50000:
                        content += f"\n\n... (truncated, {len(text)} total bytes)"
                else:
                    content += "(no content)"
                
                self.content_view.setPlainText(content)
    
    def open_in_browser(self, url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def show_context_menu(self, position):
        """Show context menu."""
        menu = QMenu(self)
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_documents)
        menu.addAction(refresh_action)
        
        export_action = QAction("Export Selected", self)
        export_action.triggered.connect(self.export_selected)
        menu.addAction(export_action)
        
        menu.exec(self.doc_table.viewport().mapToGlobal(position))
    
    def export_selected(self):
        """Export selected documents to JSON."""
        selected = self.doc_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        item = self.doc_table.item(row, 0)
        if item:
            doc = item.data(Qt.UserRole)
            if doc:
                url, title, desc, text, status, depth, timestamp = doc
                import json
                from datetime import datetime
                
                export_data = {
                    "url": url,
                    "title": title,
                    "description": desc,
                    "content": text,
                    "http_status": status,
                    "depth": depth,
                    "crawled_at": timestamp,
                    "exported_at": datetime.now().isoformat()
                }
                
                from PySide6.QtWidgets import QFileDialog
                fname, _ = QFileDialog.getSaveFileName(self, "Export Document", f"{title[:50]}.json", "JSON Files (*.json)")
                if fname:
                    with open(fname, 'w') as f:
                        json.dump(export_data, f, indent=2)
                    QMessageBox.information(self, "Exported", f"Document exported to {fname}")