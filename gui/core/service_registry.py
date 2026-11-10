"""
Service Registry
Manages backend services and their adapters for GUI integration.
"""

from typing import Dict, Any, Type

class ServiceRegistry:
    """Central registry for backend services used by GUI components."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        self._services[name] = service
    
    def register_factory(self, name: str, factory: callable) -> None:
        """Register a service factory that creates instances on demand."""
        self._factories[name] = factory
    
    def get(self, name: str, force_create: bool = False) -> Any:
        """Get a service by name. Can force creation via factory if available."""
        if name in self._services:
            return self._services[name]
        
        if force_create and name in self._factories:
            instance = self._factories[name]()
            self._services[name] = instance
            return instance
        
        return None
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._factories
    
    def register_backend_adapters(self):
        """Register all backend service adapters."""
        from gui.core.backend_adapter import BackendServiceAdapter
        
        # Create and register the main backend adapter
        adapter = BackendServiceAdapter(self)
        self.register("backend", adapter)
        
        # Register individual service adapters for convenience
        self.register_factory("research_service", adapter.get_research_service)
        self.register_factory("search_service", adapter.get_search_service)
        self.register_factory("crawl_service", adapter.get_crawl_service)
        self.register_factory("extraction_service", adapter.get_extraction_service)
        self.register_factory("document_service", adapter.get_document_service)
        self.register_factory("entity_service", adapter.get_entity_service)
        self.register_factory("storage_service", adapter.get_storage_service)
        self.register_factory("report_service", adapter.get_report_service)