"""
Crawl Queue View
Shows active and completed crawl jobs with progress monitoring.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

class CrawlQueueView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.init_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_jobs)
        self.refresh_timer.start(3000)  # Refresh every 3 seconds
        
        # Initial load
        self.refresh_jobs()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and toolbar
        header_layout = QHBoxLayout()
        title = QLabel("Crawl Queue")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # New Crawl button
        self.new_crawl_btn = QPushButton("New Crawl")
        self.new_crawl_btn.clicked.connect(self.show_new_crawl_dialog)
        header_layout.addWidget(self.new_crawl_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_jobs)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Job table
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(8)
        self.job_table.setHorizontalHeaderLabels([
            "ID", "URL", "Status", "Pages", "Depth", "Started", "Completed", "Actions"
        ])
        self.job_table.horizontalHeader().setStretchLastSection(True)
        self.job_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.job_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.job_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.job_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.job_table)
        
        # Status label
        self.status_label = QLabel("Loading...")
        layout.addWidget(self.status_label)
    
    def refresh_jobs(self):
        """Load crawl jobs from database."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db:
            self.status_label.setText("No database connection")
            return
        
        try:
            c = db.conn.cursor()
            c.execute("""
                SELECT id, url, status, pages_crawled, max_pages, created_at, completed_at
                FROM crawl_jobs
                ORDER BY created_at DESC
            """)
            jobs = c.fetchall()
            
            self.job_table.setRowCount(len(jobs))
            
            for row, job in enumerate(jobs):
                job_id, url, status, pages_crawled, max_pages, created_at, completed_at = job
                
                # ID
                self.job_table.setItem(row, 0, QTableWidgetItem(job_id))
                
                # URL (truncated)
                url_display = url[:80] + "..." if len(url) > 80 else url
                self.job_table.setItem(row, 1, QTableWidgetItem(url_display))
                
                # Status with color
                status_item = QTableWidgetItem(status)
                if status == "running":
                    status_item.setBackground(Qt.yellow)
                elif status == "completed":
                    status_item.setBackground(Qt.green)
                elif status == "failed":
                    status_item.setBackground(Qt.red)
                elif status == "paused":
                    status_item.setBackground(Qt.cyan)
                self.job_table.setItem(row, 2, status_item)
                
                # Pages
                pages_text = f"{pages_crawled}/{max_pages}"
                self.job_table.setItem(row, 3, QTableWidgetItem(pages_text))
                
                # Depth
                self.job_table.setItem(row, 4, QTableWidgetItem(str(max_pages) if max_pages else "N/A"))
                
                # Started
                self.job_table.setItem(row, 5, QTableWidgetItem(created_at or "N/A"))
                
                # Completed
                self.job_table.setItem(row, 6, QTableWidgetItem(completed_at or "N/A"))
                
                # Actions button
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                
                if status in ("running", "paused"):
                    pause_btn = QPushButton("Pause" if status == "running" else "Resume")
                    pause_btn.setMaximumWidth(80)
                    pause_btn.clicked.connect(lambda checked, jid=job_id, s=status: self.toggle_pause(jid, s))
                    actions_layout.addWidget(pause_btn)
                
                if status in ("completed", "failed"):
                    retry_btn = QPushButton("Retry")
                    retry_btn.setMaximumWidth(80)
                    retry_btn.clicked.connect(lambda checked, jid=job_id: self.retry_job(jid))
                    actions_layout.addWidget(retry_btn)
                
                view_btn = QPushButton("View")
                view_btn.setMaximumWidth(60)
                view_btn.clicked.connect(lambda checked, jid=job_id: self.view_job_details(jid))
                actions_layout.addWidget(view_btn)
                
                self.job_table.setCellWidget(row, 7, actions_widget)
            
            # Update status
            running = sum(1 for j in jobs if j[2] == "running")
            completed = sum(1 for j in jobs if j[2] == "completed")
            failed = sum(1 for j in jobs if j[2] == "failed")
            self.status_label.setText(f"Total: {len(jobs)} | Running: {running} | Completed: {completed} | Failed: {failed}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error loading jobs: {e}")
    
    def show_new_crawl_dialog(self):
        """Show new crawl dialog."""
        try:
            from gui.widgets.crawl_dialog import CrawlDialog
            dialog = CrawlDialog(self.service_registry, self)
            if dialog.exec():
                # Dialog accepted - crawl started in background
                # Refresh will pick it up via timer
                pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open crawl dialog: {e}")
    
    def toggle_pause(self, job_id, current_status):
        """Pause or resume a crawl job."""
        # Find the running worker for this job
        workers = self.service_registry.get("crawl_workers", {})
        worker = workers.get(job_id)
        
        if not worker:
            QMessageBox.warning(self, "Not Running", f"No active crawl found for job {job_id}")
            return
        
        if current_status == "running":
            worker.pause()
            # Update DB status
            db = self.service_registry.get("database_manager")
            if db:
                db._update_crawl_job(job_id, "paused")
        elif current_status == "paused":
            worker.resume()
            # Update DB status
            db = self.service_registry.get("database_manager")
            if db:
                db._update_crawl_job(job_id, "running")
        
        self.refresh_jobs()
    
    def retry_job(self, job_id):
        """Retry a failed/completed job."""
        # Get job details and start new crawl
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if db:
            c = db.conn.cursor()
            c.execute("SELECT url, max_pages FROM crawl_jobs WHERE id = ?", (job_id,))
            row = c.fetchone()
            if row:
                url, max_pages = row
                from gui.widgets.crawl_dialog import CrawlDialog
                dialog = CrawlDialog(self.service_registry, self)
                dialog.url_input.setText(url)
                if max_pages:
                    dialog.max_pages_spin.setValue(max_pages)
                dialog.exec()
    
    def view_job_details(self, job_id):
        """View detailed job information."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if db:
            c = db.conn.cursor()
            c.execute("SELECT * FROM crawl_jobs WHERE id = ?", (job_id,))
            row = c.fetchone()
            if row:
                cols = [desc[0] for desc in c.description]
                details = "\n".join(f"{col}: {val}" for col, val in zip(cols, row))
                QMessageBox.information(self, f"Job Details: {job_id}", details)
    
    def show_context_menu(self, position):
        """Show context menu for job row."""
        menu = QMenu(self)
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_jobs)
        menu.addAction(refresh_action)
        menu.exec(self.job_table.viewport().mapToGlobal(position))
