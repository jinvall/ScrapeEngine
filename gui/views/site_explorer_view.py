"""
Site Explorer View
Four synchronized views for domain/sitemap hierarchy, URL path tree, internal-link graph, and URL inventory.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeView, QTableView,
    QSplitter, QFrame, QTabWidget, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter

class SiteExplorerView(QWidget):
    """Site Explorer workspace with four synchronized views."""
    
    def __init__(self, service_registry: ServiceRegistry, backend: BackendServiceAdapter):
        super().__init__()
        self.service_registry = service_registry
        self.backend = backend
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize site explorer UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Site Explorer")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Domain and Sitemap Tree
        left_panel = self.create_domain_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Tabbed content
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter sizes
        main_splitter.setSizes([300, 500])
        
        layout.addWidget(main_splitter)
    
    def create_domain_panel(self):
        """Create the left domain panel with tree views."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Domain tree section
        domain_frame = QFrame()
        domain_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        domain_layout = QVBoxLayout(domain_frame)
        domain_layout.setContentsMargins(15, 15, 15, 15)
        
        domain_title = QLabel("Domain/Sitemap Tree")
        domain_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        domain_layout.addWidget(domain_title)
        
        # Domain tree view
        self.domain_tree = QTreeView()
        self.domain_tree.setHeaderHidden(False)
        self.setup_domain_tree()
        domain_layout.addWidget(self.domain_tree)
        
        panel_layout.addWidget(domain_frame)
        
        # Sitemap info section
        sitemap_frame = QFrame()
        sitemap_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        sitemap_layout = QVBoxLayout(sitemap_frame)
        sitemap_layout.setContentsMargins(15, 15, 15, 15)
        
        sitemap_title = QLabel("Sitemap Information")
        sitemap_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        sitemap_layout.addWidget(sitemap_title)
        
        self.sitemap_info = QLabel("No sitemap selected")
        self.sitemap_info.setStyleSheet("padding: 10px; font-family: monospace;")
        self.sitemap_info.setWordWrap(True)
        sitemap_layout.addWidget(self.sitemap_info)
        
        panel_layout.addWidget(sitemap_frame)
        
        return panel
    
    def create_right_panel(self):
        """Create the right panel with tabbed content."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # URL Path Tree tab
        path_tab = self.create_path_tab()
        self.tabs.addTab(path_tab, "URL Path Tree")
        
        # Internal Link Graph tab
        graph_tab = self.create_graph_tab()
        self.tabs.addTab(graph_tab, "Internal Link Graph")
        
        # URL Inventory tab
        inventory_tab = self.create_inventory_tab()
        self.tabs.addTab(inventory_tab, "URL Inventory")
        
        panel_layout.addWidget(self.tabs)
        
        return panel
    
    def create_path_tab(self):
        """Create the URL path tree tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tree view for URL path hierarchy
        self.path_tree = QTreeView()
        self.path_tree.setHeaderHidden(False)
        self.setup_path_tree()
        layout.addWidget(self.path_tree)
        
        return tab
    
    def create_graph_tab(self):
        """Create the internal link graph tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Graphics view for link graph
        self.graph_view = QGraphicsView()
        self.graph_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.graph_scene = QGraphicsScene()
        self.graph_view.setScene(self.graph_scene)
        
        layout.addWidget(self.graph_view)
        
        return tab
    
    def create_inventory_tab(self):
        """Create the URL inventory tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Table view for URL inventory
        self.inventory_table = QTableView()
        self.inventory_table.setEditTriggers(QTableView.NoEditTriggers)
        self.inventory_table.setSelectionBehavior(QTableView.SelectRows)
        self.inventory_table.setSelectionMode(QTableView.SingleSelection)
        self.setup_inventory_table()
        layout.addWidget(self.inventory_table)
        
        return tab
    
    def setup_domain_tree(self):
        """Set up the domain tree model."""
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        
        self.domain_model = QStandardItemModel()
        self.domain_model.setHorizontalHeaderLabels(["Domain", "Sitemaps", "URLs"])
        
        # Add example domain structure
        example_item = QStandardItem("example.com")
        example_item.setChild(0, QStandardItem("sitemap.xml"))
        example_item.setChild(0, 1, QStandardItem("/"))
        
        self.domain_model.appendRow(example_item)
        
        self.domain_tree.setModel(self.domain_model)
        
        # Connect selection
        self.domain_tree.selectionModel().selectionChanged.connect(self.on_domain_selected)
    
    def setup_path_tree(self):
        """Set up the path tree model."""
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        
        self.path_model = QStandardItemModel()
        self.path_model.setHorizontalHeaderLabels(["Path", "Type", "Status"])
        
        # Add example path structure
        root_item = QStandardItem("docs/")
        root_item.setChild(0, QStandardItem("api/"))
        root_item.setChild(0, 1, QStandardItem("directory"))
        
        sub_item = QStandardItem("api/")
        sub_item.setChild(0, QStandardItem("authentication"))
        sub_item.setChild(0, 1, QStandardItem("file.html"))
        sub_item.setChild(1, QStandardItem("directory"))
        
        root_item.child(0).appendRow(sub_item)
        
        self.path_model.appendRow(root_item)
        
        self.path_tree.setModel(self.path_model)
    
    def setup_inventory_table(self):
        """Set up the inventory table model."""
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        
        self.inventory_model = QStandardItemModel()
        headers = ["URL", "Title", "Domain", "Path", "Discovery Method", 
                  "Sitemap Membership", "Crawl Status", "HTTP Status"]
        self.inventory_model.setHorizontalHeaderLabels(headers)
        
        # Add example inventory items
        item = QStandardItem("https://example.com/docs/api/")
        item.setChild(0, QStandardItem("API Documentation"))
        item.setChild(0, 1, QStandardItem("example.com"))
        item.setChild(0, 2, QStandardItem("/docs/api/"))
        item.setChild(0, 3, QStandardItem("internal_link"))
        item.setChild(0, 4, QStandardItem("sitemap.xml"))
        item.setChild(0, 5, QStandardItem("completed"))
        item.setChild(0, 6, QStandardItem("200"))
        
        self.inventory_model.appendRow(item)
        
        self.inventory_table.setModel(self.inventory_model)
    
    def on_domain_selected(self, selected, deselected):
        """Handle domain selection changes."""
        indexes = selected.indexes()
        if indexes:
            model = self.domain_tree.model()
            domain_item = model.itemFromIndex(indexes[0])
            if domain_item:
                domain_name = domain_item.text()
                self.update_sitemap_info(domain_name)
    
    def update_sitemap_info(self, domain_name: str):
        """Update sitemap information display."""
        # Example sitemap info - would integrate with actual sitemap service
        info = f"""
Domain: {domain_name}
Status: Active
Sitemap URLs: 12
URLs Crawled: 8
Last Updated: 2024-01-15 10:30:00

Discovered Sitemaps:
- {domain_name}/sitemap.xml
- {domain_name}/sitemap_index.xml

URL Coverage: 66% (8/12 URLs)
        """.strip()
        
        self.sitemap_info.setText(info)
    
    def update_graph(self, domain_name: str):
        """Update the internal link graph display."""
        self.graph_scene.clear()
        
        # Example graph implementation
        # This would integrate with actual link data from backend
        self.add_example_links_to_graph()
    
    def add_example_links_to_graph(self):
        """Add example links to the graph for demonstration."""
        # Example nodes
        nodes = [
            ("https://example.com/", 0, 0),
            ("https://example.com/docs/", 100, 100),
            ("https://example.com/docs/api/", 200, 100),
            ("https://example.com/docs/guides/", 100, 200),
            ("https://example.com/blog/", 300, 150),
        ]
        
        # Add nodes
        for url, x, y in nodes:
            text_item = QGraphicsTextItem(url)
            text_item.setPos(x, y)
            self.graph_scene.addItem(text_item)
            
            # Create node ellipse
            node_ellipse = QGraphicsEllipseItem(x-30, y-10, 60, 20)
            node_ellipse.setBrush(QBrush(QColor(52, 152, 219, 100)))
            node_ellipse.setPen(QPen(QColor(41, 128, 185), 2))
            self.graph_scene.addItem(node_ellipse)
        
        # Add example links
        links = [
            (0, 1), (0, 2), (1, 2), (1, 3), (0, 4)
        ]
        
        for from_idx, to_idx in links:
            from_node = nodes[from_idx]
            to_node = nodes[to_idx]
            
            line = QGraphicsLineItem(
                QPointF(from_node[1], from_node[2]),
                QPointF(to_node[1], to_node[2])
            )
            line.setPen(QPen(QColor(100, 100, 100, 150), 2))
            self.graph_scene.addItem(line)
    
    def get_selected_domain(self):
        """Get the currently selected domain."""
        selection = self.domain_tree.selectionModel()
        if selection.hasSelection():
            index = selection.currentIndex()
            if index.isValid():
                model = self.domain_tree.model()
                return model.itemFromIndex(index).text()
        return None