"""
Natural Language Processing for Crawl Configuration
Translates user instructions into actionable crawl criteria
"""

import re
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field


@dataclass
class CrawlObjectives:
    """Structured crawl objectives derived from natural language instructions."""
    primary_subject: str = ""
    secondary_topics: List[str] = field(default_factory=list)
    required_keywords: List[str] = field(default_factory=list)
    optional_keywords: List[str] = field(default_factory=list)
    extract_info: List[str] = field(default_factory=list)
    preferred_content_types: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    link_priorities: List[str] = field(default_factory=list)
    output_structure: Dict[str, Any] = field(default_factory=dict)
    raw_instructions: str = ""


class CrawlNLPProcessor:
    """Process natural language crawl instructions."""
    
    def __init__(self):
        self.keyword_patterns = [
            r'\b(find|search for|get|collect|extract|gather|locate)\b',
            r'\b(prioritize|focus on|look for|want|need)\b',
            r'\b(exclude|avoid|skip|ignore)\b',
        ]
        
    def process_instructions(self, instructions: str) -> CrawlObjectives:
        """Translate natural language instructions into structured objectives."""
        objectives = CrawlObjectives(raw_instructions=instructions)
        
        if not instructions or not instructions.strip():
            return objectives
        
        instructions_lower = instructions.lower()
        
        # Extract primary subject (often after "find about" or at beginning)
        primary_match = re.search(r'(?:find|search|about|information on|research)\s+([^.]+?)(?:\.|,|prioritize|extract|$)', 
                                  instructions, re.IGNORECASE)
        if primary_match:
            objectives.primary_subject = primary_match.group(1).strip()
        else:
            # Take first sentence as primary subject
            first_sentence = instructions.split('.')[0].strip()
            objectives.primary_subject = first_sentence
        
        # Extract required keywords (after prioritize, focus on)
        required_section = re.findall(r'(?:prioritize|focus on|required|must have|need)\s+([^.]+)', 
                                     instructions, re.IGNORECASE)
        for section in required_section:
            keywords = self._extract_keywords(section)
            objectives.required_keywords.extend(keywords)
            objectives.link_priorities.extend(keywords)
        
        # Extract what to extract
        extract_section = re.findall(r'extract\s+([^.]+)', instructions, re.IGNORECASE)
        for section in extract_section:
            objectives.extract_info.append(section.strip())
            keywords = self._extract_keywords(section)
            objectives.required_keywords.extend(keywords)
        
        # Extract exclusions
        exclude_section = re.findall(r'(?:exclude|avoid|skip)\s+([^.]+)', instructions, re.IGNORECASE)
        for section in exclude_section:
            objectives.exclude_patterns.append(section.strip())
            keywords = self._extract_keywords(section)
            objectives.exclude_patterns.extend(keywords)
        
        # General keyword extraction
        all_keywords = self._extract_keywords(instructions)
        # Filter out common words and add to required if not already there
        for kw in all_keywords:
            if kw not in [k.lower() for k in objectives.required_keywords]:
                if len(kw) > 3:  # Only meaningful keywords
                    objectives.optional_keywords.append(kw)
        
        # Deduplicate
        objectives.required_keywords = list(set(objectives.required_keywords))
        objectives.optional_keywords = list(set(objectives.optional_keywords))
        objectives.secondary_topics = list(set(objectives.secondary_topics))
        
        return objectives
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words and extract noun phrases
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                      'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were',
                      'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 
                      'did', 'will', 'would', 'could', 'should', 'may', 'might',
                      'can', 'this', 'that', 'these', 'those', 'from', 'as'}
        
        # Extract word tokens
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        
        # Also extract hyphenated terms
        hyphenated = re.findall(r'\b[a-zA-Z]+-[a-zA-Z]+\b', text.lower())
        keywords.extend(hyphenated)
        
        return keywords
    
    def score_page_relevance(self, page_data: Dict[str, Any], objectives: CrawlObjectives) -> float:
        """Calculate relevance score for a page."""
        score = 0.0
        title = page_data.get('title', '').lower()
        content = page_data.get('content', '').lower()
        url = page_data.get('url', '').lower()
        headings = ' '.join(page_data.get('headings', [])).lower()
        
        # Title relevance (high weight)
        for kw in objectives.required_keywords:
            if kw in title:
                score += 10.0
        for kw in objectives.optional_keywords:
            if kw in title:
                score += 3.0
        
        # Headings relevance
        for kw in objectives.required_keywords:
            if kw in headings:
                score += 5.0
        for kw in objectives.optional_keywords:
            if kw in headings:
                score += 2.0
        
        # Content relevance
        for kw in objectives.required_keywords:
            count = content.count(kw)
            score += min(count * 2.0, 20.0)  # Cap content score
        for kw in objectives.optional_keywords:
            count = content.count(kw)
            score += min(count * 0.5, 5.0)
        
        # URL relevance
        for kw in objectives.required_keywords:
            if kw in url:
                score += 3.0
        for kw in objectives.link_priorities:
            if kw in url:
                score += 2.0
        
        # Primary subject
        if objectives.primary_subject:
            primary_words = self._extract_keywords(objectives.primary_subject)
            for pw in primary_words:
                if pw in title:
                    score += 8.0
                if pw in content:
                    score += 1.0
        
        return score
