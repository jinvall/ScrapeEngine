# ScrapeEngine

A professional desktop research workstation for web scraping, content extraction, and intelligent research with natural language processing capabilities.

## Features

### Core Functionality
- **Web Scraping Engine** - Configurable crawler with depth control, domain restrictions, and robots.txt compliance
- **Content Extraction** - Structured HTML parsing, entity extraction, and metadata collection
- **Sitemap Discovery** - Automatic sitemap parsing and URL hierarchy mapping
- **Storage Management** - 5 GiB quota with FIFO eviction, content-addressed storage, and deduplication
- **Query Parsing** - Natural language query interpretation

### GUI (PySide6/Qt6)
- **Professional Desktop Interface** - Native Qt6 application with multiple workspaces
- **Natural Language Crawl Configuration** - Describe research objectives in plain English
- **Intelligent Crawling** - NLP-driven relevance scoring and link prioritization
- **Site Explorer** - Four synchronized views of site structure, URL hierarchy, link graphs, and inventory
- **Document & Entity Management** - Browse extracted content and identified entities
- **Storage Dashboard** - Real-time quota monitoring and usage analytics
- **Research Sessions** - Manage multiple research projects

### Natural Language Processing
- **Instruction Interpretation** - Automatically extracts keywords, priorities, and extraction goals from plain English
- **Relevance Scoring** - Ranks pages based on title, headings, content, and URL relevance
- **Smart Link Prioritization** - Follows most relevant links first
- **Deterministic Fallback** - Works without LLM dependencies

## Requirements

- Python 3.8+
- PySide6 (Qt6)
- Linux (tested on Ubuntu)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jinvall/scrawler.git
cd scrawler
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Launch GUI
```bash
./venv/bin/python launch_gui.py
```

Or:
```bash
./venv/bin/python gui/entrypoint.py
```

### Command Line Usage
```bash
python3 scrape_engine.py crawl https://example.com --max-pages 50 --max-depth 3
```

## Architecture

- `gui/` - PySide6/Qt6 desktop interface
- `scrape_engine.py` - Core crawling engine
- `extraction.py` - Content extraction and entity recognition
- `sitemap_module.py` - Sitemap parsing and URL hierarchy
- `storage_manager.py` - Content-addressed storage with quotas
- `query_parser.py` - Natural language query parsing
- `crawl_nlp.py` - NLP processing for crawl instructions
- `crawl_controller.py` - Crawl orchestration

## Configuration

- Storage quota: 5 GiB (configurable in storage_manager)
- Database: SQLite (`crawl_database.sqlite`)
- User config: `~/.kilo/crawl_config.json`

## License

See repository for license information.
# scrawler
