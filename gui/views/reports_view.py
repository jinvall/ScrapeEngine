"""
Reports View
Generate and export research and crawl reports.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QTextEdit, QDateEdit, QCheckBox, QMessageBox,
    QFileDialog, QProgressBar, QGroupBox, QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont
import sys
import os

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from scrape_engine import DatabaseManager
except Exception as e:
    print(f"[DEBUG] reports_view: Import failed: {e}", file=sys.stderr)

class ReportWorker(QThread):
    """Worker for generating reports."""
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, report_type, db, params):
        super().__init__()
        self.report_type = report_type
        self.db = db
        self.params = params
    
    def run(self):
        try:
            if self.report_type == "crawl":
                self.generate_crawl_report()
            elif self.report_type == "storage":
                self.generate_storage_report()
            elif self.report_type == "research":
                self.generate_research_report()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def generate_crawl_report(self):
        self.progress.emit("Fetching crawl jobs...")
        c = self.db.conn.cursor()
        
        # Build query based on params
        where_clauses = []
        params = []
        
        if self.params.get("job_id"):
            where_clauses.append("id = ?")
            params.append(self.params["job_id"])
        else:
            if self.params.get("date_from"):
                where_clauses.append("date(created_at) >= ?")
                params.append(self.params["date_from"])
            if self.params.get("date_to"):
                where_clauses.append("date(created_at) <= ?")
                params.append(self.params["date_to"])
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        c.execute(f"SELECT * FROM crawl_jobs {where_sql} ORDER BY created_at DESC", params)
        jobs = c.fetchall()
        
        self.progress.emit("Fetching page data...")
        # Get pages for each job
        report = "# Crawl Report\n\n"
        report += f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n"
        
        for job in jobs:
            job_id, url, status, pages_crawled, max_pages, created_at, completed_at = job
            
            report += f"## Job: {job_id}\n"
            report += f"- **URL:** {url}\n"
            report += f"- **Status:** {status}\n"
            report += f"- **Pages Crawled:** {pages_crawled}/{max_pages}\n"
            report += f"- **Started:** {created_at}\n"
            report += f"- **Completed:** {completed_at or 'N/A'}\n"
            
            # Get pages for this job
            c.execute("SELECT url, http_status, crawl_depth, crawl_timestamp FROM pages WHERE url LIKE ? ORDER BY crawl_timestamp", (url + "%",))
            pages = c.fetchall()
            
            if pages:
                report += f"\n### Pages ({len(pages)})\n"
                report += "| URL | Status | Depth | Crawled |\n"
                report += "|-----|--------|-------|---------|\n"
                for page_url, pstatus, depth, ts in pages:
                    report += f"| {page_url} | {pstatus} | {depth} | {ts} |\n"
            
            report += "\n---\n\n"
        
        self.finished.emit(report)
    
    def generate_storage_report(self):
        self.progress.emit("Generating storage report...")
        
        # Get storage stats from service registry if available
        report = "# Storage Report\n\n"
        report += f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n"
        
        # Database stats
        c = self.db.conn.cursor()
        c.execute("SELECT COUNT(*) FROM pages")
        total_pages = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM pages WHERE http_status = 200")
        ok_pages = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM pages WHERE http_status != 200")
        error_pages = c.fetchone()[0]
        
        c.execute("SELECT SUM(LENGTH(text)) FROM pages WHERE text IS NOT NULL")
        total_content = c.fetchone()[0] or 0
        
        report += "## Database Statistics\n"
        report += f"- **Total Pages:** {total_pages}\n"
        report += f"- **Successful (200):** {ok_pages}\n"
        report += f"- **Errors:** {error_pages}\n"
        report += f"- **Total Content Size:** {total_content / 1024 / 1024:.2f} MB\n\n"
        
        # Storage manager stats if available
        try:
            from storage_manager import StorageManager
            storage = StorageManager('.storage')
            usage = storage.get_usage_report()
            
            report += "## Storage Manager\n"
            report += f"- **Used:** {usage.get('total_bytes', 0) / 1024 / 1024:.2f} MB\n"
            report += f"- **Hard Ceiling:** {usage.get('hard_ceiling_bytes', 0) / 1024 / 1024:.2f} MB\n"
            report += f"- **Available:** {usage.get('available_bytes', 0) / 1024 / 1024:.2f} MB\n"
            report += f"- **Usage:** {usage.get('pct_used', 0):.2f}%\n"
            report += f"- **Compression Ratio:** {usage.get('compression_ratio', 0):.2f}x\n"
            
            breakdown = usage.get('breakdown', {})
            if breakdown:
                report += "\n### Breakdown\n"
                for k, v in breakdown.items():
                    report += f"- **{k}:** {v:.2f} MB\n"
        except Exception:
            pass
        
        self.finished.emit(report)
    
    def generate_research_report(self):
        self.progress.emit("Generating research report...")
        
        c = self.db.conn.cursor()
        
        # Get research sessions
        c.execute("SELECT * FROM research_sessions ORDER BY created_at DESC")
        sessions = c.fetchall()
        
        # Get searches
        c.execute("SELECT * FROM search_queries ORDER BY created_at DESC LIMIT 50")
        searches = c.fetchall()
        
        report = "# Research Report\n\n"
        report += f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n"
        
        report += "## Research Sessions\n"
        for session in sessions:
            session_id, query, status, created_at, completed_at = session
            report += f"- **{session_id}** ({status})\n"
            report += f"  Query: {query}\n"
            report += f"  Started: {created_at}\n"
            if completed_at:
                report += f"  Completed: {completed_at}\n"
            report += "\n"
        
        report += "## Recent Searches\n"
        report += "| Query | Type | Results | Status | Time |\n"
        report += "|-------|------|---------|--------|------|\n"
        for search in searches:
            search_id, query, qtype, count, status, created_at = search
            report += f"| {query} | {qtype} | {count} | {status} | {created_at} |\n"
        
        self.finished.emit(report)


class ReportsView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.worker = None
        self.current_report = ""
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and controls
        header_layout = QHBoxLayout()
        title = QLabel("Reports")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.report_type = QComboBox()
        self.report_type.addItems(["Crawl Report", "Storage Report", "Research Report"])
        self.report_type.setMaximumWidth(200)
        header_layout.addWidget(QLabel("Type:"))
        header_layout.addWidget(self.report_type)
        
        # Options
        self.job_id_input = QLineEdit()
        self.job_id_input.setPlaceholderText("Job ID (optional)")
        self.job_id_input.setMaximumWidth(200)
        header_layout.addWidget(QLabel("Job ID:"))
        header_layout.addWidget(self.job_id_input)
        
        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self.generate_report)
        header_layout.addWidget(generate_btn)
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_report)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Date range
        date_group = QGroupBox("Date Range")
        date_layout = QHBoxLayout(date_group)
        
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.date_to)
        
        layout.addWidget(date_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Report preview
        preview_label = QLabel("Report Preview")
        preview_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(preview_label)
        
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setFont(QFont("Monospace", 10))
        layout.addWidget(self.report_preview)
    
    def generate_report(self):
        """Generate selected report type."""
        db = self.service_registry.get("database_manager") if self.service_registry else None
        if not db:
            QMessageBox.warning(self, "No Database", "Database not available")
            return
        
        report_type = self.report_type.currentText().lower().split()[0]
        
        params = {
            "job_id": self.job_id_input.text().strip() or None,
            "date_from": self.date_from.date().toString("yyyy-MM-dd"),
            "date_to": self.date_to.date().toString("yyyy-MM-dd")
        }
        
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Generating report...")
        
        self.worker = ReportWorker(report_type, db, params)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, message):
        self.progress_label.setText(message)
    
    def on_finished(self, report):
        self.current_report = report
        self.report_preview.setPlainText(report)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
    
    def on_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        QMessageBox.critical(self, "Error", f"Report generation failed: {error_msg}")
    
    def export_report(self):
        """Export current report to file."""
        if not self.current_report:
            QMessageBox.information(self, "No Report", "Generate a report first")
            return
        
        fmt = "Markdown"
        fname, _ = QFileDialog.getSaveFileName(
            self, "Export Report", 
            f"{self.report_type.currentText().lower().replace(' ', '_')}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.md",
            "Markdown Files (*.md);;Text Files (*.txt);;HTML Files (*.html)"
        )
        
        if fname:
            try:
                if fname.endswith('.html'):
                    # Convert markdown to HTML
                    import markdown
                    html = markdown.markdown(self.current_report)
                    with open(fname, 'w') as f:
                        f.write(f"<html><body>{html}</body></html>")
                else:
                    with open(fname, 'w') as f:
                        f.write(self.current_report)
                QMessageBox.information(self, "Exported", f"Report saved to {fname}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")