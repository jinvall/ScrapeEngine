import traceback
"""
Backend Service Adapter
Integrates existing backend modules with GUI service interfaces.
"""

from typing import Dict, Any, List, Optional
from PySide6.QtCore import QObject, QThread, QTimer, Signal

class BackendServiceAdapter(QObject):
    """Adapts existing backend modules to GUI service interfaces."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        
        # Configuration paths - these should point to where actual data lives
        self._db_path = "scrape_engine.db"
        self._storage_root = ".storage"
        
        self._setup_backend_adapters()
    
    def _setup_backend_adapters(self):
        """Set up adapters for all backend modules."""
        # Initialize backend modules from existing codebase
        self._init_backend_modules()
        
        # Register service factories
        self._register_service_factories()
    
    def _init_backend_modules(self):
        """Initialize existing backend modules."""
        # Adapt existing modules to GUI-compatible interfaces
        try:
            # Database and Engine from scrape_engine.py
            from scrape_engine import DatabaseManager, ScraperEngine, ScraperConfig
            self._init_scrape_engine_adapters(DatabaseManager, ScraperEngine, ScraperConfig)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: Could not import scrape_engine: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            # Extraction from extraction.py
            from extraction import StructuredHTMLParser, EntityExtractor, CollectionProfile
            self._init_extraction_adapters(StructuredHTMLParser, EntityExtractor, CollectionProfile)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: Could not import extraction: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            # Sitemap from sitemap_module.py
            from sitemap_module import SitemapParser, URLHierarchy
            self._init_sitemap_adapters(SitemapParser, URLHierarchy)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: Could not import sitemap_module: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            # Storage from storage_manager.py
            from storage_manager import StorageManager
            self._init_storage_adapters(StorageManager)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: Could not import storage_manager: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
        
        try:
            # Query parser
            from query_parser import NaturalLanguageParser, StructuredQuery
            self._init_query_parser_adapters(NaturalLanguageParser, StructuredQuery)
        except Exception as e:
            print(f"[DEBUG] BackendServiceAdapter: Could not import query_parser: {e}", file=__import__("sys").stderr)
            traceback.print_exc()
    
    def _init_scrape_engine_adapters(self, DatabaseManager, ScraperEngine, ScraperConfig):
        """Initialize ScrapeEngine adapters."""
        # Use the actual database with data
        self._database_manager = DatabaseManager(self._db_path)
        self._scraper_engine_class = ScraperEngine
        self._scraper_config_class = ScraperConfig
        
        # Store references in service registry for other components
        self.service_registry.register("database_manager", self._database_manager)
        self.service_registry.register("scraper_engine_class", self._scraper_engine_class)
        self.service_registry.register("scraper_config_class", self._scraper_config_class)
        self.service_registry.register("db_path", self._db_path)
    
    def _init_extraction_adapters(self, StructuredHTMLParser, EntityExtractor, CollectionProfile):
        """Initialize extraction adapters."""
        self._structured_html_parser_class = StructuredHTMLParser
        self._entity_extractor_class = EntityExtractor
        self._collection_profile_class = CollectionProfile
        
        self.service_registry.register("structured_html_parser_class", self._structured_html_parser_class)
        self.service_registry.register("entity_extractor_class", self._entity_extractor_class)
        self.service_registry.register("collection_profile_class", self._collection_profile_class)
    
    def _init_sitemap_adapters(self, SitemapParser, URLHierarchy):
        """Initialize sitemap adapters."""
        self._sitemap_parser_class = SitemapParser
        self._url_hierarchy_class = URLHierarchy
        
        self.service_registry.register("sitemap_parser_class", self._sitemap_parser_class)
        self.service_registry.register("url_hierarchy_class", self._url_hierarchy_class)
    
    def _init_storage_adapters(self, StorageManager):
        """Initialize storage adapters."""
        # Create a persistent storage manager instance with the correct path
        self._storage_manager = StorageManager(self._storage_root)
        
        self.service_registry.register("storage_manager_class", StorageManager)
        self.service_registry.register("storage_manager_instance", self._storage_manager)
        self.service_registry.register("storage_root", self._storage_root)
    
    def _init_query_parser_adapters(self, NaturalLanguageParser, StructuredQuery):
        """Initialize query parser adapters."""
        self._natural_language_parser_class = NaturalLanguageParser
        self._structured_query_class = StructuredQuery
        
        self.service_registry.register("natural_language_parser_class", self._natural_language_parser_class)
        self.service_registry.register("structured_query_class", self._structured_query_class)
    
    def _register_service_factories(self):
        """Register service factories for GUI components."""
        self.service_registry.register_factory("research_service", self._create_research_service)
        self.service_registry.register_factory("search_service", self._create_search_service)
        self.service_registry.register_factory("crawl_service", self._create_crawl_service)
        self.service_registry.register_factory("extraction_service", self._create_extraction_service)
        self.service_registry.register_factory("document_service", self._create_document_service)
        self.service_registry.register_factory("entity_service", self._create_entity_service)
        self.service_registry.register_factory("storage_service", self._create_storage_service)
        self.service_registry.register_factory("report_service", self._create_report_service)
    
    # Service factory methods
    def _create_research_service(self):
        """Create research service adapter."""
        return ResearchServiceAdapter(self.service_registry)
    
    def _create_search_service(self):
        """Create search service adapter."""
        return SearchServiceAdapter(self.service_registry)
    
    def _create_crawl_service(self):
        """Create crawl service adapter."""
        return CrawlServiceAdapter(self.service_registry)
    
    def _create_extraction_service(self):
        """Create extraction service adapter."""
        return ExtractionServiceAdapter(self.service_registry)
    
    def _create_document_service(self):
        """Create document service adapter."""
        return DocumentServiceAdapter(self.service_registry)
    
    def _create_entity_service(self):
        """Create entity service adapter."""
        return EntityServiceAdapter(self.service_registry)
    
    def _create_storage_service(self):
        """Create storage service adapter."""
        return StorageServiceAdapter(self.service_registry)
    
    def _create_report_service(self):
        """Create report service adapter."""
        return ReportServiceAdapter(self.service_registry)
    
    # Individual service getters
    def get_research_service(self):
        """Get research service adapter."""
        return self._create_research_service()
    
    def get_search_service(self):
        """Get search service adapter."""
        return self._create_search_service()
    
    def get_crawl_service(self):
        """Get crawl service adapter."""
        return self._create_crawl_service()
    
    def get_extraction_service(self):
        """Get extraction service adapter."""
        return self._create_extraction_service()
    
    def get_document_service(self):
        """Get document service adapter."""
        return self._create_document_service()
    
    def get_entity_service(self):
        """Get entity service adapter."""
        return self._create_entity_service()
    
    def get_storage_service(self):
        """Get storage service adapter."""
        return self._create_storage_service()
    
    def get_report_service(self):
        """Get report service adapter."""
        return self._create_report_service()

# Service adapter classes
class ResearchServiceAdapter(QObject):
    """Research service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.db = service_registry.get("database_manager")
        self.parser = service_registry.get("natural_language_parser_class")()
    
    def create_research_session(self, query: str) -> Dict:
        """Create a research session from a query."""
        structured_query = self.parser.parse(query)
        
        session_id = f"research_{__import__('datetime').datetime.now().timestamp()}"
        
        return {
            "id": session_id,
            "query": structured_query.__dict__,
            "created": __import__('datetime').datetime.now().isoformat(),
            "status": "active"
        }
    
    def get_research_results(self, session_id: str) -> List[Dict]:
        """Get results for a research session."""
        return []
    
    def pause_research(self, session_id: str) -> bool:
        """Pause a research session."""
        return True
    
    def resume_research(self, session_id: str) -> bool:
        """Resume a research session."""
        return True
class SearchServiceAdapter(QObject):
    """Search service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.db = service_registry.get("database_manager")
        self.parser = service_registry.get("natural_language_parser_class")()
    
    def search_content(self, query: str, filters: Dict = None) -> List[Dict]:
        """Search content based on query and filters."""
        if not self.db:
            return []
        
        structured_query = self.parser.parse(query)
        
        results = []
        
        if structured_query.exact_phrase:
            results.extend(self.db.search_exact_phrase(
                structured_query.exact_phrase,
                domain=structured_query.domains[0] if structured_query.domains else None,
                case_insensitive=True
            ))
        
        if structured_query.required_phrases and not structured_query.exact_phrase:
            for phrase in structured_query.required_phrases[:1]:
                results.extend(self.db.search_literal_substring(
                    phrase,
                    domain=structured_query.domains[0] if structured_query.domains else None,
                    case_insensitive=True
                ))
        
        return results
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions."""
        return [
            f"Search for {partial_query}...",
            f"Scrape {partial_query} website...",
            f"Analyze {partial_query} content..."
        ]
class CrawlServiceAdapter(QObject):
    """Crawl service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.db = service_registry.get("database_manager")
    
    def start_crawl(self, url: str, config: Dict = None) -> str:
        """Start a crawl job."""
        job_id = f"crawl_{__import__('datetime').datetime.now().timestamp()}"
        return job_id
    
    def get_crawl_status(self, job_id: str) -> Dict:
        """Get crawl job status."""
        return {
            "id": job_id,
            "status": "running",
            "progress": 50,
            "pages_crawled": 25,
            "total_pages": 50
        }
class ExtractionServiceAdapter(QObject):
    """Extraction service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.extractor = service_registry.get("structured_html_parser_class")()
        self.entity_extractor = service_registry.get("entity_extractor_class")()
    
    def extract_content(self, url: str, profile: str = "main_text") -> Dict:
        """Extract content from a URL."""
        return {
            "url": url,
            "title": "Extracted Title",
            "text": "Extracted content would appear here...",
            "profile": profile,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    
    def extract_entities(self, text: str, url: str = "") -> List[Dict]:
        """Extract entities from text."""
        if not self.entity_extractor:
            return []
        
        mentions = self.entity_extractor.process_text(text, "general", url)
        return [
            {
                "text": mention.text,
                "type": mention.entity_type,
                "confidence": mention.confidence,
                "section": mention.section.text if mention.section else ""
            }
            for mention in mentions
        ]
class DocumentServiceAdapter(QObject):
    """Document service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.db = service_registry.get("database_manager")
    
    def get_documents(self, filters: Dict = None) -> List[Dict]:
        """Get list of documents."""
        return []
    
    def get_document_content(self, url: str) -> Dict:
        """Get full document content."""
        return {}
class EntityServiceAdapter(QObject):
    """Entity service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.entity_extractor = service_registry.get("entity_extractor_class")()
    
    def get_entities(self, filters: Dict = None) -> List[Dict]:
        """Get entities."""
        return []
    
    def get_entity_details(self, entity_name: str) -> Dict:
        """Get detailed information about an entity."""
        return {
            "name": entity_name,
            "type": "person",
            "aliases": [],
            "mentions": []
        }
class StorageServiceAdapter(QObject):
    """Storage service adapter for GUI."""
    
    storage_updated = Signal(dict)
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        # Use the persistent instance from registry
        self.storage = service_registry.get("storage_manager_instance")
    
    def get_storage_status(self) -> Dict:
        """Get storage usage and quota information."""
        if not self.storage:
            result = {
                "total_bytes": 0,
                "hard_ceiling_bytes": 5 * 1024**3,
                "available_bytes": 5 * 1024**3,
                "pct_used": 0.0
            }
            self.storage_updated.emit(result)
            return result
        
        result = self.storage.get_usage_report()
        self.storage_updated.emit(result)
        return result
    
    def get_storage_breakdown(self) -> Dict:
        """Get detailed storage breakdown."""
        result = self.storage.get_usage_report() if self.storage else {}
        self.storage_updated.emit(result)
        return result
class ReportServiceAdapter(QObject):
    """Report service adapter for GUI."""
    
    def __init__(self, service_registry):
        super().__init__()
        self.service_registry = service_registry
        self.db = service_registry.get("database_manager")
        self.storage = service_registry.get("storage_manager_class")()
    
    def generate_research_report(self, research_id: str, format: str = "markdown") -> str:
        """Generate a research report."""
        return f"# Research Report: {research_id}\n\nContent would appear here..."
    
    def generate_crawl_report(self, crawl_id: str, format: str = "markdown") -> str:
        """Generate a crawl report."""
        return f"# Crawl Report: {crawl_id}\n\nContent would appear here..."
    
    def generate_storage_report(self, format: str = "markdown") -> str:
        """Generate a storage report."""
        return f"# Storage Report\n\nContent would appear here..."