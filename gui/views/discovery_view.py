"""
Web Discovery View
Discover and analyze website structure via sitemaps and robots.txt.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit, 
    QSplitter, QTabWidget, QMessageBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import sys
import os

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from sitemap_module import SitemapParser, URLHierarchy
except Exception as e:
    print(f"[DEBUG] discovery_view: Import failed: {e}", file=sys.stderr)
    SitemapParser = None
    URLHierarchy = None

class DiscoveryWorker(QThread):
    """Worker for fetching and parsing sitemaps."""
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            if not SitemapParser:
                self.error.emit("SitemapParser not available")
                return
            
            self.progress.emit("Fetching sitemap...")
            parser = SitemapParser(self.url)
            sitemap_data = parser.parse()
            
            self.progress.emit("Building URL hierarchy...")
            hierarchy = URLHierarchy(sitemap_data)
            tree_data = hierarchy.get_tree()
            
            self.progress.emit("Fetching robots.txt...")
            robots = parser.get_robots_txt()
            
            self.finished.emit({
                "sitemap": sitemap_data,
                "hierarchy": tree_data,
                "robots": robots,
                "url_count": len(sitemap_data.get("urls", []))
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class DiscoveryView(QWidget):
    def __init__(self, service_registry=None, backend=None, parent=None):
        super().__init__(parent)
        self.service_registry = service_registry
        self.backend = backend
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title and input
        header_layout = QHBoxLayout()
        title = QLabel("Web Discovery")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setMinimumWidth(400)
        self.url_input.returnPressed.connect(self.start_discovery)
        header_layout.addWidget(self.url_input)
        
        self.discover_btn = QPushButton("Discover")
        self.discover_btn.clicked.connect(self.start_discovery)
        header_layout.addWidget(self.discover_btn)
        
        self.add_to_crawl_btn = QPushButton("Add to Crawl Queue")
        self.add_to_crawl_btn.clicked.connect(self.add_to_crawl_queue)
        self.add_to_crawl_btn.setEnabled(False)
        header_layout.addWidget(self.add_to_crawl_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Tab widget for results
        self.tabs = QTabWidget()
        
        # Sitemap tab
        self.sitemap_tab = QWidget()
        sitemap_layout = QVBoxLayout(self.sitemap_tab)
        
        self.sitemap_tree = QTreeWidget()
        self.sitemap_tree.setHeaderLabels(["URL", "Last Modified", "Change Freq", "Priority"])
        self.sitemap_tree.setAlternatingRowColors(True)
        self.sitemap_tree.setSortingEnabled(True)
        sitemap_layout.addWidget(self.sitemap_tree)
        
        self.tabs.addTab(self.sitemap_tab, "Sitemap")
        
        # Hierarchy tab
        self.hierarchy_tab = QWidget()
        hierarchy_layout = QVBoxLayout(self.hierarchy_tab)
        
        self.hierarchy_tree = QTreeWidget()
        self.hierarchy_tree.setHeaderLabels(["Path", "URL Count", "Depth"])
        self.hierarchy_tree.setAlternatingRowColors(True)
        hierarchy_layout.addWidget(self.hierarchy_tree)
        
        self.tabs.addTab(self.hierarchy_tab, "URL Hierarchy")
        
        # Robots.txt tab
        self.robots_tab = QWidget()
        robots_layout = QVBoxLayout(self.robots_tab)
        
        self.robots_text = QTextEdit()
        self.robots_text.setReadOnly(True)
        self.robots_text.setFont(QFont("Monospace", 10))
        robots_layout.addWidget(self.robots_text)
        
        self.tabs.addTab(self.robots_tab, "robots.txt")
        
        layout.addWidget(self.tabs)
        
        # Stats
        self.stats_label = QLabel("Enter a URL and click Discover")
        layout.addWidget(self.stats_label)
    
    def start_discovery(self):
        """Start sitemap discovery."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL")
            return
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
            return
        
        # Clear previous results
        self.sitemap_tree.clear()
        self.hierarchy_tree.clear()
        self.robots_text.clear()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting discovery...")
        self.discover_btn.setEnabled(False)
        self.add_to_crawl_btn.setEnabled(False)
        
        # Start worker
        self.worker = DiscoveryWorker(url)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, message):
        self.progress_label.setText(message)
    
    def on_finished(self, data):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.discover_btn.setEnabled(True)
        self.add_to_crawl_btn.setEnabled(True)
        
        # Populate sitemap tree
        sitemap = data.get("sitemap", {})
        urls = sitemap.get("urls", [])
        
        for url_data in urls:
            item = QTreeWidgetItem([
                url_data.get("loc", ""),
                url_data.get("lastmod", ""),
                url_data.get("changefreq", ""),
                str(url_data.get("priority", ""))
            ])
            self.sitemap_tree.addTopLevelItem(item)
        
        # Populate hierarchy tree
        hierarchy = data.get("hierarchy", {})
        self.build_hierarchy_tree(hierarchy, self.hierarchy_tree)
        
        # Populate robots.txt
        robots = data.get("robots", "")
        self.robots_text.setPlainText(robots if robots else "(no robots.txt found)")
        
        # Stats
        url_count = data.get("url_count", 0)
        self.stats_label.setText(f"Discovered {url_count} URLs from sitemap")
        
        # Resize columns
        for i in range(4):
            self.sitemap_tree.resizeColumnToContents(i)
        for i in range(3):
            self.hierarchy_tree.resizeColumnToContents(i)
    
    def build_hierarchy_tree(self, node, parent_item):
        """Recursively build hierarchy tree."""
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "_urls":
                    item = QTreeWidgetItem([f"📄 {len(value)} URLs", "", ""])
                    parent_item.addChild(item)
                elif key == "_count":
                    continue
                else:
                    count = value.get("_count", 0) if isinstance(value, dict) else 0
                    item = QTreeWidgetItem([key, str(count), ""])
                    parent_item.addChild(item)
                    self.build_hierarchy_tree(value, item)
    
    def on_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.discover_btn.setEnabled(True)
        QMessageBox.critical(self, "Discovery Error", f"Failed: {error_msg}")
    
    def add_to_crawl_queue(self):
        """Add discovered URLs to crawl queue."""
        # Get selected URLs from sitemap tree
        selected = self.sitemap_tree.selectedItems()
        urls = []
        
        if selected:
            for item in selected:
                urls.append(item.text(0))
        else:
            # Add all URLs
            for i in range(self.sitemap_tree.topLevelItemCount()):
                item = self.sitemap_tree.topLevelItem(i)
                urls.append(item.text(0))
        
        if not urls:
            QMessageBox.information(self, "No URLs", "No URLs to add")
            return
        
        # Open crawl dialog with first URL
        try:
            from gui.widgets.crawl_dialog import CrawlDialog
            dialog = CrawlDialog(self.service_registry, self)
            dialog.url_input.setText(urls[0])
            dialog.max_pages_spin.setValue(min(len(urls), 100))
            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open crawl dialog: {e}")