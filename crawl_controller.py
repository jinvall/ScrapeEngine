"""
Crawl Controller with Natural Language Support
Manages intelligent crawling with NLP-driven prioritization
"""

import json
from typing import Dict, List, Any, Optional
from PySide6.QtCore import QObject, Signal, QThread

from crawl_nlp import CrawlNLPProcessor, CrawlObjectives


class CrawlController(QObject):
    """Controller for managing crawl operations with NLP support."""
    
    # Signals
    progress_updated = Signal(dict)
    page_crawled = Signal(dict)
    crawl_completed = Signal(dict)
    crawl_error = Signal(str)
    
    def __init__(self, service_registry=None):
        super().__init__()
        self.service_registry = service_registry
        self.nlp_processor = CrawlNLPProcessor()
        self.objectives = None
        self.is_running = False
        self.visited_urls = set()
        self.url_queue = []
        self.results = []
        
    def start_crawl(self, config: Dict[str, Any]):
        """Start a crawl with natural language instructions."""
        self.is_running = True
        self.visited_urls = set()
        self.url_queue = []
        self.results = []
        
        # Process natural language instructions
        instructions = config.get('instructions', '')
        if instructions:
            self.objectives = self.nlp_processor.process_instructions(instructions)
        else:
            self.objectives = CrawlObjectives()
        
        # Emit progress
        self.progress_updated.emit({
            "status": "started",
            "message": "Processing crawl instructions...",
            "objectives": self.objectives.__dict__ if self.objectives else {}
        })
        
        # Start crawling (would integrate with actual scraper)
        # For now, emit that it's ready
        self.progress_updated.emit({
            "status": "initialized",
            "message": f"Crawl initialized. Primary subject: {self.objectives.primary_subject if self.objectives else 'None'}",
            "config": config
        })
    
    def stop_crawl(self):
        """Stop the crawl."""
        self.is_running = False
        self.progress_updated.emit({
            "status": "stopped",
            "message": "Crawl stopped by user"
        })
    
    def prioritize_urls(self, urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize URLs based on relevance."""
        if not self.objectives:
            return urls
        
        scored_urls = []
        for url_info in urls:
            score = self.nlp_processor.score_page_relevance(url_info, self.objectives)
            url_info['relevance_score'] = score
            scored_urls.append(url_info)
        
        # Sort by relevance score descending
        scored_urls.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return scored_urls
