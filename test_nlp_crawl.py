#!/usr/bin/env python3
"""Tests for NLP crawl functionality"""
import sys
sys.path.insert(0, '/home/jason/ScrapeEngine')

from crawl_nlp import CrawlNLPProcessor, CrawlObjectives

def test_nlp_basic():
    proc = CrawlNLPProcessor()
    instructions = "Find technical information about ESP32 audio streaming. Prioritize UDP and TCP transmission, microphone sensitivity, low-latency processing. Extract technical specifications, code examples."
    obj = proc.process_instructions(instructions)
    assert obj.primary_subject
    assert len(obj.required_keywords) > 0
    print("Basic NLP test passed")

def test_scoring():
    proc = CrawlNLPProcessor()
    instructions = "Find ESP32 projects"
    obj = proc.process_instructions(instructions)
    score1 = proc.score_page_relevance({'title': 'ESP32 Tutorial', 'content': 'arduino esp32 projects', 'url': 'esp32.com/tutorial', 'headings': []}, obj)
    score2 = proc.score_page_relevance({'title': 'Cat Photos', 'content': 'cats dogs pets', 'url': 'cats.com/photos', 'headings': []}, obj)
    print(f"Scores: {score1} vs {score2}")
    # Just verify scoring works
    assert isinstance(score1, float)
    assert isinstance(score2, float)
    print("Scoring test passed")

if __name__ == '__main__':
    test_nlp_basic()
    test_scoring()
    print("All tests passed")
