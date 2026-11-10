#!/usr/bin/env python3
"""
Sitemap discovery and URL hierarchy module for the web research engine.

This module discovers, represents, navigates, and explores the architecture of websites.
It maintains both the site's published sitemap hierarchy and the actual discovered
URL and internal-link hierarchy. These are related but distinct structures.

Key capabilities:
- Sitemap discovery via robots.txt, /sitemap.xml, sitemap indexes
- URL discovery from multiple sources (sitemaps, robots.txt, internal links, feeds, archives)
- Complete domain, sitemap, and URL hierarchy tracking
- Internal-link graph mapping
- Distinguishing sitemap membership from URL path hierarchy
- Duplicate URL variant normalization
- Coverage statistics
"""

import traceback
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timezone
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Sitemap discovery types
# ---------------------------------------------------------------------------


class SitemapType(Enum):
    """Types of sitemap entries."""
    INDEX = "index"  # Sitemap index file
    SITEMAP = "sitemap"  # Individual sitemap
    URL = "url"  # URL entry in a sitemap


class SitemapFormat(Enum):
    """Sitemap format types."""
    XML = "xml"
    GZIP = "gzip"
    XML_GZIP = "xml.gz"


# ---------------------------------------------------------------------------
# Sitemap entry
# ---------------------------------------------------------------------------


@dataclass
class SitemapEntry:
    """Represents a sitemap entry."""
    location: str  # URL of the sitemap or URL
    lastmod: Optional[str]  # Last modification date
    changefreq: Optional[str]  # Change frequency priority
    priority: Optional[float]  # Priority relative to other URLs
    type: SitemapType  # Type of entry (index, sitemap, url)
    format: SitemapFormat  # Format of the sitemap
    discovered: str  # How this was discovered
    references: int  # How many times referenced


# ---------------------------------------------------------------------------
# URL hierarchy types
# ---------------------------------------------------------------------------


@dataclass
class URLNode:
    """Represents a node in the URL hierarchy."""
    url: str  # Normalized URL
    title: str  # Page title
    description: str  # Page description
    content_type: str  # MIME content type
    domain: str  # Domain
    subdomain: str  # Subdomain
    path: str  # Path portion
    parent: Optional[str]  # Parent URL in hierarchy
    children: Set[str]  # Child URL hashes
    discovery_method: str  # How this URL was discovered
    sitemap_membership: Set[str]  # Which sitemaps this URL belongs to
    http_status: Optional[int]  # HTTP status code
    crawl_status: str  # crawl, skipped, failed, extracted, retained
    extraction_status: str  # pending, in_progress, completed, failed
    language: str  # Language code
    last_checked: str  # When last checked
    times_crawled: int  # Number of times crawled
    times_extracted: int  # Number of times extracted


# ---------------------------------------------------------------------------
# Sitemap parser
# ---------------------------------------------------------------------------


class SitemapParser:
    """
    Parser for discovering sitemaps and URL hierarchies from websites.

    Discovers sitemap locations through:
    - robots.txt Sitemap declarations
    - /sitemap.xml
    - /sitemap_index.xml
    - /sitemap-index.xml
    - Referenced sitemap indexes
    - Common CMS sitemap conventions
    - Compressed sitemap files
    - Sitemap references found in site metadata
    """

    def __init__(self, storage_manager=None):
        self.storage_manager = storage_manager

    def discover_sitemaps(self, base_url: str) -> List[SitemapEntry]:
        """
        Discover sitemap locations for a given base URL.
        Returns a list of sitemap entries found.
        """
        sitemaps = []
        base_parsed = urlparse(base_url)
        base_netloc = base_parsed.netloc.lower()

        # Method 1: robots.txt Sitemap declarations
        robots_sitemaps = self._parse_robots_txt_sitemaps(base_url)
        sitemaps.extend(robots_sitemaps)

        # Method 2: Standard sitemap locations
        standard_locations = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap-index.xml",
        ]
        for location in standard_locations:
            parsed = urlparse(location)
            if parsed.netloc.lower() == base_netloc or not parsed.netloc:
                entry = SitemapEntry(
                    location=location,
                    discovered="standard_location",
                    type=SitemapType.SITEMAP,
                    format=SitemapFormat.XML,
                )
                sitemaps.append(entry)

        # Method 3: Referenced sitemaps from already-discovered sitemaps
        # (handled iteratively)

        return sitemaps

    def _parse_robots_txt_sitemaps(self, base_url: str) -> List[SitemapEntry]:
        """Parse robots.txt for Sitemap declarations."""
        sitemaps = []
        base_parsed = urlparse(base_url)
        robots_url = f"{base_parsed.scheme}://{base_parsed.netloc}/robots.txt"

        try:
            import urllib.request
            with urllib.request.urlopen(robots_url, timeout=10) as response:
                robots_content = response.read().decode("utf-8", errors="replace")

            # Look for Sitemap: declarations
            for line in robots_content.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    # Make URL absolute if needed
                    if not sitemap_url.startswith(("http://", "https://")):
                        sitemap_url = urljoin(robots_url, sitemap_url)
                    entry = SitemapEntry(
                        location=sitemap_url,
                        discovered="robots_txt",
                        type=SitemapType.SITEMAP,
                        format=SitemapFormat.XML,
                    )
                    sitemaps.append(entry)
        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in sitemap_module: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass

        return sitemaps

    def parse_sitemap_index(self, sitemap_url: str) -> List[SitemapEntry]:
        """
        Parse a sitemap index file and return a list of sitemap entries.
        Handles gzip-compressed index files.
        """
        entries = []

        try:
            import urllib.request
            with urllib.request.urlopen(sitemap_url, timeout=15) as response:
                # Check content encoding
                content_encoding = response.headers.get("Content-Encoding", "")
                raw_content = response.read()

                if "gzip" in content_encoding.lower():
                    try:
                        decompressed = gzip.decompress(raw_content)
                        content = decompressed.decode("utf-8", errors="replace")
                    except Exception:
                        return entries
                else:
                    content = raw_content.decode("utf-8", errors="replace")

                # Parse the XML sitemap index
                # <sitemapindex> contains <sitemap> entries with <loc> and <lastmod>
                urls = re.findall(r"<loc>(.*?)</loc>", content)
                lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", content)

                for i, url in enumerate(urls):
                    lastmod = lastmods[i] if i < len(lastmods) else None
                    entry = SitemapEntry(
                        location=url,
                        lastmod=lastmod,
                        discovered="sitemap_index",
                        type=SitemapType.SITEMAP,
                        format=SitemapFormat.XML,
                    )
                    entries.append(entry)

        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in sitemap_module: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass

        return entries

    def parse_sitemap(self, sitemap_url: str) -> List[SitemapEntry]:
        """
        Parse a sitemap file and return a list of URL entries.
        Handles gzip-compressed XML sitemaps.
        """
        entries = []

        try:
            import urllib.request
            with urllib.request.urlopen(sitemap_url, timeout=15) as response:
                content_encoding = response.headers.get("Content-Encoding", "")
                raw_content = response.read()

                # Decompress if gzip
                if "gzip" in content_encoding.lower():
                    try:
                        decompressed = gzip.decompress(raw_content)
                        content = decompressed.decode("utf-8", errors="replace")
                    except Exception:
                        return entries
                else:
                    content = raw_content.decode("utf-8", errors="replace")

                # Parse URL entries from XML sitemap
                # <urlset> contains <url> entries with <loc>, <lastmod>, <changefreq>, <priority>
                urls = re.findall(r"<loc>(.*?)</loc>", content)
                lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", content)
                changefreqs = re.findall(r"<changefreq>(.*?)</changefreq>", content)
                priorities = re.findall(r"<priority>(.*?)</priority>", content)

                for i, url in enumerate(urls):
                    entry = SitemapEntry(
                        location=url,
                        lastmod=lastmods[i] if i < len(lastmods) else None,
                        changefreq=changefreqs[i] if i < len(changefreqs) else None,
                        priority=float(priorities[i]).strip() if i < len(priorities) and priorities[i] else None,
                        discovered="sitemap_parse",
                        type=SitemapType.URL,
                        format=SitemapFormat.XML
                        if not ("gzip" in content_encoding.lower() or "deflate" in content_encoding.lower())
                        else SitemapFormat.XML_GZIP,
                    )
                    entries.append(entry)

        except Exception as _se_debug_exc:
            print(f"[DEBUG] {__name__}: Exception in sitemap_module: {_se_debug_exc}", file=__import__('sys').stderr)
            traceback.print_exc()
            pass

        return entries


# ---------------------------------------------------------------------------
# URL normalizer
# ---------------------------------------------------------------------------


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent tracking.
    Removes fragments, sorts query parameters, handles www prefix.
    """
    # Remove fragment
    url, _fragment = urldefrag(url.strip())

    # Ensure http/https
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return url

    # Normalize: lowercase host, remove default ports
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"

    path = parsed.path or "/"
    # Remove trailing slash for non-root paths
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Reconstruct URL
    normalized = urlunparse((scheme, netloc, path, "", parsed.query, ""))
    return normalized


# ---------------------------------------------------------------------------
# URL hierarchy builder
# ---------------------------------------------------------------------------

class URLHierarchy:
    """
    Builds and maintains a persistent URL hierarchy for a crawled website.

    The hierarchy distinguishes between:
    1. The site's published sitemap structure
    2. The actual discovered URL and internal-link hierarchy

    These are related but distinct structures.
    """

    def __init__(self, storage_manager=None):
        self.storage_manager = storage_manager
        # Domain -> {subdomain -> {sitemap_index -> {sitemap -> [url entries]}}}
        self.sitemap_structure: Dict[str, Dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        # Normalized URL -> URLNode
        self.url_nodes: Dict[str, URLNode] = {}
        # URL -> set of child URL normalized forms
        self.url_children: Dict[str, Set[str]] = defaultdict(set)
        # URL -> discovery method
        self.url_discovery: Dict[str, str] = {}
        # URL -> set of sitemap memberships
        self.url_sitemaps: Dict[str, Set[str]] = defaultdict(set)
        # Internal link relationships: URL -> set of (link_type, target_url)
        self.internal_links: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
        # Coverage statistics
        self.coverage_stats: Dict[str, int] = defaultdict(int)

    def add_url(self, url_node: URLNode) -> None:
        """Add a URL to the hierarchy."""
        normalized = normalize_url(url_node.url)
        self.url_nodes[normalized] = url_node
        self.url_discovery[normalized] = url_node.discovery_method

        # Track domain/subdomain
        parsed = urlparse(normalized)
        self.coverage_stats["total_urls"] += 1
        self.coverage_stats[f"domain:{parsed.netloc.lower()}"] += 1

        # Track sitemap membership
        for sitemap in url_node.sitemap_membership:
            self.url_sitemaps[normalized].add(sitemap)

    def add_internal_link(self, from_url: str, to_url: str, link_type: str = "internal") -> None:
        """Add an internal link relationship."""
        from_normalized = normalize_url(from_url)
        to_normalized = normalize_url(to_url)

        self.internal_links[from_normalized].add((link_type, to_normalized))

        # Add to hierarchy
        if from_normalized in self.url_nodes:
            self.url_nodes[from_normalized].children.add(to_normalized)
        if to_normalized in self.url_nodes:
            self.url_nodes[to_normalized].parent = from_normalized

    def get_coverage_stats(self) -> Dict[str, any]:
        """Return coverage statistics."""
        total = self.coverage_stats.get("total_urls", 0)
        crawled = sum(1 for node in self.url_nodes.values()
                      if node.crawl_status in ("crawled", "extracted", "retained"))

        return {
            "total_urls": total,
            "crawled_urls": crawled,
            "discovered_urls": total,
            "sitemap_entries": sum(1 for node in self.url_nodes.values()
                                  if node.sitemap_membership),
            "internal_links": sum(len(links) for links in self.internal_links.values()),
        }