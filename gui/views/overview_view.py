"""
Overview View
Dashboard and overview workspace for research activities.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt

from gui.core.service_registry import ServiceRegistry
from gui.core.backend_adapter import BackendServiceAdapter

class OverviewView(QWidget):
    """Overview workspace showing research dashboard and statistics."""
    
    def __init__(self, service_registry: ServiceRegistry, backend: BackendServiceAdapter, main_window=None):
        super().__init__()
        self.service_registry = service_registry
        self.backend = backend
        self.main_window = main_window
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize overview UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Overview")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Statistics cards
        stats_layout = QHBoxLayout()
        
        # Storage card
        storage_card = self.create_stat_card("Storage", "💾")
        self.update_storage_card(storage_card)
        stats_layout.addWidget(storage_card)
        
        # Research sessions card
        research_card = self.create_stat_card("Research Sessions", "🔍")
        self.update_research_card(research_card)
        stats_layout.addWidget(research_card)
        
        # Crawl jobs card
        crawl_card = self.create_stat_card("Crawl Jobs", "🕷️")
        self.update_crawl_card(crawl_card)
        stats_layout.addWidget(crawl_card)
        
        # Search queries card
        search_card = self.create_stat_card("Search Queries", "🔎")
        self.update_search_card(search_card)
        stats_layout.addWidget(search_card)
        
        layout.addLayout(stats_layout)
        
        # Recent activity section
        activity_frame = QFrame()
        activity_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        activity_layout = QVBoxLayout(activity_frame)
        
        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        activity_layout.addWidget(activity_title)
        
        # Recent activities list
        self.activities_list = QLabel("No recent activity")
        self.activities_list.setStyleSheet("padding: 10px; font-family: monospace;")
        self.activities_list.setWordWrap(True)
        activity_layout.addWidget(self.activities_list)
        
        layout.addWidget(activity_frame)
        
        # Quick actions section
        actions_frame = QFrame()
        actions_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        actions_layout = QVBoxLayout(actions_frame)
        
        actions_title = QLabel("Quick Actions")
        actions_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        actions_layout.addWidget(actions_title)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        new_research_btn = self.create_action_button("New Research", "Start a new research session")
        if self.main_window:
            new_research_btn.clicked.connect(self.main_window.show_new_research_dialog)
        button_layout.addWidget(new_research_btn)
        
        new_crawl_btn = self.create_action_button("New Crawl", "Start a new crawl job")
        if self.main_window:
            new_crawl_btn.clicked.connect(self.main_window.show_new_crawl_dialog)
        button_layout.addWidget(new_crawl_btn)
        
        search_btn = self.create_action_button("Search", "Search through documents")
        if self.main_window:
            search_btn.clicked.connect(self.main_window.show_search_workspace)
        button_layout.addWidget(search_btn)
        
        explore_btn = self.create_action_button("Explore", "Explore website structure")
        if self.main_window:
            explore_btn.clicked.connect(self.main_window.show_site_explorer_workspace)
        button_layout.addWidget(explore_btn)
        
        actions_layout.addLayout(button_layout)
        
        layout.addWidget(actions_frame)
    
    def create_stat_card(self, title: str, icon: str):
        """Create a statistics card."""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        card_layout = QVBoxLayout(card)
        
        # Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding-left: 10px;")
        header_layout.addWidget(title_label, stretch=1)
        
        card_layout.addLayout(header_layout)
        
        # Card content
        self_value_label = QLabel("-")
        self_value_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #3498db;")
        self_value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self_value_label)
        
        unit_label = QLabel("")
        unit_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        unit_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(unit_label)
        
        # Store references for updates
        card.value_label = self_value_label
        card.unit_label = unit_label
        
        card.setLayout(card_layout)
        card.setMinimumHeight(120)
        card.setMaximumHeight(160)
        
        return card
    
    def create_action_button(self, text: str, tooltip: str):
        """Create an action button."""
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1e6391;
            }
        """)
        return button
    
    def update_storage_card(self, card):
        """Update storage statistics card."""
        storage_service = self.backend.get_storage_service()
        if storage_service:
            status = storage_service.get_storage_status()
            
            total_gb = status.get('total_bytes', 0) / (1024**3)
            hard_gb = status.get('hard_ceiling_bytes', 0) / (1024**3)
            used_gb = total_gb
            
            card.value_label.setText(f"{used_gb:.1f}")
            card.unit_label.setText(f"of {hard_gb:.0f} GiB")
    
    def update_research_card(self, card):
        """Update research sessions card."""
        card.value_label.setText("0")
        card.unit_label.setText("active sessions")
    
    def update_crawl_card(self, card):
        """Update crawl jobs card."""
        card.value_label.setText("0")
        card.unit_label.setText("running/paused")
    
    def update_search_card(self, card):
        """Update search queries card."""
        card.value_label.setText("0")
        card.unit_label.setText("queries today")
