"""
Storage View
Monitor and manage 5 GiB storage quota with FIFO eviction.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFormLayout, QMessageBox, QTextEdit, QSplitter,
    QFileDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
import sys
import os

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from storage_manager import StorageManager
except Exception as e:
    print(f"[DEBUG] storage_view: Import failed: {e}", file=sys.stderr)
    StorageManager = None

class StorageView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.storage = None
        if StorageManager:
            self.storage = StorageManager('.storage')
        
        self.init_ui()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_storage)
        self.refresh_timer.start(5000)
        
        self.refresh_storage()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Storage Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        # Quota Overview
        quota_group = QGroupBox("Quota Overview")
        quota_layout = QVBoxLayout(quota_group)
        
        # Progress bar with color coding
        self.quota_bar = QProgressBar()
        self.quota_bar.setRange(0, 100)
        self.quota_bar.setFormat("%p%")
        self.quota_bar.setTextVisible(True)
        self.quota_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        quota_layout.addWidget(self.quota_bar)
        
        # Quota details
        details_layout = QHBoxLayout()
        
        self.used_label = QLabel("Used: 0 B")
        self.used_label.setFont(QFont("Monospace", 11))
        details_layout.addWidget(self.used_label)
        
        self.available_label = QLabel("Available: 0 B")
        self.available_label.setFont(QFont("Monospace", 11))
        details_layout.addWidget(self.available_label)
        
        self.ceiling_label = QLabel("Ceiling: 5 GiB")
        self.ceiling_label.setFont(QFont("Monospace", 11))
        details_layout.addWidget(self.ceiling_label)
        
        quota_layout.addLayout(details_layout)
        layout.addWidget(quota_group)
        
        # Breakdown
        breakdown_group = QGroupBox("Storage Breakdown")
        breakdown_layout = QFormLayout(breakdown_group)
        
        self.blobs_label = QLabel("0 B")
        self.blobs_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Tracked Blobs:", self.blobs_label)
        
        self.metadata_label = QLabel("0 B")
        self.metadata_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Metadata:", self.metadata_label)
        
        self.database_label = QLabel("0 B")
        self.database_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Database:", self.database_label)
        
        self.eviction_label = QLabel("0 B")
        self.eviction_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Eviction Reserve:", self.eviction_label)
        
        self.compression_label = QLabel("N/A")
        self.compression_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Compression Ratio:", self.compression_label)
        
        self.dedup_label = QLabel("N/A")
        self.dedup_label.setFont(QFont("Monospace", 11))
        breakdown_layout.addRow("Deduplication:", self.dedup_label)
        
        layout.addWidget(breakdown_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        verify_btn = QPushButton("Verify Integrity")
        verify_btn.clicked.connect(self.verify_integrity)
        actions_layout.addWidget(verify_btn)
        
        evict_btn = QPushButton("Force Eviction (1 GiB)")
        evict_btn.clicked.connect(self.force_eviction)
        actions_layout.addWidget(evict_btn)
        
        report_btn = QPushButton("Generate Report")
        report_btn.clicked.connect(self.generate_report)
        actions_layout.addWidget(report_btn)
        
        layout.addWidget(actions_group)
        
        # Blob table
        layout.addWidget(QLabel("Blob Metadata"))
        
        self.blob_table = QTableWidget()
        self.blob_table.setColumnCount(6)
        self.blob_table.setHorizontalHeaderLabels([
            "SHA256", "Compressed", "Original", "Refs", "Tags", "Collection"
        ])
        self.blob_table.horizontalHeader().setStretchLastSection(True)
        self.blob_table.setAlternatingRowColors(True)
        self.blob_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.blob_table)
        
        # Status
        self.status_label = QLabel("Loading...")
        layout.addWidget(self.status_label)
    
    def refresh_storage(self):
        """Refresh storage information."""
        if not self.storage:
            self.status_label.setText("StorageManager not available")
            return
        
        try:
            usage = self.storage.get_usage_report()
            
            # Update quota bar
            pct = usage.get('pct_used', 0)
            self.quota_bar.setValue(int(pct * 100) if pct > 0 else 0)
            
            # Color code based on usage
            if pct >= 0.95:
                color = "#e74c3c"  # Red
            elif pct >= 0.80:
                color = "#f39c12"  # Orange
            else:
                color = "#27ae60"  # Green
            
            self.quota_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid #bdc3c7;
                    border-radius: 5px;
                    text-align: center;
                    height: 25px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)
            
            # Update labels
            used = usage.get('total_bytes', 0)
            available = usage.get('available_bytes', 0)
            ceiling = usage.get('hard_ceiling_bytes', 0)
            
            self.used_label.setText(f"Used: {self.format_bytes(used)}")
            self.available_label.setText(f"Available: {self.format_bytes(available)}")
            self.ceiling_label.setText(f"Ceiling: {self.format_bytes(ceiling)}")
            
            # Breakdown
            breakdown = usage.get('breakdown', {})
            self.blobs_label.setText(self.format_bytes(breakdown.get('blobs_tracked', 0) * 1024 * 1024))
            self.metadata_label.setText(self.format_bytes(breakdown.get('metadata_untracked', 0) * 1024 * 1024))
            self.database_label.setText(self.format_bytes(breakdown.get('database', 0) * 1024 * 1024))
            self.eviction_label.setText(self.format_bytes(breakdown.get('eviction_untracked', 0) * 1024 * 1024))
            
            self.compression_label.setText(f"{usage.get('compression_ratio', 0):.2f}x")
            
            # Deduplication info
            try:
                c = self.storage.db_conn.cursor()
                c.execute("SELECT COUNT(*), SUM(reference_count) FROM storage_metadata")
                row = c.fetchone()
                if row:
                    unique_blobs = row[0]
                    total_refs = row[1] or 0
                    if unique_blobs > 0:
                        self.dedup_label.setText(f"{total_refs} refs / {unique_blobs} blobs ({total_refs/unique_blobs:.1f}x)")
            except Exception:
                pass
            
            # Populate blob table
            self.refresh_blob_table()
            
            self.status_label.setText(f"Last updated: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {e}")
    
    def refresh_blob_table(self):
        """Populate blob metadata table."""
        if not self.storage:
            return
        
        try:
            c = self.storage.db_conn.cursor()
            c.execute("""
                SELECT sha256_hex, size_compressed, size_uncompressed, reference_count, tags, collection
                FROM storage_metadata
                ORDER BY ingestion_timestamp DESC
                LIMIT 200
            """)
            blobs = c.fetchall()
            
            self.blob_table.setRowCount(len(blobs))
            
            for row, blob in enumerate(blobs):
                sha256, comp_size, orig_size, refs, tags, collection = blob
                
                # Truncate SHA256
                sha_display = sha256[:16] + "..." + sha256[-8:]
                self.blob_table.setItem(row, 0, QTableWidgetItem(sha_display))
                self.blob_table.item(row, 0).setToolTip(sha256)
                
                self.blob_table.setItem(row, 1, QTableWidgetItem(self.format_bytes(comp_size)))
                self.blob_table.setItem(row, 2, QTableWidgetItem(self.format_bytes(orig_size)))
                self.blob_table.setItem(row, 3, QTableWidgetItem(str(refs)))
                
                # Parse tags
                import json
                try:
                    tag_list = json.loads(tags) if tags else []
                    self.blob_table.setItem(row, 4, QTableWidgetItem(", ".join(tag_list)))
                except:
                    self.blob_table.setItem(row, 4, QTableWidgetItem(""))
                
                self.blob_table.setItem(row, 5, QTableWidgetItem(collection or ""))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def format_bytes(self, bytes_val):
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
    
    def verify_integrity(self):
        """Verify storage integrity."""
        if not self.storage:
            QMessageBox.warning(self, "Unavailable", "StorageManager not available")
            return
        
        self.status_label.setText("Verifying integrity...")
        QApplication.processEvents()
        
        try:
            issues = self.storage.verify_integrity()
            if issues:
                msg = f"Found {len(issues)} integrity issues:\n\n"
                for issue in issues[:20]:
                    msg += f"- {issue}\n"
                if len(issues) > 20:
                    msg += f"\n... and {len(issues) - 20} more"
                QMessageBox.warning(self, "Integrity Issues", msg)
            else:
                QMessageBox.information(self, "Integrity OK", "All blobs verified successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Verification failed: {e}")
        finally:
            self.refresh_storage()
    
    def force_eviction(self):
        """Force eviction of oldest blobs."""
        if not self.storage:
            QMessageBox.warning(self, "Unavailable", "StorageManager not available")
            return
        
        if QMessageBox.question(self, "Confirm Eviction", 
            "This will evict oldest blobs to free ~1 GiB. Continue?") != QMessageBox.Yes:
            return
        
        self.status_label.setText("Evicting...")
        QApplication.processEvents()
        
        try:
            self.storage.eviction.run_eviction(target_bytes=1024**3)
            QMessageBox.information(self, "Eviction Complete", "Eviction finished")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Eviction failed: {e}")
        finally:
            self.refresh_storage()
    
    def generate_report(self):
        """Generate storage report."""
        if not self.storage:
            QMessageBox.warning(self, "Unavailable", "StorageManager not available")
            return
        
        try:
            from gui.widgets.crawl_dialog import CrawlDialog
            # Reuse export functionality
            fname, _ = QFileDialog.getSaveFileName(
                self, "Save Storage Report", 
                f"storage_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                "Markdown Files (*.md)"
            )
            if fname:
                usage = self.storage.get_usage_report()
                
                report = f"# Storage Report\n\n"
                report += f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n"
                
                report += "## Quota\n"
                report += f"- **Used:** {self.format_bytes(usage.get('total_bytes', 0))}\n"
                report += f"- **Available:** {self.format_bytes(usage.get('available_bytes', 0))}\n"
                report += f"- **Ceiling:** {self.format_bytes(usage.get('hard_ceiling_bytes', 0))}\n"
                report += f"- **Usage:** {usage.get('pct_used', 0):.2f}%\n\n"
                
                report += "## Breakdown\n"
                breakdown = usage.get('breakdown', {})
                for k, v in breakdown.items():
                    report += f"- **{k}:** {v:.2f} MB\n"
                
                report += f"\n## Compression\n- **Ratio:** {usage.get('compression_ratio', 0):.2f}x\n"
                
                with open(fname, 'w') as f:
                    f.write(report)
                
                QMessageBox.information(self, "Report Generated", f"Report saved to {fname}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Report generation failed: {e}")