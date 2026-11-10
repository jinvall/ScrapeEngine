#!/usr/bin/env python3
"""
Open-ended educational web scraping engine with persistent full-text search.


Examples:
  python3 scrape_engine.py https://example.com
  python3 scrape_engine.py https://example.com --max-pages 25 --max-depth 2
  python3 scrape_engine.py https://example.com --same-domain false --output results.json


"""

from __future__ import annotations

import traceback
try:
    from crawl_nlp import CrawlNLPProcessor, CrawlObjectives
except Exception as _nlp_import_err:
    print(f"[DEBUG] scrape_engine: NLP import failed: {_nlp_import_err}", file=__import__("sys").stderr)
    traceback.print_exc()
    CrawlNLPProcessor = None
    CrawlObjectives = None

import argparse
import hashlib
import json
import logging
import re
import sqlite3
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


# ---------------------------------------------------------------------------
# Configuration
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
    user_agent: str = "EducationalScraper/1.0 (+respectful public-page research)"
    output: str = "scrape_results.json"
    instructions: str = ""
    objectives: Any = None


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


class DatabaseManager:
    """SQLite-backed persistent storage with FTS5 full-text search."""

    def __init__(self, db_path: str = "crawl_database.sqlite"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self):
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS pages (
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
            )"""
        )
        c.execute(
            """CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                url,
                title,
                description,
                text
            )"""
        )
        c.execute(
            """CREATE TRIGGER IF NOT EXISTS pages_ai
            AFTER INSERT ON pages
            BEGIN
                INSERT INTO pages_fts(url, title, description, text)
                VALUES (NEW.url, NEW.title, NEW.description, NEW.text);
            END"""
        )
        c.execute(
            """CREATE TRIGGER IF NOT EXISTS pages_ad
            AFTER DELETE ON pages
            BEGIN
                DELETE FROM pages_fts WHERE url = OLD.url;
            END"""
        )
        c.execute(
            """CREATE TRIGGER IF NOT EXISTS pages_au
            AFTER UPDATE ON pages
            BEGIN
                DELETE FROM pages_fts WHERE url = NEW.url;
                INSERT INTO pages_fts(url, title, description, text)
                VALUES (NEW.url, NEW.title, NEW.description, NEW.text);
            END"""
        )
        self.conn.commit()

    def page_exists(self, url: str) -> bool:
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM pages WHERE url = ?", (url,))
        return c.fetchone() is not None

    @staticmethod
    def content_hash(text: str) -> str:
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
        norm = self._normalize_url_for_storage(url)
        ch = self.content_hash(text)
        c = self.conn.cursor()
        c.execute("SELECT content_hash FROM pages WHERE url = ?", (norm,))
        row = c.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if row and row[0] == ch:
            return ch
        c.execute(
            """UPDATE pages SET title=?, description=?, text=?, last_updated=?,
               content_hash=?, http_status=?, crawl_depth=?, referring_url=?
               WHERE url=?""",
            (title, description, text, now, ch, http_status, crawl_depth,
             referring_url, norm),
        )
        if not row:
            c.execute(
                """INSERT INTO pages (url, title, description, text, http_status, crawl_depth, referring_url, content_hash)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (norm, title, description, text, http_status, crawl_depth,
                 referring_url, ch),
            )
        self.conn.commit()
        return ch

    def _normalize_url_for_storage(self, url: str) -> str:
        try:
            from urllib.parse import urldefrag, urlparse, urlunparse
            url, _f = urldefrag(url.strip())
            p = urlparse(url)
            if p.scheme.lower() not in {"http", "https"} or not p.hostname:
                return url
            s = p.scheme.lower()
            h = p.hostname.lower()
            po = p.port
            n = h
            if po and not ((s == "http" and po == 80) or (s == "https" and po == 443)):
                n = f"{h}:{po}"
            pt = p.path or "/"
            return urlunparse((s, n, pt, "", p.query, ""))
        except (ValueError, AttributeError):
            return url

    def search_exact_phrase(self, phrase: str, domain: str | None = None,
                           case_insensitive: bool = True) -> list[dict]:
        c = self.conn.cursor()
        esc = phrase.replace('"', '\\"')
        fts_q = f'"{esc}"'
        c.execute(
            """SELECT p.url, p.title, p.text, p.crawl_timestamp, p.http_status
               FROM pages p
               WHERE EXISTS (
                   SELECT 1 FROM pages_fts ft
                   WHERE ft.url = p.url
                   AND pages_fts MATCH ?)""",
            (fts_q,),
        )
        rows = c.fetchall()
        res = []
        for url, title, text, ts, hs in rows:
            if case_insensitive:
                ms = [(m.start(), m.end()) for m in re.finditer(re.escape(phrase), text or "", re.IGNORECASE)]
            else:
                ms = []
                st = 0
                while True:
                    idx = text.find(phrase, st) if text else -1
                    if idx == -1:
                        break
                    ms.append((idx, idx + len(phrase)))
                    st = idx + 1
            oc = len(ms)
            if oc:
                pos = ms[0][0]
                cb = text[max(0, pos - 100):pos] if text else ""
                ca = text[pos + len(phrase):pos + len(phrase) + 100] if text else ""
                res.append({"title": title or "", "url": url, "match": phrase,
                            "context_before": cb, "context_after": ca,
                            "position": pos, "occurrences": oc,
                            "crawl_timestamp": ts, "http_status": hs})
        return res

    def search_literal_substring(self, substring: str, domain: str | None = None,
                                  case_insensitive: bool = True, case_sensitive: bool = False) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT url, title, text, crawl_timestamp, http_status FROM pages "
            "WHERE text IS NOT NULL AND text != ''")
        rows = c.fetchall()
        res = []
        for url, title, text, ts, hs in rows:
            if not text:
                continue
            if case_insensitive:
                found = substring.lower() in (text or "").lower()
            else:
                found = substring in (text or "")
            if found:
                pos_list = []
                if case_insensitive:
                    tl = (text or "").lower()
                    sl = substring.lower()
                    st = 0
                    while True:
                        ix = tl.find(sl, st)
                        if ix == -1:
                            break
                        as_ = ix
                        ae = ix + len(substring)
                        if text[as_:ae] == substring or text[as_:ae].lower() == substring.lower():
                            pos_list.append(as_)
                        st = ix + 1
                else:
                    st = 0
                    while True:
                        idx = (text or "").find(substring, st)
                        if idx == -1:
                            break
                        pos_list.append(idx)
                        st = idx + 1
                oc = len(pos_list)
                if oc:
                    pos = pos_list[0]
                    cb = text[max(0, pos - 100):pos] if text else ""
                    ca = text[pos + len(substring):pos + len(substring) + 100] if text else ""
                    res.append({"title": title or "", "url": url, "match": substring,
                                "context_before": cb, "context_after": ca,
                                "position": pos, "occurrences": oc,
                                "crawl_timestamp": ts, "http_status": hs})
        if domain:
            fr = []
            for r in res:
                u = r.get("url", "")
                if u.lower().startswith(f"http://{domain}/") or u.lower().startswith(f"https://{domain}/"):
                    fr.append(r)
            res = fr
        return res

    def search_regex(self, pattern: str, domain: str | None = None,
                     max_matches: int = 100) -> list[dict]:
        import re as _re
        try:
            compiled = _re.compile(pattern)
        except _re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        if len(pattern) > 1000:
            raise ValueError("Regex pattern too long (max 1000 characters).")
        c = self.conn.cursor()
        c.execute(
            "SELECT url, title, text, crawl_timestamp, http_status FROM pages "
            "WHERE text IS NOT NULL AND text != ''")
        rows = c.fetchall()
        res = []
        for url, title, text, ts, hs in rows:
            if not text:
                continue
            matches = []
            try:
                for m in _re.finditer(compiled, text):
                    if len(matches) >= max_matches:
                        break
                    st = m.start()
                    en = m.end()
                    matches.append({"start": st, "end": en, "text": m.group()})
            except _re.error:
                continue
            if matches:
                first = matches[0]
                pos = first["start"]
                cb = text[max(0, pos - 100):pos]
                ca = text[first["end"]:first["end"] + 100]
                res.append({"title": title or "", "url": url, "match": first["text"],
                            "context_before": cb, "context_after": ca,
                            "position": pos, "occurrences": len(matches),
                            "crawl_timestamp": ts, "http_status": hs})
        if domain:
            fr = []
            for r in res:
                u = r.get("url", "")
                if u.lower().startswith(f"http://{domain}/") or u.lower().startswith(f"https://{domain}/"):
                    fr.append(r)
            res = fr
        return res



    def stats(self) -> dict:
        """Return database statistics."""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM pages")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM pages WHERE http_status = 200")
        sp = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM pages WHERE http_status = 0")
        ep = c.fetchone()[0]
        c.execute("SELECT http_status, COUNT(*) FROM pages GROUP BY http_status")
        sb = c.fetchall()
        c.execute("SELECT MIN(crawl_timestamp), MAX(crawl_timestamp) FROM pages")
        tr = c.fetchone()
        c.execute("SELECT COUNT(*) FROM pages_fts")
        fs = c.fetchone()[0]
        return {
            "total_pages": total,
            "successful_pages": sp,
            "error_pages": ep,
            "status_breakdown": sb,
            "timestamp_range": tr,
            "fts_index_size": fs,
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
        self.nlp_processor = CrawlNLPProcessor() if CrawlNLPProcessor else None
        self.objectives = None
        if getattr(config, 'instructions', None) and self.nlp_processor:
            try:
                print(f"[DEBUG] scrape_engine: Processing instructions: {config.instructions[:100]}...", file=__import__("sys").stderr)
                self.objectives = self.nlp_processor.process_instructions(config.instructions)
                print(f"[DEBUG] scrape_engine: Objectives - primary: {self.objectives.primary_subject}, keywords: {len(self.objectives.required_keywords)}", file=__import__("sys").stderr)
            except Exception as e:
                print(f"[DEBUG] scrape_engine: Failed to process instructions: {e}", file=__import__("sys").stderr)
                traceback.print_exc()
        elif getattr(config, 'objectives', None):
            self.objectives = config.objectives

    @staticmethod
    def normalize_url(url: str) -> str | None:
        try:
            url, _f = urldefrag(url.strip())
            p = urlparse(url)
            if p.scheme.lower() not in {"http", "https"} or not p.hostname:
                return None
            s = p.scheme.lower()
            h = p.hostname.lower()
            po = p.port
            n = h
            if po and not ((s == "http" and po == 80) or (s == "https" and po == 443)):
                n = f"{h}:{po}"
            pt = p.path or "/"
            return urlunparse((s, n, pt, "", p.query, ""))
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
                req = Request(robots_url, headers={"User-Agent": self.config.user_agent})
                with urlopen(req, timeout=self.config.timeout) as r:
                    body = r.read(512_000).decode("utf-8", errors="replace")
                parser.parse(body.splitlines())
            except HTTPError as e:
                if e.code == 404:
                    parser.parse(["User-agent: *", "Allow: /"])
                else:
                    parser.parse(["User-agent: *", "Disallow: /"])
            except Exception:
                parser.parse(["User-agent: *", "Disallow: /"])
            self.robot_parsers[origin] = parser
        return self.robot_parsers[origin].can_fetch(self.config.user_agent, url)

    def _polite_wait(self):
        el = time.monotonic() - self.last_request_at
        rem = self.config.request_delay - el
        if rem > 0:
            time.sleep(rem)
        self.last_request_at = time.monotonic()

    def fetch(self, url: str) -> PageResult:
        le = "unknown error"
        for attempt in range(self.config.retries + 1):
            self._polite_wait()
            req = Request(url, headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                "Accept-Language": "en-US,en;q=0.8",
            })
            try:
                with urlopen(req, timeout=self.config.timeout) as resp:
                    st = getattr(resp, "status", 200)
                    fu = resp.geturl()
                    ct = resp.headers.get_content_type()
                    if ct not in {"text/html", "application/xhtml+xml"}:
                        return PageResult(requested_url=url, final_url=fu, status=st,
                                          fetched_at=datetime.now(timezone.utc).isoformat(),
                                          title="", description="", text="", links=[],
                                          error=f"Skipped non-HTML content type: {ct}")
                    raw = resp.read(self.config.max_bytes + 1)
                    if len(raw) > self.config.max_bytes:
                        raw = raw[:self.config.max_bytes]
                        tn = " [response truncated at configured byte limit]"
                    else:
                        tn = ""
                    chs = resp.headers.get_content_charset() or "utf-8"
                    html = raw.decode(chs, errors="replace")
                    parser = PageParser(fu)
                    parser.feed(html)
                    parser.close()
                    ext = parser.result()
                    if self.db is not None:
                        self.db.store_page(url=url, title=ext["title"], description=ext["description"],
                                           text=ext["text"] + tn, http_status=st, crawl_depth=0,
                                           referring_url=None)
                    return PageResult(requested_url=url, final_url=fu, status=st,
                                      fetched_at=datetime.now(timezone.utc).isoformat(),
                                      title=ext["title"], description=ext["description"],
                                      text=ext["text"] + tn, links=ext["links"])
            except HTTPError as e:
                le = f"HTTP {e.code}: {e.reason}"
                if 400 <= e.code < 500 and e.code != 429:
                    break
            except (URLError, TimeoutError, OSError) as e:
                le = f"{type(e).__name__}: {e}"
            except Exception as e:
                le = f"{type(e).__name__}: {e}"
                break
            if attempt < self.config.retries:
                time.sleep(min(2 ** attempt, 8))
        return PageResult(requested_url=url, final_url=url, status=0,
                          fetched_at=datetime.now(timezone.utc).isoformat(),
                          title="", description="", text="", links=[], error=le)

    def crawl(self) -> list[PageResult]:
        start = self.normalize_url(self.config.start_url)
        if not start:
            raise ValueError("start_url must be a valid http:// or https:// URL")
        if self.db is not None:
            pass
        print(f"[DEBUG] scrape_engine: Starting crawl from {start} with instructions: {getattr(self.config, 'instructions', '')[:50]}", file=__import__("sys").stderr)
        q = deque([(start, 0)])
        while q and len(self.results) < self.config.max_pages:
            url, depth = q.popleft()
            url = self.normalize_url(url)
            if not url or url in self.visited:
                continue
            if self.db is not None and self.db.page_exists(url):
                logging.info("Skipping previously crawled page: %s", url)
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
            res = self.fetch(url)
            self.results.append(res)
            if res.error:
                logging.warning("Fetch issue for %s: %s", url, res.error)
            if depth < self.config.max_depth and not res.error:
                # Collect and prioritize links if we have objectives
                candidates = []
                for ln in res.links:
                    nl = self.normalize_url(ln)
                    if nl and nl not in self.visited and self.allowed_domain(nl):
                        candidates.append((nl, depth + 1, ln))
                if self.objectives and self.nlp_processor and candidates:
                    try:
                        scored_candidates = []
                        for nl, d, orig_ln in candidates:
                            page_data = {'url': nl, 'title': res.title, 'content': '', 'headings': []}
                            score = self.nlp_processor.score_page_relevance(page_data, self.objectives)
                            scored_candidates.append((nl, d, orig_ln, score))
                        scored_candidates.sort(key=lambda x: x[3], reverse=True)
                        for nl, d, orig_ln, score in scored_candidates:
                            q.append((nl, d))
                    except Exception as e:
                        print(f"[DEBUG] scrape_engine: Link prioritization failed: {e}", file=__import__("sys").stderr)
                        for nl, d, orig_ln in candidates:
                            q.append((nl, d))
                else:
                    for nl, d, orig_ln in candidates:
                        q.append((nl, d))
        print(f"[DEBUG] scrape_engine: Crawl completed. Fetched {len(self.results)} pages", file=__import__("sys").stderr)
        return self.results

    def save(self, path: str):
        payload = {"engine": "EducationalScraper",
                   "generated_at": datetime.now(timezone.utc).isoformat(),
                   "start_url": self.config.start_url,
                   "settings": asdict(self.config),
                   "pages_fetched": len(self.results),
                   "pages": [asdict(p) for p in self.results]}
        with open(path, "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)

    def search_exact_phrase(self, phrase: str, domain: str | None = None,
                           case_insensitive: bool = True) -> list[dict]:
        if self.db is None:
            return []
        return self.db.search_exact_phrase(phrase=phrase, domain=domain,
                                           case_insensitive=case_insensitive)

    def search_literal_substring(self, substring: str, domain: str | None = None,
                                  case_insensitive: bool = True, case_sensitive: bool = False) -> list[dict]:
        if self.db is None:
            return []
        return self.db.search_literal_substring(substring=substring, domain=domain,
                                                 case_insensitive=case_insensitive,
                                                 case_sensitive=case_sensitive)

    def search_regex(self, pattern: str, domain: str | None = None, max_matches: int = 100) -> list[dict]:
        if self.db is None:
            return []
        return self.db.search_regex(pattern=pattern, domain=domain, max_matches=max_matches)


def parse_bool(value: str) -> bool:
    norm = value.strip().lower()
    if norm in {"1", "true", "yes", "y", "on"}:
        return True
    if norm in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def build_argument_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db-path", default="crawl_database.sqlite",
                        help="Path to SQLite database for persistent storage")
    common.add_argument("--verbose", action="store_true")
    main_p = argparse.ArgumentParser(
        description="A polite, configurable educational HTML scraping engine "
                    "with persistent full-text search.",
        parents=[common])
    sub = main_p.add_subparsers(dest="command", help="Available commands")
    c = sub.add_parser("crawl", help="Crawl a website", parents=[common])
    c.add_argument("url", help="Starting page URL (http:// or https://)")
    c.add_argument("--max-pages", type=int, default=20,
                   help="Maximum number of pages to crawl (default: 20)")
    c.add_argument("--max-depth", type=int, default=2,
                   help="Maximum crawl depth (default: 2)")
    c.add_argument("--delay", type=float, default=1.0,
                   help="Minimum seconds between page requests")
    c.add_argument("--timeout", type=float, default=15.0)
    c.add_argument("--retries", type=int, default=2)
    c.add_argument("--max-bytes", type=int, default=2_000_000)
    c.add_argument("--same-domain", type=parse_bool, default=True)
    c.add_argument("--obey-robots", type=parse_bool, default=True)
    c.add_argument("--user-agent", default="EducationalScraper/1.0 (+respectful public-page research)")
    c.add_argument("--output", default="scrape_results.json")
    s = sub.add_parser("search", help="Search the database", parents=[common])
    s.add_argument("--phrase", help='Search for an exact phrase (e.g. "ambient noise floor")')
    s.add_argument("--literal", help='Search for literal text (e.g. "AttributeError")')
    s.add_argument("--regex", help='Search using a regex pattern (e.g. "0x[0-9A-Fa-f]+")')
    s.add_argument("--case-sensitive", action='store_true',
                   help='Case-sensitive search (for --literal)')
    s.add_argument("--limit", type=int, default=20,
                   help='Maximum number of search results')
    s.add_argument("--domain", help='Filter search by domain (e.g. example.com)')
    s.add_argument("--offset", type=int, default=0,
                   help='Result offset for pagination')
    st = sub.add_parser("stats", help="Show database statistics", parents=[common])

    return main_p


def main():
    args = build_argument_parser().parse_args()
    if args.command is None:
        if getattr(args, "url", None):
            args.command = "crawl"
        else:
            build_argument_parser().print_help()
            raise SystemExit(1)
    if args.command == "crawl" and not getattr(args, "url", None):
        raise SystemExit("The 'crawl' command requires a URL argument")
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s: %(message)s")
    cfg = ScraperConfig(start_url=getattr(args, "url", None) if args.command == "crawl" else "",
                        max_pages=args.max_pages if args.command == "crawl" else 20,
                        max_depth=args.max_depth if args.command == "crawl" else 2,
                        request_delay=args.delay if args.command == "crawl" else 1.0,
                        timeout=args.timeout if args.command == "crawl" else 15.0,
                        retries=args.retries if args.command == "crawl" else 2,
                        max_bytes=args.max_bytes if args.command == "crawl" else 2_000_000,
                        same_domain=getattr(args, "same_domain", True),
                        obey_robots=getattr(args, "obey_robots", True),
                        user_agent=getattr(args, "user_agent", "EducationalScraper/1.0 (+respectful public-page research)"),
                        output=getattr(args, "output", "scrape_results.json"),
                        )
    eng = ScraperEngine(cfg, db_path=args.db_path)
    try:
        if args.command == "crawl":
            pag = eng.crawl()
            eng.save(cfg.output)
        elif args.command == "search":
            if eng.db is None:
                raise SystemExit("Search requires a database. Use --db-path to specify one.")
            res = _execute_search(args, eng)
            _print_search_results(res, args)
        elif args.command == "stats":
            if eng.db is None:
                raise SystemExit("Stats require a database. Use --db-path to specify one.")
            _print_stats(eng.db.stats())
    except KeyboardInterrupt:
        logging.warning("Interrupted. Saving results collected so far.")
        if eng.db is not None:
            eng.db.close()
        eng.save(cfg.output)
        raise SystemExit(130)
    except Exception as exc:
        logging.error("%s: %s", type(exc).__name__, exc)
        raise SystemExit(1)
    if args.command == "crawl":
        su = sum(1 for p in eng.results if not p.error and p.status)
        print(f"Finished: {su}/{len(eng.results)} pages fetched successfully.")
        print(f"Output: {cfg.output}")


def _execute_search(args, eng: ScraperEngine) -> list[dict]:
    ph = args.phrase
    lit = args.literal
    reg = args.regex
    cs = args.case_sensitive
    dmn = args.domain
    lim = args.limit
    off = args.offset
    if ph is not None:
        res = eng.search_exact_phrase(phrase=ph, domain=dmn, case_insensitive=not cs)
    elif lit is not None:
        res = eng.search_literal_substring(substring=lit, domain=dmn,
                                            case_insensitive=not cs,
                                            case_sensitive=cs)
    elif reg is not None:
        res = eng.search_regex(pattern=reg, domain=dmn, max_matches=lim + off)
    else:
        raise SystemExit("A search mode is required. Use --phrase, --literal, or --regex.")
    return res[off:off + lim]


def _print_search_results(res: list[dict], args) -> None:
    if not res:
        print("No matches found.")
        return
    for i, r in enumerate(res, 1):
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
    print("Database Statistics:")
    print(f"  Total pages: {stats.get('total_pages', 0)}")
    print(f"  Successful pages: {stats.get('successful_pages', 0)}")
    print(f"  Error pages: {stats.get('error_pages', 0)}")
    print(f"  FTS index size: {stats.get('fts_index_size', 0)}")
    print(f"  Timestamp range: {stats.get('timestamp_range', ('N', 'N'))}")
    print("  Status breakdown:")
    for sc, cnt in stats.get('status_breakdown', []):
        print(f"    HTTP {sc}: {cnt}")


if __name__ == "__main__":
    main()
