"""
Overview View
Dashboard and overview workspace for research activities.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, QTimer

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
        
        # Set up periodic refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        # Initial refresh
        self.refresh_all()
    
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
        self.storage_card = self.create_stat_card("Storage", "💾")
        stats_layout.addWidget(self.storage_card)
        
        # Research sessions card
        self.research_card = self.create_stat_card("Research Sessions", "🔍")
        stats_layout.addWidget(self.research_card)
        
        # Crawl jobs card
        self.crawl_card = self.create_stat_card("Crawl Jobs", "🕷️")
        stats_layout.addWidget(self.crawl_card)
        
        # Search queries card
        self.search_card = self.create_stat_card("Search Queries", "🔎")
        stats_layout.addWidget(self.search_card)
        
        layout.addLayout(stats_layout)
        
        # Recent activity section
        activity_frame = QFrame()
        activity_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        activity_layout = QVBoxLayout(activity_frame)
        
        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        activity_layout.addWidget(activity_title)
        
        # Recent activities list
        self.activities_list = QLabel("Loading...")
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
    
    def refresh_all(self):
        """Refresh all data from backend services."""
        self.refresh_storage_card()
        self.refresh_research_card()
        self.refresh_crawl_card()
        self.refresh_search_card()
        self.refresh_recent_activity()
    
    def refresh_storage_card(self):
        """Update storage statistics card."""
        storage_service = self.backend.get_storage_service()
        if storage_service:
            status = storage_service.get_storage_status()
            
            total_bytes = status.get('total_bytes', 0)
            hard_gb = status.get('hard_ceiling_bytes', 0) / (1024**3)
            
            # Display in appropriate units
            if total_bytes >= 1024**3:
                used_str = f"{total_bytes / (1024**3):.1f}"
                unit_str = f"of {hard_gb:.0f} GiB"
            elif total_bytes >= 1024**2:
                used_str = f"{total_bytes / (1024**2):.1f}"
                unit_str = f"MiB of {hard_gb:.0f} GiB"
            else:
                used_str = f"{total_bytes / 1024:.1f}"
                unit_str = f"KiB of {hard_gb:.0f} GiB"
            
            self.storage_card.value_label.setText(used_str)
            self.storage_card.unit_label.setText(unit_str)
    
    def refresh_research_card(self):
        """Update research sessions card with real count."""
        # Query database for research sessions
        db = self.service_registry.get("database_manager")
        if db:
            try:
                # Count active research sessions
                c = db.conn.cursor()
                c.execute("SELECT COUNT(*) FROM research_sessions WHERE status = 'active'")
                count = c.fetchone()[0]
                self.research_card.value_label.setText(str(count))
                self.research_card.unit_label.setText("active sessions")
            except Exception:
                self.research_card.value_label.setText("0")
                self.research_card.unit_label.setText("active sessions")
        else:
            self.research_card.value_label.setText("0")
            self.research_card.unit_label.setText("active sessions")
    
    def refresh_crawl_card(self):
        """Update crawl jobs card with real count."""
        db = self.service_registry.get("database_manager")
        if db:
            try:
                c = db.conn.cursor()
                # Count all crawl jobs (running, paused, completed recently)
                c.execute("SELECT COUNT(*) FROM crawl_jobs WHERE status IN ('running', 'paused', 'completed')")
                count = c.fetchone()[0]
                self.crawl_card.value_label.setText(str(count))
                self.crawl_card.unit_label.setText("total jobs")
            except Exception:
                self.crawl_card.value_label.setText("0")
                self.crawl_card.unit_label.setText("total jobs")
        else:
            self.crawl_card.value_label.setText("0")
            self.crawl_card.unit_label.setText("total jobs")
    
    def refresh_search_card(self):
        """Update search queries card with real count from today."""
        db = self.service_registry.get("database_manager")
        if db:
            try:
                from datetime import datetime, timezone
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                c = db.conn.cursor()
                c.execute("SELECT COUNT(*) FROM search_queries WHERE date(created_at) = ?", (today,))
                count = c.fetchone()[0]
                self.search_card.value_label.setText(str(count))
                self.search_card.unit_label.setText("queries today")
            except Exception:
                self.search_card.value_label.setText("0")
                self.search_card.unit_label.setText("queries today")
        else:
            self.search_card.value_label.setText("0")
            self.search_card.unit_label.setText("queries today")
    
    def refresh_recent_activity(self):
        """Update recent activity list with real data."""
        db = self.service_registry.get("database_manager")
        if db:
            try:
                c = db.conn.cursor()
                # Get recent crawls
                c.execute("""
                    SELECT 'crawl' as type, url, status, created_at 
                    FROM crawl_jobs 
                    ORDER BY created_at DESC LIMIT 5
                """)
                crawls = c.fetchall()
                
                # Get recent searches
                c.execute("""
                    SELECT 'search' as type, query, status, created_at 
                    FROM search_queries 
                    ORDER BY created_at DESC LIMIT 5
                """)
                searches = c.fetchall()
                
                # Get recent research
                c.execute("""
                    SELECT 'research' as type, query, status, created_at 
                    FROM research_sessions 
                    ORDER BY created_at DESC LIMIT 5
                """)
                research = c.fetchall()
                
                # Combine and sort
                all_activity = list(crawls) + list(searches) + list(research)
                all_activity.sort(key=lambda x: x[3], reverse=True)
                
                if all_activity:
                    lines = []
                    for act_type, val1, val2, created_at in all_activity[:10]:
                        if act_type == 'crawl':
                            lines.append(f"[{created_at[:16]}] 🕷️ Crawl: {val1[:50]}... ({val2})")
                        elif act_type == 'search':
                            lines.append(f"[{created_at[:16]}] 🔎 Search: {val1[:50]}... ({val2})")
                        elif act_type == 'research':
                            lines.append(f"[{created_at[:16]}] 🔍 Research: {val1[:50]}... ({val2})")
                    self.activities_list.setText("\n".join(lines))
                else:
                    self.activities_list.setText("No recent activity")
            except Exception as e:
                self.activities_list.setText(f"Error loading activity: {e}")
        else:
            self.activities_list.setText("No database connection")
