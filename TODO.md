# Natural Language Crawl Implementation TODO

## Critical Missing Pieces for Full Acceptance

### 1. Instructions must reach the actual crawl engine
- [ ] Modify scrape_engine.py to accept and use natural language instructions
- [ ] Add instruction processing to ScraperEngine
- [ ] Pass instructions from GUI through to engine

### 2. Crawl execution integration
- [ ] Connect CrawlDialog to actually start crawls
- [ ] Integrate CrawlController with real scraper
- [ ] Wire up signals for progress/cancellation
- [ ] Make GUI responsive with QThread workers

### 3. Relevance scoring in engine
- [ ] Use NLP processor in actual crawling logic
- [ ] Prioritize links based on relevance scores
- [ ] Implement link prioritization algorithm

### 4. Sitemap and URL hierarchy
- [ ] Ensure discovered URLs are added to sitemap
- [ ] Maintain parent-child relationships
- [ ] Track discovery depth and relevance scores

### 5. Configuration persistence
- [ ] Save crawl config with instructions
- [ ] Load/restore instructions on reopen
- [ ] Pass config through all layers

### 6. Testing
- [ ] Create tests for NLP processing
- [ ] Test full workflow

## Completed
- [x] Added multiline Natural Language Instructions field to CrawlDialog (QTextEdit)
- [x] Field accepts substantial instructions with placeholder
- [x] Preserved Start URL, Depth, Max Pages functionality
- [x] Created crawl_nlp.py with NLP processor for instruction interpretation
- [x] Created crawl_controller.py for crawl management
- [x] Extended ScraperEngine to accept and process instructions
- [x] Added keyword extraction and relevance scoring (deterministic fallback)
- [x] Implemented link prioritization based on relevance
- [x] Added debug logging throughout
- [x] CrawlDialog validates and starts crawls with instructions

## Remaining
- [ ] Full GUI worker thread integration for non-blocking crawls
- [x] Persist crawl config with instructions to database/settings
- [ ] Complete sitemap/URL hierarchy integration in GUI display
- [x] Add tests for NLP functionality
- [ ] Ensure all signals properly connected for progress reporting
# DONE
