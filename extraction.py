#!/usr/bin/env python3
"""
Structured extraction and collection profiles for the web research engine.

Supports selective scraping profiles that determine:
- What to discover
- What to download
- What to extract
- What to retain
- What to index
- What to discard

Profiles:
- Metadata only
- Main readable text
- Full article
- Headings and document structure
- Tables
- Code and technical examples
- Links and references
- Structured metadata
- Entities and relationships
- Images and image metadata
- PDFs and attachments
- Full archival capture
- Custom combinations
"""

import hashlib
import json
import re
from html.parser import HTMLParser
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Extraction result types
# ---------------------------------------------------------------------------


class ExtractionType(Enum):
    """Types of extractable content within a document."""
    TITLE = "title"
    DESCRIPTION = "description"
    HEADING_H1 = "heading_h1"
    HEADING_H2 = "heading_h2"
    HEADING_H3 = "heading_h3"
    HEADING_H4 = "heading_h4"
    HEADING_H5 = "heading_h5"
    HEADING_H6 = "heading_h6"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    TABLE = "table"
    MATH = "math"
    CITATION = "citation"
    METADATA = "metadata"
    ENTITY = "entity"
    LINK = "link"
    IMAGE = "image"
    FILE = "file"


@dataclass
class ExtractedSection:
    """Represents a structured section of extracted content."""
    extraction_type: ExtractionType
    title: str  # For headings; empty for paragraphs/etc.
    text: str
    level: int  # Heading level (1-6) or 0 for non-heading types
    start_pos: int  # Position in original text for reference
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Complete extraction result from a document."""
    url: str
    title: str
    description: str
    sections: List[ExtractedSection]
    raw_text: str  # Full normalized text for FTS
    extraction_timestamp: str
    profile_used: str
    fingerprint: str  # SHA-256 of normalized extracted text


# ---------------------------------------------------------------------------
# Collection Profiles
# ---------------------------------------------------------------------------


class CollectionProfile(Enum):
    """Named collection profiles that control extraction behavior."""

    # Minimal: only essential metadata
    METADATA_ONLY = "metadata_only"

    # Main readable text, scripts/styles removed
    MAIN_TEXT = "main_text"

    # Full article text with headings preserved
    FULL_ARTICLE = "full_article"

    # Headings and document structure only
    HEADINGS_STRUCTURE = "headings_structure"

    # Tables extracted as structured data
    TABLES = "tables"

    # Code examples and technical content
    CODE_TECHNICAL = "code_technical"

    # Links and references
    LINKS_REFERENCES = "links_references"

    # Structured metadata (Open Graph, JSON-LD, Schema.org)
    STRUCTURED_METADATA = "structured_metadata"

    # Entities and relationship mentions
    ENTITIES = "entities"

    # Images and image alt text
    IMAGES = "images"

    # Full archival capture (everything including media)
    FULL_ARCHIVAL = "full_archival"

    # Custom profile specified by user
    CUSTOM = "custom"


PROFILE_DEFINITIONS: Dict[CollectionProfile, Dict[str, Any]] = {
    CollectionProfile.METADATA_ONLY: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": False,
        "extract_paragraphs": False,
        "extract_tables": False,
        "extract_code": False,
        "extract_links": False,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": False,
    },
    CollectionProfile.MAIN_TEXT: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": False,
        "extract_code": False,
        "extract_links": False,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": True,
    },
    CollectionProfile.FULL_ARTICLE: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": False,
        "discard_media": False,
        "index_full_text": True,
    },
    CollectionProfile.HEADINGS_STRUCTURE: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": False,
        "extract_tables": False,
        "extract_code": False,
        "extract_links": False,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": True,
    },
    CollectionProfile.TABLES: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": False,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": True,
    },
    CollectionProfile.CODE_TECHNICAL: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": False,
        "index_full_text": True,
    },
    CollectionProfile.LINKS_REFERENCES: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": True,
    },
    CollectionProfile.STRUCTURED_METADATA: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": False,
        "extract_paragraphs": False,
        "extract_tables": False,
        "extract_code": False,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": False,
    },
    CollectionProfile.ENTITIES: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": True,
        "extract_images": False,
        "discard_scripts_styles": True,
        "discard_images": True,
        "discard_media": True,
        "index_full_text": True,
    },
    CollectionProfile.IMAGES: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": False,
        "extract_images": True,
        "discard_scripts_styles": True,
        "discard_images": False,
        "discard_media": False,
        "index_full_text": True,
    },
    CollectionProfile.FULL_ARCHIVAL: {
        "extract_title": True,
        "extract_description": True,
        "extract_headings": True,
        "extract_paragraphs": True,
        "extract_tables": True,
        "extract_code": True,
        "extract_links": True,
        "extract_metadata": True,
        "extract_entities": True,
        "extract_images": True,
        "discard_scripts_styles": True,
        "discard_images": False,
        "discard_media": False,
        "index_full_text": True,
    },
}


def get_profile_definition(profile: CollectionProfile) -> Dict[str, Any]:
    """Return the extraction profile definition for a given profile name."""
    return PROFILE_DEFINITIONS.get(profile, PROFILE_DEFINITIONS[CollectionProfile.METADATA_ONLY])


def is_extraction_enabled(profile: CollectionProfile, extraction_type: ExtractionType) -> bool:
    """Check whether a given extraction type is enabled for a profile."""
    definition = PROFILE_DEFINITIONS.get(profile, {})
    return definition.get(extraction_type.value, False)


# ---------------------------------------------------------------------------
# HTML Structured Extractor
# ---------------------------------------------------------------------------


class StructuredHTMLParser:
    """
    HTML parser that extracts structured content according to a collection profile.
    Preserves section relationships (headings -> associated content).
    """

    def __init__(self, profile: CollectionProfile = CollectionProfile.MAIN_TEXT):
        self.profile = profile
        self.sections: List[ExtractedSection] = []
        self.current_section: Optional[ExtractedSection] = None
        self.heading_stack: List[ExtractedSection] = []
        self._in_code_block = False
        self._code_lang: str = ""
        self._tables: List[List[List[str]]] = []
        self._current_table_rows: List[List[str]] = []
        self._table_in_progress = False
        self._discard_tags: Set[str] = set()
        self._meta_tags: Dict[str, str] = {}
        self._html_parser: Optional[_ExtractionHTMLParser] = None

    def should_discard_tag(self, tag: str) -> bool:
        """Check if a tag should be discarded based on profile settings."""
        if tag in {"script", "style", "noscript", "svg", "canvas", "template"}:
            return True
        return tag in self._discard_tags

    def extract(self, html: str, base_url: str = "") -> ExtractionResult:
        """Extract structured content from HTML string."""
        # Reset state
        self.sections = []
        self.current_section = None
        self.heading_stack = []
        self._in_code_block = False
        self._code_lang = ""
        self._tables = []
        self._current_table_rows = []
        self._table_in_progress = False
        self._discard_tags = set()
        self._meta_tags = {}

        parser = _ExtractionHTMLParser(self)
        self._html_parser = parser
        parser.feed(html)
        parser.close()

        # Build raw text from all sections
        all_text_parts = []
        for sec in self.sections:
            all_text_parts.append(sec.text)

        raw_text = "\n".join(all_text_parts).strip()
        fingerprint = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # Collect metadata description
        description = self._meta_tags.get("description", "")
        if not description:
            # Try og:description
            for tag_name in ["og:description", "twitter:description"]:
                if tag_name in self._meta_tags:
                    description = self._meta_tags[tag_name]
                    break

        result = ExtractionResult(
            url=base_url,
            title=self._extract_title(html),
            description=description,
            sections=self.sections,
            raw_text=raw_text,
            extraction_timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            profile_used=self.profile.value,
            fingerprint=fingerprint,
        )
        self._html_parser = None
        return result

    def _extract_title(self, html: str) -> str:
        """Extract the page title from HTML."""
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            return re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        # Fallback: h1
        h1_match = re.search(r"<h1[^>]>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            return re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
        return ""

    def _flush_current_section(self):
        """Flush the current section into the sections list."""
        if self.current_section and self.current_section.text.strip():
            self.sections.append(self.current_section)
        self.current_section = None


class _ExtractionHTMLParser(HTMLParser):
    """Internal HTML parser doing the actual extraction work."""

    def __init__(self, parser: StructuredHTMLParser):
        super().__init__(convert_charrefs=True)
        self.parser = parser  # direct reference to StructuredHTMLParser
        self._deep_drop = 0
        self._in_title = False
        self._description_found = False
        self._last_tag: Optional[str] = None  # Track the most recent start tag
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)

        # Handle discard tags
        if self.parser.should_discard_tag(tag):
            if tag not in {"script", "style", "noscript"}:
                self.parser._discard_tags.add(tag)
            if tag in {"script", "style"}:
                self._deep_drop += 1
            return

        # Handle deep drop (script/style)
        if self._deep_drop > 0:
            return

        # Handle title
        if tag == "title":
            self._in_title = True
            return

        # Handle meta description
        if tag == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name in {"description", "og:description"} and not self._description_found:
                self._description_found = True
                self.parser._meta_tags["description"] = (
                    attrs_dict.get("content") or "").strip()
            if name == "og:description" and not self._description_found:
                self.parser._meta_tags["og:description"] = (
                    attrs_dict.get("content") or "").strip()

        # Handle headings
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            # Flush any previous section
            self.parser._flush_current_section()

            # Create the section
            self.parser.current_section = ExtractedSection(
                extraction_type=ExtractionType.HEADING_H1 if level == 1
                else ExtractionType.HEADING_H2 if level == 2
                else ExtractionType.HEADING_H3 if level == 3
                else ExtractionType.HEADING_H4 if level == 4
                else ExtractionType.HEADING_H5 if level == 5
                else ExtractionType.HEADING_H6,
                title="",
                text="",
                level=level,
                start_pos=0,
                end_pos=0,
            )
            # Push to heading stack for relationship tracking
            self.parser.heading_stack.append(self.parser.current_section)
            return

        # Handle anchor links
        if tag == "a":
            href = (attrs_dict.get("href") or "").strip()
            if href:
                pass  # Could store link info, but profile-dependent

        # Store the current tag for handle_data reference
        self._last_tag = tag

        # Handle paragraphs and block containers
        if tag in {"p", "div", "br", "li", "section", "article"}:
            # Start a new potential section
            self.parser._flush_current_section()
            # The text handling in handle_data will populate it

        # Handle code blocks (pre > code)
        if tag == "pre":
            self.parser._in_code_block = True
            self._code_lang = ""
            # Look for language indicator
            code_elem = dict(attrs).get("class", "")
            if "language-" in code_elem:
                self._code_lang = code_elem.split("language-")[1].split()[0]

        # Handle tables - simplified approach
        if tag == "table":
            self.parser._table_in_progress = True
            self.parser._current_table_rows = []

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg", "canvas", "template"}:
            if self._deep_drop > 0:
                self._deep_drop -= 1
            return

        if self._deep_drop > 0:
            return

        # Handle title end
        if tag == "title":
            self._in_title = False
            return

        # Handle headings end - pop from stack
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            if self.parser.heading_stack:
                self.parser.heading_stack.pop()
            # Flush the heading section
            self.parser._flush_current_section()
            return

        # Handle pre/code end
        if tag == "pre":
            self.parser._in_code_block = False
            # Create a code block section if we have content
            if (self.parser.current_section
                    and self.parser.current_section.extraction_type == ExtractionType.CODE_BLOCK):
                # Already handled, just flush
                self.parser._flush_current_section()
            else:
                # Create a code block section
                code_text = self._extract_code_text()
                if code_text.strip():
                    self.parser.current_section = ExtractedSection(
                        extraction_type=ExtractionType.CODE_BLOCK,
                        title="Code block",
                        text=code_text,
                        level=0,
                        start_pos=0,
                        end_pos=0,
                    )
                    self.parser._flush_current_section()
            return

        # Handle table end
        if tag == "table":
            self.parser._table_in_progress = False
            if self.parser._current_table_rows:
                # Store the table as extracted
                table_text = "\n".join(
                    " | ".join(row) for row in self.parser._current_table_rows
                )
                if table_text.strip():
                    self.parser.current_section = ExtractedSection(
                        extraction_type=ExtractionType.TABLE,
                        title="Table",
                        text=table_text,
                        level=0,
                        start_pos=0,
                        end_pos=0,
                    )
                    self.parser._flush_current_section()
            self.parser._current_table_rows = []
            return

        # Handle block containers - finalize section
        if tag in {"p", "div", "li", "section", "article"}:
            self.parser._flush_current_section()
            self._last_tag = None

    def handle_data(self, data: str):
        if self._deep_drop > 0:
            return

        cleaned = data.strip()
        if not cleaned:
            return

        if self._in_title:
            # Title handled separately; just accumulate
            return

        # Determine what kind of content this is based on current state
        # Priority: code block > headings > paragraphs > other

        if self.parser._in_code_block:
            # Accumulate code block text
            if self.parser.current_section is None:
                self.parser.current_section = ExtractedSection(
                    extraction_type=ExtractionType.CODE_BLOCK,
                    title="Code block",
                    text="",
                    level=0,
                    start_pos=0,
                    end_pos=0,
                )
            self.parser.current_section.text += (" " if self.parser.current_section.text else "") + cleaned
            return

        # If we're at a heading (current_section is a heading type), append text
        if (self.parser.current_section
                and self.parser.current_section.extraction_type
                and self.parser.current_section.extraction_type.value.startswith("heading_h")):
            self.parser.current_section.text += (" " if self.parser.current_section.text else "") + cleaned
            return

        # Otherwise, treat as paragraph or list item
        # Flush any existing section first
        self.parser._flush_current_section()

        # Determine the extraction type based on profile
        et = self._determine_extraction_type(self._last_tag, cleaned)

        self.parser.current_section = ExtractedSection(
            extraction_type=et,
            title="",
            text=cleaned,
            level=0,
            start_pos=0,
            end_pos=0,
        )

    def _determine_extraction_type(self, tag: str, data: str) -> ExtractionType:
        """Determine the extraction type based on the tag and profile settings."""
        # Simple heuristic: certain tags default to paragraph
        if tag in {"span", "font", "b", "i", "u", "strong", "em"}:
            return ExtractionType.PARAGRAPH

        return ExtractionType.PARAGRAPH

    def _extract_code_text(self) -> str:
        """Extract accumulated code text from the pre block."""
        return self.parser.current_section.text if self.parser.current_section else ""


# ---------------------------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------------------------


class EntityMention:
    """A mention of an entity within a document with source context."""

    def __init__(self, text: str, entity_type: str,
                 section: Optional[ExtractedSection] = None,
                 position: Optional[Tuple[int, int]] = None):
        self.text = text
        self.entity_type = entity_type  # e.g., "person", "organization", "product"
        self.section = section  # The section where this entity was mentioned
        self.position = position  # (start_pos, end_pos) in the extracted text
        self.confidence: float = 0.8  # Default confidence
        self.evidence: str = ""  # Source URL, section title, etc.


class Entity:
    """A persistent entity record with aliases and relationships."""

    def __init__(self, canonical_name: str, entity_type: str):
        self.canonical_name = canonical_name
        self.entity_type = entity_type
        self.aliases: Set[str] = set()
        self.mentions: List[EntityMention] = []
        self.relationships: List[Dict[str, Any]] = []
        self.source_urls: Set[str] = set()
        self.extraction_count = 0
        self.last_seen: str = ""

    def add_alias(self, alias: str):
        """Add an alternate spelling or abbreviation."""
        self.aliases.add(alias)

    def add_mention(self, mention: EntityMention):
        """Add a source mention of this entity."""
        self.mentions.append(mention)
        self.source_urls.add(mention.section.text if mention.section else "")
        self.extraction_count += 1
        self.last_seen = mention.section.evidence if mention.section and mention.section.evidence else ""

    def add_relationship(self, relationship: Dict[str, Any]):
        """Add a relationship to another entity."""
        self.relationships.append(relationship)


class EntityExtractor:
    """
    Extracts named entities from extracted text using pattern matching
    and heuristics. Supports people, organizations, products, technologies,
    and other categories relevant to web research.
    """

    # Patterns for entity types
    PATTERNS: Dict[str, List[str]] = {
        "person": [
            r"\b[A-Z][a-z]+(?:[\s'-][A-Z][a-z]+)+\s+(?:said|explained|wrote| noted)",
        ],
        "organization": [
            r"\b[A-Z][a-z]+(?:[\s&-][A-Z][a-z]+)*\s+(?:Inc|LLC|Corp|Ltd|GmbH|AG)\b",
            r"\b(?:Google|Microsoft|Apple|Amazon|Meta|Twitter)\b",
        ],
        "product": [
            r"\b(?:ESP32|Raspberry Pi|Arduino|ESP8266)\b",
            r"\b(?:TensorFlow|PyTorch|scikit-learn)\b",
        ],
        "technology": [
            r"\b(?:API|SQL|HTTP|HTTPS|JSON|XML|REST|GraphQL)\b",
            r"\b(?:Python|JavaScript|TypeScript|Rust|Go|React|Angular)\b",
        ],
        "location": [
            r"\b(?:University of|College of|Department of)\s+[A-Z][a-z]+(?:[\s'-][A-Z][a-z]+)*",
        ],
    }

    def __init__(self):
        self.entities: Dict[str, Entity] = {}  # canonical_name -> Entity
        self._normalized_cache: Dict[str, str] = {}

    def _normalize_name(self, name: str) -> str:
        """Normalize an entity name for caching/dedup."""
        key = name.strip().lower()
        if key not in self._normalized_cache:
            # Simple normalization: lowercase, collapse whitespace
            self._normalized_cache[key] = re.sub(r"\s+", " ", key)
        return self._normalized_cache[key]

    def process_text(self, text: str, entity_type: str = "general",
                     source_url: str = "") -> List[EntityMention]:
        """
        Process text and extract entities of the specified type.
        Returns a list of EntityMention objects.
        """
        mentions: List[EntityMention] = []

        if entity_type == "general":
            # Run all pattern categories
            for etype, patterns in self.PATTERNS.items():
                mentions.extend(self._extract_by_patterns(text, patterns, etype, source_url))
        else:
            mentions = self._extract_by_patterns(
                text, self.PATTERNS.get(entity_type, []), entity_type, source_url)

        # Deduplicate and register entities
        for mention in mentions:
            norm = self._normalize_name(mention.text)
            if norm in self.entities:
                # Entity already exists; just add this mention
                self.entities[norm].add_mention(mention)
            else:
                # Create new entity
                entity = Entity(mention.text, mention.entity_type)
                entity.add_mention(mention)
                self.entities[norm] = entity

        return mentions

    def _extract_by_patterns(
        self, text: str, patterns: List[str], entity_type: str,
        source_url: str
    ) -> List[EntityMention]:
        """Extract entities using a list of regex patterns."""
        mentions: List[EntityMention] = []
        for pattern in patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matched_text = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()

                    # Skip very short matches or common words
                    if len(matched_text) < 3:
                        continue

                    mention = EntityMention(
                        text=matched_text,
                        entity_type=entity_type,
                        position=(start_pos, end_pos),
                    )
                    mentions.append(mention)
            except re.error:
                # Skip invalid patterns
                continue
        return mentions

    def get_entity(self, name: str) -> Optional[Entity]:
        """Get an entity by its canonical name, or None."""
        norm = self._normalize_name(name)
        return self.entities.get(norm)

    def get_all_entities(self) -> Dict[str, Entity]:
        """Return all extracted entities."""
        return dict(self.entities)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entities to dict for storage."""
        result = {}
        for name, entity in self.entities.items():
            result[name] = {
                "canonical_name": entity.canonical_name,
                "entity_type": entity.entity_type,
                "aliases": list(entity.aliases),
                "mentions_count": entity.extraction_count,
                "source_urls": list(entity.source_urls),
                "relationships": entity.relationships,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityExtractor":
        """Deserialize entities from dict."""
        instance = cls()
        for name, ndata in data.items():
            entity = Entity(canonical_name=ndata.get("canonical_name", name),
                            entity_type=ndata.get("entity_type", "general"))
            entity.aliases = set(ndata.get("aliases", []))
            entity.extraction_count = ndata.get("mentions_count", 0)
            entity.source_urls = set(ndata.get("source_urls", []))
            entity.relationships = ndata.get("relationships", [])
            instance.entities[name] = entity
        return instance