"""
Crawl Dialog Widget
Dialog for configuring crawl operations.
"""

import sys
import json
import os
import urllib.request
import urllib.parse
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QFormLayout, QPushButton, QDialogButtonBox, QMessageBox, 
    QSpinBox, QTextEdit, QDoubleSpinBox, QCheckBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    print("[DEBUG] crawl_dialog: BeautifulSoup not available", file=sys.stderr)

sys.path.insert(0, '/home/jason/ScrapeEngine')
try:
    from scrape_engine import ScraperEngine, ScraperConfig, DatabaseManager
    from crawl_controller import CrawlController
    from crawl_nlp import CrawlNLPProcessor
    from storage_manager import StorageManager
except Exception as e:
    print(f"[DEBUG] crawl_dialog: Import failed: {e}", file=sys.stderr)

class CrawlWorker(QThread):
    """Worker thread for running crawl operations."""
    progress = Signal(dict)
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, config, service_registry=None, job_id=None):
        super().__init__()
        self.config = config
        self.service_registry = service_registry
        self.engine = None
        self.job_id = job_id
        
    def run(self):
        try:
            # Create storage manager
            storage = StorageManager('.storage')
            
            # Check if search-first mode is enabled
            search_first = self.config.get('search_first', False)
            search_results_count = self.config.get('search_results', 5)
            search_engine = self.config.get('search_engine', 'Google')
            
            urls_to_crawl = []
            
            if search_first:
                # Use instructions as search query
                search_query = self.config.get('instructions', '')
                if not search_query:
                    self.error.emit("Search First enabled but no instructions provided")
                    return
                    
                self.progress.emit({"status": "searching", "message": f"Searching {search_engine} for: {search_query[:80]}...", "job_id": self.job_id})
                
                # Perform search based on selected engine
                urls_to_crawl = self.perform_search(
                    search_query, 
                    search_results_count, 
                    search_engine
                )
                
                if not urls_to_crawl:
                    self.error.emit("Search returned no results to crawl")
                    return
                
                self.progress.emit({"status": "search_complete", "message": f"Found {len(urls_to_crawl)} results to crawl", "job_id": self.job_id})
            else:
                # Traditional single URL crawl
                urls_to_crawl = [self.config['start_url']]
            
            all_results = []
            
            # Crawl each URL
            for i, url in enumerate(urls_to_crawl):
                if i >= self.config.get('max_pages', 10):
                    break
                
                self.progress.emit({"status": "crawling", "message": f"Crawling {i+1}/{len(urls_to_crawl)}: {url[:60]}...", "pages_crawled": len(all_results), "job_id": self.job_id})
                
                # Create scraper config for this URL
                scraper_config = ScraperConfig(
                    start_url=url,
                    max_depth=self.config['max_depth'],
                    max_pages=1,  # One URL at a time
                    request_delay=self.config.get('request_delay', 1.0),
                    same_domain=self.config.get('same_domain', True),
                    obey_robots=self.config.get('obey_robots', True),
                    timeout=self.config.get('timeout', 15.0),
                    retries=self.config.get('retries', 2),
                    max_bytes=self.config.get('max_bytes', 2_000_000),
                    user_agent=self.config.get('user_agent', 'EducationalScraper/1.0 (+respectful public-page research)'),
                    instructions=self.config.get('instructions', '')
                )
                
                # Create engine and run crawl
                engine = ScraperEngine(scraper_config, db_path='scrape_engine.db', storage_manager=storage)
                
                # Process instructions if provided
                if scraper_config.instructions and hasattr(engine, 'nlp_processor') and engine.nlp_processor:
                    try:
                        engine.objectives = engine.nlp_processor.process_instructions(scraper_config.instructions)
                        self.progress.emit({"status": "processing", "message": f"NLP objectives: {engine.objectives.primary_subject if engine.objectives else 'None'}", "job_id": self.job_id})
                    except Exception as e:
                        print(f"[DEBUG] CrawlWorker: NLP processing failed: {e}", file=sys.stderr)
                
                # Run the crawl for this URL
                results = engine.crawl()
                all_results.extend(results)
                
                engine.db.conn.close()
            
            # Get stats
            stats = engine.db.stats() if hasattr(engine, 'db') and hasattr(engine.db, 'stats') else {}
            storage_report = storage.get_usage_report() if hasattr(storage, 'get_usage_report') else {}
            
            # Unregister worker
            if self.service_registry:
                workers = self.service_registry.get("crawl_workers", {})
                if self.job_id in workers:
                    del workers[self.job_id]
                self.service_registry.register("crawl_workers", workers)
            
            self.finished.emit({
                "pages_crawled": len(all_results),
                "results": all_results,
                "stats": stats,
                "storage": storage_report,
                "job_id": self.job_id
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # Unregister worker on error
            if self.service_registry:
                workers = self.service_registry.get("crawl_workers", {})
                if self.job_id in workers:
                    del workers[self.job_id]
                self.service_registry.register("crawl_workers", workers)
            
            self.error.emit(str(e))
    
    def perform_search(self, query, count, engine_name):
        """Perform search and extract result URLs."""
        import urllib.request
        import urllib.parse
        import re
        from bs4 import BeautifulSoup
        
        try:
            if engine_name == "Google":
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={count}"
            elif engine_name == "DuckDuckGo":
                search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            elif engine_name == "Bing":
                search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={count}"
            else:
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={count}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', errors='replace')
            
            soup = BeautifulSoup(html, 'html.parser')
            urls = []
            
            if engine_name == "Google":
                # Google result links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/url?q='):
                        url = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
                        if url.startswith('http'):
                            urls.append(url)
                    elif href.startswith('http') and 'google.com' not in href:
                        urls.append(href)
            elif engine_name == "DuckDuckGo":
                # DuckDuckGo result links are in result__a class, with redirect URLs
                for link in soup.find_all('a', class_='result__a', href=True):
                    href = link['href']
                    # Extract actual URL from DDG redirect: //duckduckgo.com/l/?uddg=<encoded_url>&rut=...
                    if '/l/?uddg=' in href:
                        # Extract the uddg parameter
                        import urllib.parse as up
                        parsed = up.urlparse('https:' + href if href.startswith('//') else href)
                        params = up.parse_qs(parsed.query)
                        if 'uddg' in params:
                            real_url = params['uddg'][0]
                            urls.append(real_url)
                    elif href.startswith('http'):
                        urls.append(href)
            elif engine_name == "Bing":
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('http') and 'bing.com' not in href and 'microsoft.com' not in href:
                        urls.append(href)
            
            # Deduplicate
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            return unique_urls[:count]
            
        except Exception as e:
            print(f"[DEBUG] CrawlWorker: Search failed: {e}", file=sys.stderr)
            return []
    
    def pause(self):
        """Pause the crawl."""
        if self.engine:
            self.engine.pause()
            self.progress.emit({"status": "pausing", "message": "Pausing crawl...", "job_id": self.job_id})
    
    def resume(self):
        """Resume the crawl."""
        if self.engine:
            self.engine.resume()
            self.progress.emit({"status": "resuming", "message": "Resuming crawl...", "job_id": self.job_id})
    
    def is_paused(self):
        """Check if crawl is paused."""
        return self.engine and self.engine.is_paused()

class CrawlDialog(QDialog):
    """Dialog for creating and configuring crawl sessions."""
    
    def __init__(self, service_registry=None, parent=None):
        # Handle compatibility
        if service_registry is not None and parent is None and hasattr(service_registry, 'show'):
            # First arg might be parent
            parent = service_registry
            service_registry = None
        
        if service_registry is None and parent is not None:
            try:
                service_registry = getattr(parent, 'service_registry', None)
            except Exception:
                pass
        
        super().__init__(parent)
        self.service_registry = service_registry
        self.config_file = os.path.expanduser('~/.kilo/crawl_config.json')
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        except Exception:
            pass
        
        self.worker = None
        self.setWindowTitle("New Crawl Session")
        self.setMinimumSize(600, 600)
        self.resize(600, 650)
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("New Crawl Session")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(15)
        
        # URL (required for direct crawl, optional for search-first)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com (optional when Search First is enabled)")
        form_layout.addRow("Start URL:", self.url_input)
        
        # Natural Language Instructions - used as search query when Search First is enabled
        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText(
            "Describe what you want to find, what information should be extracted, "
            "which keywords or phrases matter, and what types of pages should be "
            "prioritized or excluded. For example: Find technical information about "
            "ESP32 audio streaming. Prioritize UDP and TCP transmission, microphone "
            "sensitivity, low-latency processing, noise reduction, and audio compression. "
            "Extract technical specifications, code examples, configuration values, "
            "and useful external references.\n\n"
            "When 'Search First' is enabled, this text is used as the search query."
        )
        self.instructions_input.setMinimumHeight(120)
        form_layout.addRow("Natural Language Instructions:", self.instructions_input)
        
        # Depth
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(3)
        form_layout.addRow("Crawl Depth:", self.depth_spin)
        
        # Max pages
        self.max_pages_spin = QSpinBox()
        self.max_pages_spin.setRange(1, 10000)
        self.max_pages_spin.setValue(500)
        form_layout.addRow("Max Pages:", self.max_pages_spin)
        
        # Request Delay
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 60.0)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setSuffix(" s")
        form_layout.addRow("Request Delay:", self.delay_spin)
        
        # Timeout
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(5.0, 120.0)
        self.timeout_spin.setValue(15.0)
        self.timeout_spin.setSingleStep(1.0)
        self.timeout_spin.setSuffix(" s")
        form_layout.addRow("Timeout:", self.timeout_spin)
        
        # Retries
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(2)
        form_layout.addRow("Retries:", self.retries_spin)
        
        # Max bytes
        self.max_bytes_spin = QSpinBox()
        self.max_bytes_spin.setRange(100000, 50000000)
        self.max_bytes_spin.setValue(2000000)
        self.max_bytes_spin.setSingleStep(100000)
        self.max_bytes_spin.setSuffix(" bytes")
        form_layout.addRow("Max Page Size:", self.max_bytes_spin)
        
        # Same Domain checkbox - OFF by default for broader crawl
        self.same_domain_check = QCheckBox()
        self.same_domain_check.setChecked(False)
        form_layout.addRow("Same Domain Only:", self.same_domain_check)
        
        # Obey robots.txt checkbox
        self.obey_robots_check = QCheckBox()
        self.obey_robots_check.setChecked(False)
        form_layout.addRow("Obey robots.txt:", self.obey_robots_check)
        
        # Search First checkbox - search then crawl results
        self.search_first_check = QCheckBox()
        self.search_first_check.setChecked(False)
        self.search_first_check.setToolTip("First search for the query/URL, then crawl the top N results")
        form_layout.addRow("Search First (crawl top results):", self.search_first_check)
        
        # Number of search results to crawl
        self.search_results_spin = QSpinBox()
        self.search_results_spin.setRange(1, 50)
        self.search_results_spin.setValue(5)
        self.search_results_spin.setEnabled(False)
        self.search_first_check.toggled.connect(self.search_results_spin.setEnabled)
        form_layout.addRow("Results to Crawl:", self.search_results_spin)
        
        # Search engine selector
        self.search_engine_combo = QComboBox()
        self.search_engine_combo.addItems(["Google", "DuckDuckGo", "Bing"])
        self.search_engine_combo.setEnabled(False)
        self.search_first_check.toggled.connect(self.search_engine_combo.setEnabled)
        form_layout.addRow("Search Engine:", self.search_engine_combo)
        
        # User Agent
        self.user_agent_input = QLineEdit()
        self.user_agent_input.setText("EducationalScraper/1.0 (+respectful public-page research)")
        form_layout.addRow("User Agent:", self.user_agent_input)
        
        layout.addLayout(form_layout)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setText("Start Crawl")
        button_box.accepted.connect(self.start_crawl)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def start_crawl(self):
        """Start the crawl with configuration."""
        config = self.get_config()
        url = config['start_url']
        search_first = config['search_first']
        instructions = config['instructions']
        
        if search_first:
            # In search-first mode, instructions are used as search query
            if not instructions:
                QMessageBox.warning(self, "Missing Instructions", 
                    "Please enter natural language instructions to use as the search query.")
                return
        else:
            # Direct crawl mode requires a URL
            if not url:
                QMessageBox.warning(self, "Invalid URL", "Please enter a start URL")
                return
            if not (url.startswith('http://') or url.startswith('https://')):
                QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
                return
        
        if config['max_depth'] < 0 or config['max_pages'] < 1:
            QMessageBox.warning(self, "Invalid Parameters", "Please check depth and page limits")
            return
        
        try:
            # Save config
            self.save_config()
            
            # Generate job ID upfront so we can track it
            import uuid
            job_id = f"crawl_{uuid.uuid4().hex[:12]}"
            
            # Register worker in service registry for pause/resume
            if self.service_registry:
                workers = self.service_registry.get("crawl_workers", {})
                # We'll register after creating worker
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_label.setText("Starting crawl...")
            self.ok_button.setEnabled(False)
            
            # Start worker thread
            self.worker = CrawlWorker(config, self.service_registry, job_id)
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
            
            # Register worker
            if self.service_registry:
                workers = self.service_registry.get("crawl_workers")
                if workers is None:
                    workers = {}
                workers[job_id] = self.worker
                self.service_registry.register("crawl_workers", workers)
            
            self.worker.start()
            
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Error starting crawl: {e}", file=__import__('sys').stderr)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start crawl: {e}")
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.ok_button.setEnabled(True)
    
    def on_progress(self, data):
        """Handle progress updates from worker."""
        status = data.get('status', '')
        message = data.get('message', '')
        self.progress_label.setText(message)
    
    def on_finished(self, data):
        """Handle crawl completion."""
        pages = data.get('pages_crawled', 0)
        stats = data.get('stats', {})
        storage = data.get('storage', {})
        
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.ok_button.setEnabled(True)
        
        # Build summary message
        msg = f"Crawl completed!\nPages crawled: {pages}"
        if stats:
            msg += f"\nTotal pages in DB: {stats.get('total_pages', 'N/A')}"
        if storage:
            used = storage.get('total_bytes', 0) / 1024 / 1024
            msg += f"\nStorage used: {used:.1f} MB"
        
        QMessageBox.information(self, "Crawl Complete", msg)
        self.accept()
    
    def on_error(self, error_msg):
        """Handle crawl error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.ok_button.setEnabled(True)
        QMessageBox.critical(self, "Crawl Error", f"Crawl failed: {error_msg}")
    
    def get_config(self):
        """Get the crawl configuration."""
        return {
            "start_url": self.url_input.text().strip(),
            "instructions": self.instructions_input.toPlainText().strip(),
            "max_depth": self.depth_spin.value(),
            "max_pages": self.max_pages_spin.value(),
            "request_delay": self.delay_spin.value(),
            "timeout": self.timeout_spin.value(),
            "retries": self.retries_spin.value(),
            "max_bytes": self.max_bytes_spin.value(),
            "same_domain": self.same_domain_check.isChecked(),
            "obey_robots": self.obey_robots_check.isChecked(),
            "user_agent": self.user_agent_input.text().strip(),
            "search_first": self.search_first_check.isChecked(),
            "search_results": self.search_results_spin.value(),
            "search_engine": self.search_engine_combo.currentText()
        }
    
    def load_config(self):
        """Load saved crawl configuration."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                if 'start_url' in config:
                    self.url_input.setText(config['start_url'])
                if 'instructions' in config:
                    self.instructions_input.setPlainText(config['instructions'])
                if 'max_depth' in config:
                    self.depth_spin.setValue(int(config['max_depth']))
                if 'max_pages' in config:
                    self.max_pages_spin.setValue(int(config['max_pages']))
                if 'request_delay' in config:
                    self.delay_spin.setValue(float(config['request_delay']))
                if 'timeout' in config:
                    self.timeout_spin.setValue(float(config['timeout']))
                if 'retries' in config:
                    self.retries_spin.setValue(int(config['retries']))
                if 'max_bytes' in config:
                    self.max_bytes_spin.setValue(int(config['max_bytes']))
                if 'same_domain' in config:
                    self.same_domain_check.setChecked(bool(config['same_domain']))
                if 'obey_robots' in config:
                    self.obey_robots_check.setChecked(bool(config['obey_robots']))
                if 'user_agent' in config:
                    self.user_agent_input.setText(config['user_agent'])
                if 'search_first' in config:
                    self.search_first_check.setChecked(bool(config['search_first']))
                    self.search_results_spin.setEnabled(config['search_first'])
                    self.search_engine_combo.setEnabled(config['search_first'])
                if 'search_results' in config:
                    self.search_results_spin.setValue(int(config['search_results']))
                if 'search_engine' in config:
                    index = self.search_engine_combo.findText(config['search_engine'])
                    if index >= 0:
                        self.search_engine_combo.setCurrentIndex(index)
                print("[DEBUG] crawl_dialog: Loaded saved config", file=__import__('sys').stderr)
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Failed to load config: {e}", file=__import__('sys').stderr)
    
    def save_config(self):
        """Save crawl configuration."""
        try:
            config = self.get_config()
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print("[DEBUG] crawl_dialog: Saved config", file=__import__('sys').stderr)
        except Exception as e:
            print(f"[DEBUG] crawl_dialog: Failed to save config: {e}", file=__import__('sys').stderr)
    
    def reject(self):
        """Handle cancel/close - stop worker if running."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(3000)
        super().reject()

