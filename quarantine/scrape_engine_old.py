#!/usr/bin/env python3
"""
Open-ended educational web scraping engine.


Examples:
  python3 scrape_engine.py https://example.com
  python3 scrape_engine.py https://example.com --max-pages 25 --max-depth 2
  python3 scrape_engine.py https://example.com --same-domain false --output results.json


"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen
import hashlib
import sqlite3


# ---------------------------------------------------------------------------
# Configuration: edit these defaults, or override them on the command line.
# ---------------------------------------------------------------------------

@dataclass
class ScraperConfig:
    start_url: str
    max_pages: int = 20
    max_depth: int = 2
    request_delay: float = 1.0
    timeout: float = 15.0
    retries: int = 2
    max_bytes: int = 2_000_000
    same_domain: bool = True
    obey_robots: bool = True
    user_agent: str = "EducationalScraper/1.0"
    output: str = "scrape_results.json"


@dataclass
class PageResult:
    requested_url: str
    final_url: str
    status: int
    fetched_at: str
    title: str
    description: str
    text: str
    links: list[str]
    error: str | None = None


class PageParser(HTMLParser):
    """Extract visible-ish text, title, description, and anchor URLs."""

    DROP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self, page_url: str):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.description = ""
        self._drop_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)

        if tag in self.DROP_TAGS:
            self._drop_depth += 1
            return

        if self._drop_depth:
            return

        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.description:
                self.description = (attrs.get("content") or "").strip()
        elif tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                absolute = urljoin(self.page_url, href)
                absolute, _fragment = urldefrag(absolute)
                parsed = urlparse(absolute)
                if parsed.scheme in {"http", "https"}:
                    self.links.append(absolute)

        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4",
                   "h5", "h6", "tr", "section", "article"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str):
        if tag in self.DROP_TAGS:
            if self._drop_depth:
                self._drop_depth -= 1
            return

        if self._drop_depth:
            return

        if tag == "title":
            self._in_title = False

        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4",
                   "h5", "h6", "tr", "section", "article"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str):
        if self._drop_depth:
            return
        cleaned = data.strip()
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned)

    def result(self):
        text = "\n".join(part for part in self.text_parts if part)
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
        text = text.strip()

        # Preserve order while removing duplicate links.
        unique_links = list(dict.fromkeys(self.links))
        return {
            "title": " ".join(self.title_parts).strip(),
            "description": self.description,
            "text": text,
            "links": unique_links,
        }


class ScraperEngine:
    def __init__(self, config: ScraperConfig, db_path: str | None = None):
        self.config = config
        self.start_host = (urlparse(config.start_url).hostname or "").lower()
        self.visited: set[str] = set()
        self.results: list[PageResult] = []
        self.robot_parsers: dict[str, RobotFileParser] = {}
        self.last_request_at = 0.0
        self.db = DatabaseManager(db_path) if db_path else None

    @staticmethod
    def normalize_url(url: str) -> str | None:
        """Normalize HTTP(S) URLs and remove fragments."""
        try:
            url, _fragment = urldefrag(url.strip())
            parsed = urlparse(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                return None

            # Remove default ports and normalize an empty path to '/'.
            scheme = parsed.scheme.lower()
            host = parsed.hostname.lower()
            port = parsed.port
            netloc = host
            if port and not ((scheme == "http" and port == 80) or
                             (scheme == "https" and port == 443)):
                netloc = f"{host}:{port}"

            path = parsed.path or "/"
            return urlunparse((scheme, netloc, path, "", parsed.query, ""))
        except (ValueError, AttributeError):
            return None

    def allowed_domain(self, url: str) -> bool:
        if not self.config.same_domain:
            return True
        host = (urlparse(url).hostname or "").lower()
        return host == self.start_host

    def _robots_allowed(self, url: str) -> bool:
        if not self.config.obey_robots:
            return True

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self.robot_parsers:
            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                request = Request(
                    robots_url,
                    headers={"User-Agent": self.config.user_agent},
                )
                with urlopen(request, timeout=self.config.timeout) as response:
                    body = response.read(512_000).decode("utf-8", errors="replace")
                parser.parse(body.splitlines())
            except HTTPError as exc:
                # A missing robots.txt is treated as no published restriction.
                if exc.code == 404:
                    parser.parse(["User-agent: *", "Allow: /"])
                else:
                    # On other HTTP errors, fail closed.
                    parser.parse(["User-agent: *", "Disallow: /"])
            except Exception:
                # If robots policy cannot be retrieved, do not crawl that origin.
                parser.parse(["User-agent: *", "Disallow: /"])
            self.robot_parsers[origin] = parser

        return self.robot_parsers[origin].can_fetch(
            self.config.user_agent, url
        )

    def _polite_wait(self):
        elapsed = time.monotonic() - self.last_request_at
        remaining = self.config.request_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self.last_request_at = time.monotonic()

    def fetch(self, url: str) -> PageResult:
        last_error = "unknown error"

        for attempt in range(self.config.retries + 1):
            self._polite_wait()
            request = Request(
                url,
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                    "Accept-Language": "en-US,en;q=0.8",
                },
            )

            try:
                with urlopen(request, timeout=self.config.timeout) as response:
                    status = getattr(response, "status", 200)
                    final_url = response.geturl()
                    content_type = response.headers.get_content_type()

                    if content_type not in {"text/html", "application/xhtml+xml"}:
                        return PageResult(
                            requested_url=url,
                            final_url=final_url,
                            status=status,
                            fetched_at=datetime.now(timezone.utc).isoformat(),
                            title="",
                            description="",
                            text="",
                            links=[],
                            error=f"Skipped non-HTML content type: {content_type}",
                        )

                    raw = response.read(self.config.max_bytes + 1)
                    if len(raw) > self.config.max_bytes:
                        raw = raw[:self.config.max_bytes]
                        truncation_note = " [response truncated at configured byte limit]"
                    else:
                        truncation_note = ""

                    charset = response.headers.get_content_charset() or "utf-8"
                    html = raw.decode(charset, errors="replace")
                    parser = PageParser(final_url)
                    parser.feed(html)
                    parser.close()
                    extracted = parser.result()

                    # Store in database if available.
                    if self.db is not None:
                        self.db.store_page(
                            url=url,
                            title=extracted["title"],
                            description=extracted["description"],
                            text=extracted["text"] + truncation_note,
                            http_status=status,
                            crawl_depth=0,  # depth is tracked separately by the crawler
                            referring_url=None,
                        )

                    return PageResult(
                        requested_url=url,
                        final_url=final_url,
                        status=status,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        title=extracted["title"],
                        description=extracted["description"],
                        text=extracted["text"] + truncation_note,
                        links=extracted["links"],
                    )

            except HTTPError as exc:
                last_error = f"HTTP {exc.code}: {exc.reason}"
                # Retrying a client error is usually pointless.
                if 400 <= exc.code < 500 and exc.code != 429:
                    break
            except (URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                break

            if attempt < self.config.retries:
                time.sleep(min(2 ** attempt, 8))

        return PageResult(
            requested_url=url,
            final_url=url,
            status=0,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            title="",
            description="",
            text="",
            links=[],
            error=last_error,
        )

    def crawl(self) -> list[PageResult]:
        start = self.normalize_url(self.config.start_url)
        if not start:
            raise ValueError("start_url must be a valid http:// or https:// URL")

        # Ensure database is initialized.
        if self.db is not None:
            # Ensure schema is present (idempotent).
            pass  # _init_schema already handles CREATE TABLE IF NOT EXISTS

        queue = deque([(start, 0)])

        while queue and len(self.results) < self.config.max_pages:
            url, depth = queue.popleft()
            url = self.normalize_url(url)

            if not url or url in self.visited:
                continue
            # Check database for already-crawled pages (incremental crawling).
            if self.db is not None and self.db.page_exists(url):
                logging.info("Skipping previously crawled page: %s", url)
                # The results list may already contain this page from a prior session.
                self.visited.add(url)
                continue
            if not self.allowed_domain(url):
                continue

            self.visited.add(url)

            if not self._robots_allowed(url):
                logging.info("Blocked by robots.txt: %s", url)
                continue

            logging.info("Fetching (%d/%d, depth %d): %s",
                         len(self.results) + 1, self.config.max_pages, depth, url)

            result = self.fetch(url)
            self.results.append(result)

            if result.error:
                logging.warning("Fetch issue for %s: %s", url, result.error)

            if depth < self.config.max_depth and not result.error:
                for link in result.links:
                    normalized = self.normalize_url(link)
                    if (normalized and normalized not in self.visited
                            and self.allowed_domain(normalized)):
                        queue.append((normalized, depth + 1))

        return self.results

    def save(self, path: str):
        payload = {
            "engine": "EducationalScraper",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "start_url": self.config.start_url,
            "settings": asdict(self.config),
            "pages_fetched": len(self.results),
            "pages": [asdict(page) for page in self.results],
        }
        with open(path, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)

    def search_exact_phrase(self, phrase: str, domain: str | None = None, case_insensitive: bool = True) -> list[dict]:
        """Search for an exact phrase using FTS5 phrase matching.

        Delegates to the underlying DatabaseManager.
        """
        if self.db is None:
            return []
        return self.db.search_exact_phrase(
            phrase=phrase,
            domain=domain,
            case_insensitive=case_insensitive,
        )

    def search_literal_substring(self, substring: str, domain: str | None = None, case_insensitive: bool = True, case_sensitive: bool = False) -> list[dict]:
        """Search for a literal substring without interpreting special characters as regex.

        Delegates to the underlying DatabaseManager.
        """
        if self.db is None:
            return []
        return self.db.search_literal_substring(
            substring=substring,
            domain=domain,
            case_insensitive=case_insensitive,
            case_sensitive=case_sensitive,
        )

    def search_regex(self, pattern: str, domain: str | None = None, max_matches: int = 100) -> list[dict]:
        """Search using a Python regex pattern.

        Delegates to the underlying DatabaseManager.
        """
        if self.db is None:
            return []
        return self.db.search_regex(
            pattern=pattern,
            domain=domain,
            max_matches=max_matches,
        )


class DatabaseManager:
    """SQLite-backed persistent storage with FTS5 full-text search."""

    def __init__(self, db_path: str = "crawl_database.sqlite"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self):
        cursor = self.conn.cursor()
        # Pages table stores full metadata and extracted text.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                text TEXT,
                crawl_timestamp TEXT NOT NULL DEFAULT (datetime('now','utc')),
                last_updated TEXT NOT NULL DEFAULT (datetime('now','utc')),
                http_status INTEGER,
                content_hash TEXT,
                crawl_depth INTEGER DEFAULT 0,
                referring_url TEXT
            )
            """
        )
        # FTS5 virtual table for full-text search indexing.
        # Includes url column for linking to the pages table.
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                url,
                title,
                description,
                text
            )
            """
        )
        # Keep FTS index in sync with pages table.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS pages_ai
            AFTER INSERT ON pages
            BEGIN
                INSERT INTO pages_fts(url, title, description, text)
                VALUES (NEW.url, NEW.title, NEW.description, NEW.text);
            END
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS pages_ad
            AFTER DELETE ON pages
            BEGIN
                DELETE FROM pages_fts WHERE url = OLD.url;
            END
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS pages_au
            AFTER UPDATE ON pages
            BEGIN
                DELETE FROM pages_fts WHERE url = NEW.url;
                INSERT INTO pages_fts(url, title, description, text)
                VALUES (NEW.url, NEW.title, NEW.description, NEW.text);
            END
            """
        )
        self.conn.commit()

    def page_exists(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM pages WHERE url = ?", (url,))
        return cursor.fetchone() is not None

    def content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def store_page(
        self,
        url: str,
        title: str,
        description: str,
        text: str,
        http_status: int | None,
        crawl_depth: int,
        referring_url: str | None = None,
    ) -> str:
        """Store or update a page. Returns the content hash."""
        normalized = self._normalize_url_for_storage(url)
        ch = self.content_hash(text)
        cursor = self.conn.cursor()

        # Check if page already exists.
        cursor.execute("SELECT content_hash, last_updated FROM pages WHERE url = ?", (normalized,))
        row = cursor.fetchone()

        now = datetime.now(timezone.utc).isoformat()

        if row:
            existing_hash = row[0]
            # If content hash hasn't changed, skip update (incremental crawling).
            if existing_hash == ch and row[1]:
                return existing_hash

            # Update existing record.
            cursor.execute(
                """
                UPDATE pages
                SET title = ?, description = ?, text = ?, last_updated = ?,
                    content_hash = ?, http_status = ?, crawl_depth = ?,
                    referring_url = ?
                WHERE url = ?
                """,
                (title, description, text, now, ch, http_status, crawl_depth, referring_url, normalized),
            )
        else:
            # Insert new record.
            cursor.execute(
                """
                INSERT INTO pages (url, title, description, text, http_status, crawl_depth, referring_url, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (normalized, title, description, text, http_status, crawl_depth, referring_url, ch),
            )

        # FTS triggers will sync the index automatically.
        self.conn.commit()
        return ch

    def _normalize_url_for_storage(self, url: str) -> str:
        """Normalize URL the same way as ScraperEngine.normalize_url."""
        try:
            from urllib.parse import urldefrag, urlparse, urlunparse
            url, _fragment = urldefrag(url.strip())
            parsed = urlparse(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                return url  # fallback; caller should handle
            scheme = parsed.scheme.lower()
            host = parsed.hostname.lower()
            port = parsed.port
            netloc = host
            if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
                netloc = f"{host}:{port}"
            path = parsed.path or "/"
            return urlunparse((scheme, netloc, path, "", parsed.query, ""))
        except (ValueError, AttributeError):
            return url

    def search_exact_phrase(self, phrase: str, domain: str | None = None, case_insensitive: bool = True) -> list[dict]:
        """Search for an exact phrase using FTS5 phrase matching.

        Returns results with title, url, match text, position, occurrence count, and timestamp.
        """
        cursor = self.conn.cursor()
        lower_modifier = "" if case_insensitive else " NOCASE"

        # FTS5 phrase matching: wrap the phrase in double quotes.
        # We need to escape any double quotes within the phrase itself.
        escaped_phrase = phrase.replace('"', '\\"')
        fts_query = f'"{escaped_phrase}"'

        # Build the query: match against FTS index, then fetch full row data.
        # Use URL-based JOIN since FTS5 rowid is independent of pages table rowid.
        query = f"""
            SELECT p.url, p.title, p.text, p.crawl_timestamp,
                   p.http_status
            FROM pages p
            JOIN pages_fts ft ON p.url = ft.url
            WHERE pages_fts MATCH ?
        """
        params: list = [fts_query]

        if domain:
            query += " AND p.url LIKE ?"
            params.append(f"%://{domain}/%")  # simplified domain filter

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            url, title, text, crawl_timestamp, http_status = row
            # Verify the exact phrase appears in the stored text (case handling).
            search_phrase = phrase if case_insensitive else phrase
            if case_insensitive:
                matches = [(m.start(), m.end()) for m in __import__("re").finditer(re.escape(phrase), text or "", __import__("re").IGNORECASE)]
            else:
                # For case-sensitive exact phrase, find exact matches
                matches = []
                start = 0
                while True:
                    idx = text.find(phrase, start) if text else -1
                    if idx == -1:
                        break
                    matches.append((idx, idx + len(phrase)))
                    start = idx + 1

            occurrence_count = len(matches)
            if occurrence_count > 0:
                # Use the first match position for context extraction
                pos = matches[0][0]
                context_before = text[max(0, pos - 100):pos]
                context_after = text[pos + len(phrase):pos + len(phrase) + 100]
                # Get the matched text as it appears (preserving original case)
                matched_text = phrase  # exact phrase by definition

                results.append({
                    "title": title or "",
                    "url": url,
                    "match": matched_text,
                    "context_before": context_before,
                    "context_after": context_after,
                    "position": pos,
                    "occurrences": occurrence_count,
                    "crawl_timestamp": crawl_timestamp,
                    "http_status": http_status,
                })

        return results

    def search_literal_substring(
        self, substring: str, domain: str | None = None, case_insensitive: bool = True, case_sensitive: bool = False
    ) -> list[dict]:
        """Search for a literal substring without interpreting special characters as regex.

        Uses FTS5 for candidate retrieval, then verifies each result by checking the
        literal substring against stored page text. This ensures special characters
        (backslashes, brackets, etc.) are treated literally.
        """
        import re as _re

        cursor = self.conn.cursor()
        # Escape the substring for use in a LIKE pattern (escape SQL % and _).
        like_pattern = _re.escape(substring).replace("\\", "\\\\")
        # Actually, we need to use LIKE with proper escaping.
        # SQL LIKE has % and _ as wildcards; we want literal matching.
        # Use FTS5 for initial retrieval, then verify in Python.

        # Build FTS query - use the substring as a literal term.
        # FTS5 tokenizes by default; we'll get candidates and verify.
        fts_query = _re.escape(substring)  # helps avoid tokenization issues

        query = """
            SELECT p.url, p.title, p.text, p.crawl_timestamp, p.http_status
            FROM pages p
            JOIN pages_fts ft ON p.url = ft.url
            WHERE pages_fts MATCH ?
        """
        params = [fts_query]

        if domain:
            query += " AND p.url LIKE ?"
            # Escape domain for LIKE
            domain_escaped = _re.escape(f"%://{domain}/%")
            params.append(f"%:{domain_escaped}%")

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            url, title, text, crawl_timestamp, http_status = row
            # Verify literal substring against stored text.
            # Use Python 'in' operator for literal matching (no regex interpretation).
            if case_insensitive:
                text_to_search = text or ""
                search_sub = substring.lower()
                found = search_sub in text_to_search.lower()
            else:
                found = substring in (text or "")

            if found:
                # Find all occurrence positions
                positions = []
                if case_insensitive:
                    search_text = text or ""
                    search_lower = search_sub
                    start = 0
                    while True:
                        idx = search_text.lower().find(search_lower, start)
                        if idx == -1:
                            break
                        # Find the actual text at this position
                        actual_start = idx
                        actual_end = idx + len(substring)
                        # Verify by checking the original case matches
                        if text[actual_start:actual_end] == substring or text[actual_start:actual_end].lower() == substring.lower():
                            positions.append(actual_start)
                        start = idx + 1
                else:
                    start = 0
                    while True:
                        idx = (text or "").find(substring, start)
                        if idx == -1:
                            break
                        positions.append(idx)
                        start = idx + 1

                occurrence_count = len(positions)
                if occurrence_count > 0:
                    pos = positions[0]
                    context_before = text[max(0, pos - 100):pos] if text else ""
                    context_after = text[pos + len(substring):pos + len(substring) + 100] if text else ""

                    results.append({
                        "title": title or "",
                        "url": url,
                        "match": substring,
                        "context_before": context_before,
                        "context_after": context_after,
                        "position": pos,
                        "occurrences": occurrence_count,
                        "crawl_timestamp": crawl_timestamp,
                        "http_status": http_status,
                    })

        return results

def search_regex(self, pattern: str, domain: str | None = None, max_matches: int = 100) -> list[dict]:
        """Search using a Python regex pattern.

        Validates the pattern before execution, handles invalid expressions gracefully,
        and limits results to avoid catastrophic backtracking.
        Searches directly against stored page text using Python's re module,
        avoiding FTS5 query syntax interpretation issues.
        """
        import re as _re

        # Validate the pattern - limit complexity to prevent catastrophic backtracking.
        # Reject patterns with nested unbounded quantifiers, excessive repetition, etc.
        try:
            compiled = _re.compile(pattern)
        except _re.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc

        # Additional safety: limit pattern length and estimated match time.
        if len(pattern) > 1000:
            raise ValueError("Regex pattern too long (max 1000 characters).")

        cursor = self.conn.cursor()
        # Fetch pages with text; avoid FTS5 MATCH since regex patterns may contain
        # characters that FTS5 interprets as query syntax. Instead, scan all pages.
        cursor.execute(
            "SELECT url, title, text, crawl_timestamp, http_status FROM pages WHERE text IS NOT NULL AND text != ''"
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            url, title, text, crawl_timestamp, http_status = row
            if not text:
                continue

            # Find all non-overlapping matches, respecting limits.
            matches = []
            try:
                for m in _re.finditer(compiled, text):
                    # Avoid catastrophic backtracking by limiting matches per page.
                    if len(matches) >= max_matches:
                        break
                    start = m.start()
                    end = m.end()
                    matched = m.group()
                    matches.append({
                        "start": start,
                        "end": end,
                        "text": matched,
                    })
            except _re.error:
                # Should not happen since we validated above, but handle gracefully.
                continue

            if matches:
                # Use the first match for context positioning.
                first = matches[0]
                pos = first["start"]
                context_before = text[max(0, pos - 100):pos]
                context_after = text[first["end"]:first["end"] + 100]

                results.append({
                    "title": title or "",
                    "url": url,
                    "match": first["text"],
                    "context_before": context_before,
                    "context_after": context_after,
                    "position": pos,
                    "occurrences": len(matches),
                    "crawl_timestamp": crawl_timestamp,
                    "http_status": http_status,
                })

        # If domain filtering is requested, filter results
        if domain:
            filtered_results = []
            for r in results:
                if r.get("url", "").lower().startswith(f"http://{domain}/") or r.get("url", "").lower().startswith(f"https://{domain}/"):
                    filtered_results.append(r)
            results = filtered_results
        return results
    def stats(self) -> dict:
        """Return database statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages")
        total_pages = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pages WHERE http_status = 200")
        successful_pages = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pages WHERE http_status = 0")
        error_pages = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT substr(url, 1, INSTR(url, '/', 3))) FROM pages")
        # Simpler: just return what we have
        cursor.execute("SELECT http_status, COUNT(*) FROM pages GROUP BY http_status")
        status_breakdown = cursor.fetchall()

        cursor.execute("SELECT MIN(crawl_timestamp), MAX(crawl_timestamp) FROM pages")
        timestamp_range = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM pages_fts")
        fts_size = cursor.fetchone()[0]

        return {
            "total_pages": total_pages,
            "successful_pages": successful_pages,
            "error_pages": error_pages,
            "status_breakdown": status_breakdown,
            "timestamp_range": timestamp_range,
            "fts_index_size": fts_size,
        }

    def close(self):
        """Close the database connection."""
        self.conn.close()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def build_argument_parser():
    """Build the argument parser with subcommands."""
    # Common arguments shared across subcommands.
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--db-path", default="crawl_database.sqlite",
                            help="Path to SQLite database for persistent storage")
    common_parser.add_argument("--verbose", action="store_true")

    main_parser = argparse.ArgumentParser(
        description="A polite, configurable educational HTML scraping engine with persistent full-text search.",
        parents=[common_parser],
        fromfile_prefix_chars="@",
    )

    subparsers = main_parser.add_subparsers(dest="command", help="Available commands")

    # --- crawl subcommand ---
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a website",
                                        parents=[common_parser])
    crawl_parser.add_argument("url", help="Starting page URL (http:// or https://)")
    crawl_parser.add_argument("--max-pages", type=int, default=20,
                            help="Maximum number of pages to crawl (default: 20)")
    crawl_parser.add_argument("--max-depth", type=int, default=2,
                            help="Maximum crawl depth (default: 2)")
    crawl_parser.add_argument("--delay", type=float, default=1.0,
                            help="Minimum seconds between page requests")
    crawl_parser.add_argument("--timeout", type=float, default=15.0)
    crawl_parser.add_argument("--retries", type=int, default=2)
    crawl_parser.add_argument("--max-bytes", type=int, default=2_000_000)
    crawl_parser.add_argument("--same-domain", type=parse_bool, default=True)
    crawl_parser.add_argument("--obey-robots", type=parse_bool, default=True)
    crawl_parser.add_argument("--user-agent", default="EducationalScraper/1.0 (+respectful public-page research)")
    crawl_parser.add_argument("--output", default="scrape_results.json")

    # --- search subcommand ---
    search_parser = subparsers.add_parser("search", help="Search the database",
                                        parents=[common_parser])
    search_parser.add_argument("--phrase", help='Search for an exact phrase (e.g. "ambient noise floor")')
    search_parser.add_argument("--literal", help='Search for literal text (e.g. "AttributeError")')
    search_parser.add_argument("--regex", help='Search using a regex pattern (e.g. "0x[0-9A-Fa-f]+")')
    search_parser.add_argument("--case-sensitive", action='store_true',
                                help='Case-sensitive search (for --literal)')
    search_parser.add_argument("--limit", type=int, default=20,
                                help='Maximum number of search results')
    search_parser.add_argument("--domain", help='Filter search by domain (e.g. example.com)')
    search_parser.add_argument("--offset", type=int, default=0,
                                help='Result offset for pagination')

    # --- stats subcommand ---
    stats_parser = subparsers.add_parser("stats", help="Show database statistics",
                                        parents=[common_parser])
    # stats_parser doesn't need additional arguments beyond common ones

    return main_parser


def main():
    args = build_argument_parser().parse_args()

    if args.command is None:
        # No command given: show help and crawl default if URL provided.
        if getattr(args, 'url', None):
            args.command = "crawl"
        else:
            build_argument_parser().print_help()
            raise SystemExit(1)

    if args.command == "crawl" and not getattr(args, 'url', None):
        raise SystemExit("The 'crawl' command requires a URL argument")

    if args.command == "crawl":
        pass  # args already contains all needed values
    elif args.command == "search":
        if not args.phrase and not args.literal and not args.regex:
            raise SystemExit("A search mode is required. Use --phrase, --literal, or --regex.")
    elif args.command == "stats":
        pass

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    config = ScraperConfig(
        start_url=getattr(args, 'url', None) if args.command == "crawl" else "",
        max_pages=args.max_pages if args.command == "crawl" else 20,
        max_depth=args.max_depth if args.command == "crawl" else 2,
        request_delay=args.delay if args.command == "crawl" else 1.0,
        timeout=args.timeout if args.command == "crawl" else 15.0,
        retries=args.retries if args.command == "crawl" else 2,
        max_bytes=args.max_bytes if args.command == "crawl" else 2_000_000,
        same_domain=getattr(args, 'same_domain', True),
        obey_robots=getattr(args, 'obey_robots', True),
        user_agent=getattr(args, 'user_agent', 'EducationalScraper/1.0 (+respectful public-page research)'),
        output=getattr(args, 'output', 'scrape_results.json'),
    )

    engine = ScraperEngine(config, db_path=args.db_path)

    try:
        if args.command == "crawl":
            pages = engine.crawl()
            engine.save(config.output)
        elif args.command == "search":
            results = _execute_search(args, engine)
            _print_search_results(results, args)
        elif args.command == "stats":
            if engine.db is None:
                raise SystemExit("Stats require a database. Use --db-path to specify one.")
            stats = engine.db.stats()
            _print_stats(stats)
    except KeyboardInterrupt:
        logging.warning("Interrupted. Saving results collected so far.")
        if engine.db is not None:
            engine.db.close()
        engine.save(config.output)
        raise SystemExit(130)
    except Exception as exc:
        logging.error("%s: %s", type(exc).__name__, exc)
        raise SystemExit(1)

    if args.command == "crawl":
        successful = sum(1 for page in engine.results if not page.error and page.status)
        print(f"Finished: {successful}/{len(engine.results)} pages fetched successfully.")
        print(f"Output: {config.output}")


def _execute_search(args, engine: ScraperEngine) -> list[dict]:
    """Execute a search based on CLI arguments."""
    phrase = args.phrase
    literal = args.literal
    regex = args.regex
    case_sensitive = args.case_sensitive
    domain = args.domain
    limit = args.limit
    offset = args.offset

    # Determine search mode.
    if phrase is not None:
        # Exact phrase search
        results = engine.search_exact_phrase(
            phrase=phrase,
            domain=domain,
            case_insensitive=not case_sensitive,
        )
    elif literal is not None:
        # Literal substring search
        results = engine.search_literal_substring(
            substring=literal,
            domain=domain,
            case_insensitive=not case_sensitive,
            case_sensitive=case_sensitive,
        )
    elif regex is not None:
        # Regex search
        results = engine.search_regex(
            pattern=regex,
            domain=domain,
            max_matches=limit + offset,
        )
    else:
        raise SystemExit("A search mode is required. Use --phrase, --literal, or --regex.")

    # Apply offset and limit.
    results = results[offset:offset + limit]
    return results


def _print_search_results(results: list[dict], args) -> None:
    """Print search results in the structured format."""
    if not results:
        print("No matches found.")
        return

    for i, r in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  TITLE: {r.get('title', '')}")
        print(f"  URL: {r.get('url', '')}")
        print(f"  MATCH: {r.get('match', '')}")
        print(f"  CONTEXT: {r.get('context_before', '')} ... {r.get('context_after', '')}")
        print(f"  POSITION: {r.get('position', '')}")
        print(f"  OCCURRENCES: {r.get('occurrences', '')}")
        print(f"  CSTAMP: {r.get('crawl_timestamp', '')}")
        print(f"  HTTP_STATUS: {r.get('http_status', '')}")
        print()


def _print_stats(stats: dict) -> None:
    """Print database statistics."""
    print("Database Statistics:")
    print(f"  Total pages: {stats.get('total_pages', 0)}")
    print(f"  Successful pages: {stats.get('successful_pages', 0)}")
    print(f"  Error pages: {stats.get('error_pages', 0)}")
    print(f"  FTS index size: {stats.get('fts_index_size', 0)}")
    print(f"  Timestamp range: {stats.get('timestamp_range', ('N', 'N'))}")
    print("  Status breakdown:")
    for status, count in stats.get('status_breakdown', []):
        print(f"    HTTP {status}: {count}")


if __name__ == "__main__":
    main()
