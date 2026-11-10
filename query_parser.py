#!/usr/bin/env python3
"""
Natural-language query parser for the web research engine.

Converts user instructions in ordinary language into structured discovery,
filtering, crawling, extraction, and retention plans.

The same query engine powers both the graphical interface and command-line interface.
"""

import traceback
from extraction import CollectionProfile
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Query operator types
# ---------------------------------------------------------------------------


class QueryOperator(Enum):
    """Supported query operators."""
    CONTAINS = "contains"
    CONTAINS_ALL = "contains_all"
    EXCLUDE = "exclude"
    EXACT = "exact"
    REGEX = "regex"
    TYPE = "type"
    DOMAIN = "domain"
    EXCLUDE_DOMAIN = "exclude_domain"
    DEEP = "deep"
    DEPTH = "depth"
    LIMIT = "limit"
    SINCE = "since"
    UNTIL = "until"
    PROFILE = "profile"
    PROVIDER = "provider"
    ALL_PROVIDERS = "all_providers"
    LANGUAGE = "language"
    MIN_RELEVANCE = "min_relevance"
    PRIMARY_SOURCES = "primary_sources"
    SAVE = "save"


# ---------------------------------------------------------------------------
# Query structure
# ---------------------------------------------------------------------------


@dataclass
class StructuredQuery:
    """
    A structured query representing a parsed natural-language research request.
    """
    subject: str = ""
    required_phrases: List[str] = field(default_factory=list)
    optional_phrases: List[str] = field(default_factory=list)
    excluded_phrases: List[str] = field(default_factory=list)
    exact_phrase: str = ""
    content_types: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    excluded_domains: List[str] = field(default_factory=list)
    deep: bool = False
    max_depth: int = 2
    max_results: int = 50
    since_date: Optional[str] = None
    until_date: Optional[str] = None
    profile: CollectionProfile = CollectionProfile.MAIN_TEXT
    provider: Optional[str] = None
    all_providers: bool = False
    language: Optional[str] = None
    min_relevance: float = 0.0
    primary_sources: bool = False
    save_as: str = ""


# ---------------------------------------------------------------------------
# Operator extraction using regex on raw input
# ---------------------------------------------------------------------------

# Regex patterns for extracting operator-value pairs from raw input
# Each pattern: (regex_pattern, operator_key, value_groups_spec)
OPERATOR_REGEX_PATTERNS: List[tuple] = [
    (r"--contains-all\s+\"([^\"]*)\"\s+\"([^\"]*)\"", "contains_all", 2),
    (r"--contains-all\s+(\S+)\s+(\S+)", "contains_all", 2),
    (r"--contains\s+\"([^\"]*)\"", "contains", 1),
    (r"--contains\s+(\S+)", "contains", 1),
    (r"--exclude\s+\"([^\"]*)\"", "exclude", 1),
    (r"--exclude\s+(\S+)", "exclude", 1),
    (r"--exclude\s+\"([^\"]*)\"\s+and\s+\"([^\"]*)\"", "exclude", 2),
    (r"--exclude\s+(\S+)\s+and\s+(\S+)", "exclude", 2),
    (r"--type\s+\"([^\"]*)\"", "type", 1),
    (r"--type\s+(\S+)", "type", 1),
    (r"--domain\s+\"([^\"]*)\"", "domain", 1),
    (r"--domain\s+(\S+)", "domain", 1),
    (r"--exclude-domain\s+\"([^\"]*)\"", "exclude_domain", 1),
    (r"--exclude-domain\s+(\S+)", "exclude_domain", 1),
    (r"--deep\s+", "deep", "flag"),
    (r"--depth\s+(\d+)", "depth", 1),
    (r"--limit\s+(\d+)", "limit", 1),
    (r"--since\s+\"([^\"]*)\"", "since", 1),
    (r"--since\s+(\S+)", "since", 1),
    (r"--until\s+\"([^\"]*)\"", "until", 1),
    (r"--until\s+(\S+)", "until", 1),
    (r"--profile\s+\"([^\"]*)\"", "profile", 1),
    (r"--profile\s+(\S+)", "profile", 1),
    (r"--provider\s+\"([^\"]*)\"", "provider", 1),
    (r"--provider\s+(\S+)", "provider", 1),
    (r"--all-providers\s+", "all_providers", "flag"),
    (r"--language\s+\"([^\"]*)\"", "language", 1),
    (r"--language\s+(\S+)", "language", 1),
    (r"--min-relevance\s+([\d.]+)", "min_relevance", 1),
    (r"--primary-sources\s+", "primary_sources", "flag"),
    (r"--save\s+\"([^\"]*)\"", "save", 1),
    (r"--save\s+(\S+)", "save", 1),
    (r"--exact\s+\"([^\"]*)\"", "exact", 1),
    (r"--exact\s+(\S+)", "exact", 1),
    (r"--regex\s+\"([^\"]*)\"", "regex", 1),
    (r"--regex\s+(\S+)", "regex", 1),
]

# Handler functions for operators that need custom logic
def _handle_contains(query: StructuredQuery, value: str) -> None:
    """Handle --contains X: add X as a required phrase."""
    if value and value not in query.required_phrases:
        query.required_phrases.append(value)


def _handle_contains_all(query: StructuredQuery, p1: str, p2: str) -> None:
    """Handle --contains-all X Y: add both X and Y as required phrases."""
    if p1 and p1 not in query.required_phrases:
        query.required_phrases.append(p1)
    if p2 and p2 not in query.required_phrases:
        query.required_phrases.append(p2)


def _handle_exclude(query: StructuredQuery, value: str) -> None:
    """Handle --exclude X: add X as an excluded phrase."""
    if value and value not in query.excluded_phrases:
        query.excluded_phrases.append(value)


def _handle_exclude_domain(query: StructuredQuery, value: str) -> None:
    """Handle --exclude-domain X: add X as an excluded domain."""
    if value and value not in query.excluded_domains:
        query.excluded_domains.append(value)


def _handle_type(query: StructuredQuery, value: str) -> None:
    """Handle --type X: add X as a content type."""
    if value and value not in query.content_types:
        query.content_types.append(value)


def _handle_domain(query: StructuredQuery, value: str) -> None:
    """Handle --domain X: add X as a domain restriction."""
    if value and value not in query.domains:
        query.domains.append(value)


def _handle_deep(query: StructuredQuery) -> None:
    """Handle --deep: enable deep exploration."""
    query.deep = True


def _handle_depth(query: StructuredQuery, value: str) -> None:
    """Handle --depth N: set max crawl depth."""
    try:
        q_val = int(value)
        if q_val > 0:
            query.max_depth = q_val
    except ValueError as _se_debug_exc:
        print(f"[DEBUG] {__name__}: ValueError in query_parser: {_se_debug_exc}", file=__import__('sys').stderr)
        traceback.print_exc()
        pass


def _handle_limit(query: StructuredQuery, value: str) -> None:
    """Handle --limit N: set max results."""
    try:
        q_val = int(value)
        if q_val > 0:
            query.max_results = q_val
    except ValueError as _se_debug_exc:
        print(f"[DEBUG] {__name__}: ValueError in query_parser: {_se_debug_exc}", file=__import__('sys').stderr)
        traceback.print_exc()
        pass


def _handle_since(query: StructuredQuery, value: str) -> None:
    """Handle --since X: set start date filter."""
    query.since_date = value


def _handle_until(query: StructuredQuery, value: str) -> None:
    """Handle --until X: set end date filter."""
    query.until_date = value


def _handle_profile(query: StructuredQuery, value: str) -> None:
    """Handle --profile X: set collection profile."""
    try:
        query.profile = CollectionProfile(value)
    except ValueError as _se_debug_exc:
        print(f"[DEBUG] {__name__}: ValueError in query_parser: {_se_debug_exc}", file=__import__('sys').stderr)
        traceback.print_exc()
        pass


def _handle_provider(query: StructuredQuery, value: str) -> None:
    """Handle --provider X: set search provider."""
    query.provider = value


def _handle_all_providers(query: StructuredQuery) -> None:
    """Handle --all-providers: query all providers."""
    query.all_providers = True


def _handle_language(query: StructuredQuery, value: str) -> None:
    """Handle --language X: set language filter."""
    query.language = value


def _handle_min_relevance(query: StructuredQuery, value: str) -> None:
    """Handle --min-relevance N: set minimum relevance threshold."""
    try:
        query.min_relevance = float(value)
    except ValueError as _se_debug_exc:
        print(f"[DEBUG] {__name__}: ValueError in query_parser: {_se_debug_exc}", file=__import__('sys').stderr)
        traceback.print_exc()
        pass


def _handle_save(query: StructuredQuery, value: str) -> None:
    """Handle --save X: set save name."""
    query.save_as = value


# Handler map: operator_key -> (handler_function, needs_two_values)
HANDLER_MAP: Dict[str, tuple] = {
    "contains": (_handle_contains, False),
    "contains_all": (_handle_contains_all, True),
    "exclude": (_handle_exclude, False),
    "exclude_domain": (_handle_exclude_domain, False),
    "type": (_handle_type, False),
    "domain": (_handle_domain, False),
    "deep": (_handle_deep, False),
    "depth": (_handle_depth, False),
    "limit": (_handle_limit, False),
    "since": (_handle_since, False),
    "until": (_handle_until, False),
    "profile": (_handle_profile, False),
    "provider": (_handle_provider, False),
    "all_providers": (_handle_all_providers, False),
    "language": (_handle_language, False),
    "min_relevance": (_handle_min_relevance, False),
    "save": (_handle_save, False),
}


def extract_operator_values(raw_input: str, query: StructuredQuery) -> None:
    """
    Extract --operator value pairs from raw input using regex patterns.
    
    This modifies the query in place.
    
    Args:
        raw_input: The original user input string
        query: The structured query to populate
    """
    input_lower = raw_input.lower()
    
    # Process patterns in order; stop after first match for each operator type
    processed_operators: Set[str] = set()
    
    for pattern, op_key, n_groups in OPERATOR_REGEX_PATTERNS:
        # Skip if we've already processed this operator key
        if op_key in processed_operators:
            continue
        
        match = re.search(pattern, input_lower)
        if match:
            processed_operators.add(op_key)
            
            # Extract values based on number of groups
            if n_groups == 1:
                value = match.group(1).strip()
                # Set the query field based on operator key
                if op_key == "contains":
                    _handle_contains(query, value)
                elif op_key == "exclude":
                    _handle_exclude(query, value)
                elif op_key == "type":
                    _handle_type(query, value)
                elif op_key == "domain":
                    _handle_domain(query, value)
                elif op_key == "exclude_domain":
                    _handle_exclude_domain(query, value)
                elif op_key == "deep":
                    _handle_deep(query)
                elif op_key == "depth":
                    _handle_depth(query, match.group(1).strip())
                elif op_key == "limit":
                    _handle_limit(query, match.group(1).strip())
                elif op_key == "since":
                    _handle_since(query, match.group(1).strip())
                elif op_key == "until":
                    _handle_until(query, match.group(1).strip())
                elif op_key == "profile":
                    _handle_profile(query, match.group(1).strip())
                elif op_key == "provider":
                    _handle_provider(query, match.group(1).strip())
                elif op_key == "language":
                    _handle_language(query, match.group(1).strip())
                elif op_key == "min_relevance":
                    _handle_min_relevance(query, match.group(1).strip())
                elif op_key == "save":
                    _handle_save(query, match.group(1).strip())
            elif n_groups == 2:
                p1 = match.group(1).strip()
                p2 = match.group(2).strip()
                # Set the query field based on operator key
                if op_key == "contains_all":
                    _handle_contains_all(query, p1, p2)
                elif op_key == "exclude" and n_groups == 2:
                    # Two-exclude pattern: --exclude X and Y
                    if p1 and p1 not in query.excluded_phrases:
                        query.excluded_phrases.append(p1)
                    if p2 and p2 not in query.excluded_phrases:
                        query.excluded_phrases.append(p2)
            # Flag-style operators (n_groups is "flag")
            if op_key == "deep":
                _handle_deep(query)
            elif op_key == "all_providers":
                query.all_providers = True
            elif op_key == "primary_sources":
                query.primary_sources = True


# ---------------------------------------------------------------------------
# Natural-language Query Parser
# ---------------------------------------------------------------------------

class NaturalLanguageParser:
    """
    Parser that converts ordinary-language research instructions into
    structured queries.

    Supports command formats like:
      scrape "<subject or topic>" [conditions] [collection options]

    And natural-language descriptions like:
      "Find technical articles about ESP32 firmware updates that mention
       OTA, partition tables, and rollback. Exclude unrelated products.
       Collect code examples, installation instructions, and dependencies."
    """

    # Command verbs that should be stripped from the subject
    COMMAND_VERBS = {"scrape", "find", "search", "research", "analyze", "explore"}

    # Quoted phrase pattern for exact phrase extraction
    QUOTED_PHRASE_PATTERN = r'"([^"]*)"'

    def parse(self, user_input: str) -> StructuredQuery:
        """
        Parse a natural-language user input string into a StructuredQuery.

        Parsing order:
        1. Extract operator-value pairs using regex patterns on raw input
        2. Extract natural-language phrases (that contain X, excluding Y)
        3. Extract the subject from remaining text
        4. Extract exact/quoted phrases
        5. Normalize and validate
        """
        query = StructuredQuery()
        raw_input = user_input.strip()

        # Step 1: Extract operator-value pairs using regex patterns
        extract_operator_values(raw_input, query)

        # Step 2: Extract natural-language phrases
        input_lower = raw_input.lower()
        self._extract_nl_phrases(input_lower, query)

        # Step 3: Extract the subject from remaining text
        # Remove operator-matched portions from the input, then find the subject
        remaining = self._extract_subject(raw_input, query)
        query.subject = remaining

        # Step 4: Extract exact/quoted phrases
        self._extract_quoted_phrases(raw_input, query)

        # Step 5: Normalize and validate
        self._normalize_query(query)

        return query

    def _extract_nl_phrases(self, input_lower: str, query: StructuredQuery):
        """
        Extract natural-language phrases like:
        - "that contain X Y Z"  (required phrases)
        - "excluding X Y Z"    (excluded phrases)
        """
        # Pattern: "that contain X Y Z" or "that includes X Y Z"
        that_patterns = [
            r"that\s+contains?\s+(.+?)(?:\s+excluding|\s+\.)",
            r"that\s+includes?\s+(.+?)(?:\s+excluding|\s+\.)",
            r"with\s+(.+?)(?:\s+excluding|\s+\.)",
        ]

        for pattern in that_patterns:
            match = re.search(pattern, input_lower)
            if match:
                phrase_text = match.group(1).strip()
                # Split by comma - treat all as required phrases
                phrases = [p.strip() for p in phrase_text.split(",") if p.strip()]
                query.required_phrases.extend(phrases)
                # Also add to optional as backup
                query.optional_phrases.extend(phrases)

        # Pattern: "excluding X Y Z" or "except X Y Z"
        exclude_pattern = r"(?:excluding|except)\s+(.+?)(?:\s+\.)"
        match = re.search(exclude_pattern, input_lower)
        if match:
            exclude_text = match.group(1).strip()
            phrases = [p.strip() for p in re.split(r",| and ", exclude_text) if p.strip()]
            query.excluded_phrases.extend(phrases)

    def _extract_subject(self, raw_input: str, query: StructuredQuery) -> str:
        """
        Extract the subject/topic from the raw input AFTER removing operator
        tokens and their values. This ensures operators like --contains, --exclude, etc.
        don't get included in the subject.
        
        Simple approach: remove all operator-matched portions from the input,
        then find the first substantial word sequence.
        """
        input_lower = raw_input.lower()
        
        # Find all operator match spans and build a mask of excluded text
        excluded_chars: Set[int] = set()
        
        for pattern, op_key, n_groups in OPERATOR_REGEX_PATTERNS:
            for match in re.finditer(pattern, input_lower):
                start, end = match.span()
                for i in range(start, end):
                    excluded_chars.add(i)
        
        # Also exclude command verbs at the start
        tokens = raw_input.split()
        for i, token in enumerate(tokens):
            if token in self.COMMAND_VERBS:
                # Exclude the first token if it's a command verb
                if i == 0:
                    # Mark all characters of the first token as excluded
                    first_token = tokens[0]
                    for j in range(len(first_token)):
                        if j < len(raw_input):
                            excluded_chars.add(j)
        
        # Build subject text from non-excluded characters
        subject_chars = []
        for i, char in enumerate(raw_input):
            if i not in excluded_chars:
                subject_chars.append(char)
        
        subject = ''.join(subject_chars)

        # Further cleanup: remove any residual operator words
        operator_words = {
            "contains", "contains_all", "exclude", "exact", "regex",
            "type", "domain", "exclude_domain", "limit", "depth",
            "since", "until", "profile", "provider", "all_providers",
            "language", "min_relevance", "save"
        }
        subject_words = [w for w in subject.split() if w not in operator_words]
        subject = " ".join(subject_words)

        # Strip excessive whitespace
        subject = re.sub(r"\s+", " ", subject).strip()

        # Remove surrounding quotes if the whole subject was quoted
        if len(subject) >= 2 and subject.startswith('"') and subject.endswith('"'):
            subject = subject[1:-1]
        elif subject.startswith("'") and subject.endswith("'"):
            subject = subject[1:-1]

        # If subject is empty after cleaning, fall back to "unknown topic"
        if not subject:
            return "unknown topic"

        return subject

    def _extract_quoted_phrases(self, raw_input: str, query: StructuredQuery):
        """Extract exact phrases from quoted strings in the original input."""
        # Find ALL quoted phrases in the original (non-lowercased) input
        matches = re.findall(r'"([^"]*)"', raw_input)
        if matches:
            # Use the LAST exact phrase found as the subject if no subject yet
            # (the first quoted phrase may be the subject itself, the last is the --exact phrase)
            if not query.subject:
                query.subject = matches[-1]
            # Store the last quoted phrase as exact_phrase
            query.exact_phrase = matches[-1]

    def _normalize_query(self, query: StructuredQuery):
        """Normalize and validate the structured query."""
        # Ensure subject has something meaningful
        if not query.subject or query.subject.lower() in {
            "unknown topic", "unknown", ""
        }:
            # Try the exact phrase
            if query.exact_phrase:
                query.subject = query.exact_phrase
            # Fallback to required phrases
            elif query.required_phrases:
                query.subject = " ".join(query.required_phrases[:3])
            else:
                query.subject = "research topic"

        # Deduplicate phrases
        query.required_phrases = list(set(query.required_phrases))
        query.optional_phrases = list(set(query.optional_phrases))
        query.excluded_phrases = list(set(query.excluded_phrases))

        # Trim whitespace from phrases
        query.required_phrases = [p.strip() for p in query.required_phrases if p.strip()]
        query.optional_phrases = [p.strip() for p in query.optional_phrases if p.strip()]
        query.excluded_phrases = [p.strip() for p in query.excluded_phrases if p.strip()]

        # Normalize content type values
        normalized_types = []
        for t in query.content_types:
            if t and t not in normalized_types:
                normalized_types.append(t)
        query.content_types = normalized_types

        # Set default max_depth if deep is enabled and max_depth not set
        if query.deep and query.max_depth == 0:
            query.max_depth = 3


# ---------------------------------------------------------------------------
# Query Parser Factory / CLI Integration
# ---------------------------------------------------------------------------

def build_query_from_cli(args) -> StructuredQuery:
    """
    Build a StructuredQuery from CLI argument namespace.
    This bridges the gap between the CLI and the natural-language query engine.
    """
    query = StructuredQuery()

    # Map CLI args to query fields
    if hasattr(args, 'phrase') and args.phrase:
        query.exact_phrase = args.phrase
        query.subject = args.phrase

    if hasattr(args, 'literal') and args.literal:
        # Literal substring becomes a required phrase
        query.required_phrases.append(args.literal)

    if hasattr(args, 'regex') and args.regex:
        query.content_types.append(QueryOperator.REGEX.value)

    if hasattr(args, 'domain') and args.domain:
        query.domains = [args.domain]

    if hasattr(args, 'limit') and args.limit:
        query.max_results = args.limit

    if hasattr(args, 'case_sensitive') and args.case_sensitive:
        # Store case-sensitivity preference (handled at execution time)
        pass

    if hasattr(args, 'phrase') and args.phrase:
        # If --phrase is used, treat subject as the phrase
        query.subject = args.phrase

    return query


def interpret_natural_language(query_text: str) -> StructuredQuery:
    """
    High-level function: interpret a natural-language query string.

    This is the main entry point for both CLI and GUI usage.
    """
    parser = NaturalLanguageParser()
    return parser.parse(query_text)