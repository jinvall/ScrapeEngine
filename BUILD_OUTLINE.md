# GUI IMPLEMENTATION DIRECTIVE
## Qt6 / PySide6 Desktop Research Workstation

**This directive is mandatory. Implement the GUI using Qt6 and PySide6.**

The previous GUI implementation choice of Tkinter is rejected.

Do not use Tkinter.
Do not use CustomTkinter.
Do not use a Tk-based compatibility layer.
Do not substitute another GUI framework.
Do not create a web-based GUI.
Do not implement a Flask server or browser dashboard.

The required GUI framework is **PySide6 (Qt6)**.

This is a desktop application running natively on Linux.

---

# 1. Objective

Implement a polished, fully functional desktop GUI for the existing web research, scraping, extraction, sitemap discovery, entity intelligence, and search engine.

This is not a prototype or visual demonstration.

Every control must connect to actual application functionality.

The GUI must provide an integrated research environment where the user can:

- Enter natural-language research and scrape commands.
- Search the web through multiple configured providers.
- Explore websites and their sitemap hierarchies.
- Inspect complete URL structures.
- View internal-link relationships.
- Control crawling and collection.
- Search retained content.
- Inspect extracted details.
- Investigate entities and relationships.
- Manage research sessions.
- Monitor storage consumption and FIFO eviction.
- Generate reports.
- Resume interrupted operations.

The GUI must communicate with the existing backend through defined service interfaces.

Do not duplicate backend functionality inside the GUI.

# 2. Technology requirements

Required:

- Python.
- PySide6.
- Qt6.
- Qt Model/View architecture.
- Qt signals and slots.
- QThreadPool and QRunnable for suitable background operations.
- QSettings for appropriate interface preferences.
- QSplitter for adjustable workspace layouts.
- QDockWidget for configurable panels.
- QTreeView for hierarchical data.
- QTableView for searchable inventories.
- QSortFilterProxyModel for filtering and sorting.
- QAbstractItemModel subclasses where appropriate.

Use existing project dependencies when practical.

Do not introduce unnecessary heavyweight dependencies.

The application must work on a CPU-only Linux system.

# 3. Architecture

Keep the GUI separate from the scraping and research engine.

Required architectural separation:

    Application
        |
        +-- Main Window
        |
        +-- Navigation / Workspace Manager
        |
        +-- GUI Views and Models
        |
        +-- GUI Controllers
        |
        +-- Backend Service Interfaces
                |
                +-- Research Service
                +-- Search Service
                +-- Crawl Service
                +-- Sitemap Service
                +-- URL Hierarchy Service
                +-- Extraction Service
                +-- Entity Service
                +-- Document Service
                +-- Storage Service
                +-- Report Service

Adapt this architecture to the existing repository.

Do not create fake backend implementations to make the GUI appear functional.

If a required backend service does not yet exist, implement a clearly defined interface and report the missing implementation. Do not fabricate results.

All long-running work must execute outside the GUI thread.

The GUI thread must never perform blocking network requests, large document extraction, database scans, or lengthy filesystem operations.

Use Qt signals to report progress and completion.

All UI updates must occur safely through Qt's event system.

# 4. Main application window

Create a professional desktop application with:

- Main menu.
- Toolbar.
- Persistent left navigation.
- Central workspace.
- Optional right-side contextual panel.
- Status bar.
- Background job indicator.
- Storage usage indicator.

Use QMainWindow as the application foundation.

Use QDockWidget where appropriate so users can rearrange panels.

Use QSplitter to allow resizing.

Persist window geometry, dock positions, splitter positions, and appropriate user preferences.

The interface must be readable at different screen resolutions.

Provide adjustable interface scaling and font sizes.

Use clear labels and sufficiently large controls. Do not rely on tiny icons or color alone to communicate functionality.

# 5. Main navigation

Create these workspaces:

1. Overview
2. Research
3. Web Discovery
4. Site Explorer
5. Search
6. Documents
7. Entities
8. Relationships
9. Collections
10. Crawl Queue
11. Reports
12. Settings

Each workspace must have its own functional view.

Navigation must not destroy active research sessions or lose unsaved query settings.

# 6. Overview workspace

Display:

- Active research sessions.
- Recent research.
- Active crawl jobs.
- Pending URLs.
- Recently discovered sources.
- Recent extraction activity.
- Storage consumption.
- Available storage.
- Recent errors.
- System activity.

Provide quick actions:

- New research.
- New scrape.
- Search content.
- Explore a website.
- Inspect sitemap.
- Resume previous research.

All displayed figures must come from actual backend data.

# 7. Universal command/search interface

Create a prominent command entry field.

It must accept natural-language commands such as:

    Research Ursula K. Le Guin

    Scrape ESP32 firmware documentation containing OTA
    and partition table.

    Find articles about Linux audio streaming mentioning
    UDP latency and jitter buffers.

    Explore example.org and map its sitemap hierarchy.

    Find all documents containing the exact phrase
    "firmware rollback".

Provide contextual suggestions and example commands.

Support keyboard activation.

The command interface must use the same query parser as the CLI.

### 7.1 Query interpretation preview

Before execution, show:

- Subject.
- Search terms.
- Required phrases.
- Excluded phrases.
- Content types.
- Selected providers.
- Domain restrictions.
- Date restrictions.
- Crawl depth.
- Extraction profile.
- Retention profile.

Allow editing before execution.

Provide explicit Start, Cancel, and Clear actions.

Do not silently ignore unsupported query conditions.

# 8. Research workspace

Provide a dedicated research interface.

Include:

- Subject or topic input.
- Research profile selector.
- Provider selection.
- Topic selection.
- Domain restrictions.
- Source preferences.
- Primary-source preference.
- Date range.
- Relevance threshold.
- Discovery depth.
- Extraction profile.

Display research results in a structured layout.

Recommended sections:

- Overview.
- Sources.
- Findings.
- Publications.
- Related entities.
- Evidence.
- Conflicting claims.
- Outstanding questions.
- Research history.

Provide pause, resume, cancel, and report generation.

Preserve research session state.

# 9. Site Explorer

This is a major feature and must receive substantial implementation attention.

Create four synchronized views.

## 9.1 Domain and Sitemap Tree

Use QTreeView.

Display:

- Root domain.
- Subdomains.
- Sitemap indexes.
- Nested sitemaps.
- Sitemap entries.
- URL counts.
- Crawl status.

Support expanding and collapsing branches.

## 9.2 URL Path Tree

Display the actual URL path hierarchy.

Example:

    example.org
      /docs
        /api
          /authentication
          /devices
          /reference
        /guides
        /tutorials
      /blog
        /2026
        /2025
      /downloads
        /firmware
        /manuals

The tree must be generated from actual discovered URLs.

Do not fabricate directory relationships.

## 9.3 Internal-Link Graph

Display actual page relationships.

Support:

- Incoming links.
- Outgoing links.
- Related pages.
- Orphan pages.
- Highly connected pages.
- Breadcrumb relationships.
- Canonical relationships.

Use an appropriate Qt graphics/view architecture or an established compatible visualization library.

Do not make graph rendering a blocking GUI operation.

Provide controls to limit the displayed graph to selected branches or nodes.

## 9.4 URL Inventory

Use QTableView with filtering and sorting.

Columns:

- URL.
- Title.
- Domain.
- Path.
- Parent.
- Discovery method.
- Sitemap membership.
- Content type.
- Last modified.
- First discovered.
- Last checked.
- Crawl status.
- Extraction status.
- Relevance.
- HTTP status.
- Canonical URL.
- Language.
- Stored size.

Allow column visibility and sensible resizing.

Provide context actions:

- Open source.
- Inspect URL.
- View extracted content.
- View incoming links.
- View outgoing links.
- Queue for crawling.
- Exclude from crawling.
- Copy URL.
- View discovery history.

Selecting an item in any Site Explorer view must synchronize the other views wherever a real relationship exists.

Do not confuse URL path ancestry with actual internal-link relationships.

# 10. Search workspace

Create a full search interface.

Search modes:

- Exact phrase.
- Literal substring.
- All terms.
- Any terms.
- Boolean.
- Whole word.
- Regex.
- Proximity.
- Fuzzy.
- Entity.
- Detail type.

Filters:

- Domain.
- Date.
- Content type.
- Research session.
- Collection.
- Entity type.
- Extraction type.
- Relevance.

Results must show:

- Title.
- Source URL.
- Relevant excerpt.
- Highlighted matches.
- Section heading.
- Match count.
- Capture date.
- Content type.
- Relevance score.

Provide a readable document preview.

Search must operate against retained content without refetching websites.

Literal substring results must be verified against actual text.

# 11. Documents workspace

Provide a searchable document inventory.

Display:

- Document title.
- URL.
- File type.
- Source domain.
- Capture date.
- Modification date.
- Original size.
- Stored size.
- Compression.
- Fingerprint.
- Extraction status.

Selecting a document should open a structured preview.

Support separate views for:

- Extracted text.
- Sections.
- Tables.
- Code.
- Metadata.
- Entities.
- Relationships.
- Original source information.

Do not flatten structured documents into one unformatted text display.

# 12. Entity workspace

Provide:

- Entity search.
- Entity type filtering.
- Alias display.
- Entity details.
- Source mentions.
- Related entities.
- Relationships.
- Evidence.
- Confidence.
- Explicit/inferred status.

Selecting an entity should show its actual mentions across retained documents.

Allow navigation from an entity to its source document and exact occurrence.

Do not merge distinct entities simply because their names are similar.

# 13. Relationships workspace

Provide a searchable relationship inventory.

Display:

- Source entity.
- Relationship type.
- Target entity.
- Source document.
- Supporting evidence.
- Confidence.
- Explicit/inferred status.

Provide an interactive relationship graph where practical.

Allow filtering by relationship type and entity category.

Do not present unsupported or inferred relationships as verified facts.

# 14. Collections workspace

Allow users to create and manage collections.

Collections may contain:

- Research sessions.
- Documents.
- URLs.
- Entities.
- Search results.
- Reports.

Support:

- Create.
- Rename.
- Add.
- Remove.
- Search.
- Export.
- Protect from FIFO eviction where supported.

Collection management must not duplicate the underlying content blobs.

# 15. Crawl Queue workspace

Display:

- Pending.
- Active.
- Completed.
- Failed.
- Skipped.
- Retained.
- Rejected.

Provide:

- Start.
- Pause.
- Resume.
- Cancel.
- Retry.
- Clear completed jobs.
- Inspect errors.

Display:

- URL.
- Domain.
- Discovery source.
- Queue priority.
- Relevance.
- Content profile.
- Current status.
- Progress.
- Last error.

Queue actions must use actual backend job controls.

# 16. Storage workspace

The application has a hard persistent storage ceiling of 5 GiB.

Provide a prominent storage dashboard.

Display:

- Total used.
- Maximum allowed.
- Remaining.
- Usage by category.
- Database size.
- Index size.
- Blob size.
- Attachment size.
- Report size.
- Compression savings.
- Duplicate storage avoided.
- Current reservations.
- FIFO eviction history.

Provide a readable storage breakdown.

Warn when approaching the soft operational threshold.

The GUI must not implement its own storage accounting. It must display values supplied by the centralized backend storage manager.

Never allow the GUI to bypass quota enforcement.

# 17. Reports workspace

Provide report generation for:

- Research dossiers.
- Website inventories.
- Sitemap hierarchies.
- URL inventories.
- Entity reports.
- Relationship reports.
- Search results.
- Crawl summaries.
- Storage summaries.

Support appropriate export formats:

- Markdown.
- JSON.
- CSV.
- HTML.
- PDF where supported.

Allow users to select report scope and destination.

Do not silently overwrite existing reports.

# 18. Settings

Provide settings for:

- Search providers.
- Provider API keys.
- Default research profile.
- Default collection profile.
- Crawl limits.
- Concurrent jobs.
- Request delays.
- Download size limits.
- Extraction limits.
- Storage ceiling.
- FIFO retention settings.
- Interface appearance.
- Font scaling.
- Keyboard shortcuts.
- Logging.

Never display complete API secrets after initial entry.

Use secure secret handling appropriate to the existing application architecture.

Do not store secrets in source code.

# 19. Background processing and responsiveness

Use Qt's worker infrastructure.

Implement workers for:

- Search provider requests.
- Sitemap retrieval.
- Sitemap parsing.
- URL discovery.
- Page retrieval.
- Content extraction.
- Entity extraction.
- Document processing.
- Report generation.

Workers must communicate through signals.

Do not manipulate widgets directly from worker threads.

Provide progress updates where meaningful.

Allow cancellation where the backend operation supports it.

Limit concurrency and memory consumption.

Do not launch unlimited workers.

The application must remain responsive while research and crawling are running.

# 20. Visual design

The interface should look like a professional research and data-analysis application.

Avoid:

- Default Tk-style layouts.
- Generic form-heavy interfaces.
- Tiny labels.
- Excessive decorative elements.
- Oversized empty panels.
- Unnecessary animations.
- Excessive gradients.
- Placeholder charts.
- Decorative controls that do nothing.

Use:

- Clear visual hierarchy.
- Readable typography.
- Adjustable font scaling.
- Consistent spacing.
- High-contrast text.
- Clearly labeled controls.
- Consistent tables.
- Distinct active and inactive states.
- Context-sensitive actions.
- Professional light and dark themes.

The interface should feel cohesive across all workspaces.

# 21. Application reliability

Implement:

- Clean application startup.
- Configuration loading.
- Database connection lifecycle.
- Graceful shutdown.
- Background worker cleanup.
- Exception handling.
- Logging.
- Recovery after interrupted operations.
- Persistent window preferences.
- Safe cancellation.

A GUI crash must not corrupt the research database or leave the storage manager in an inconsistent state.

Do not terminate background workers abruptly when normal cancellation is possible.

# 22. Implementation and integration rules

Before implementation:

1. Inspect the actual repository.
2. Identify existing backend services.
3. Identify existing GUI code.
4. Identify existing database interfaces.
5. Identify existing CLI commands.
6. Determine the correct integration points.
7. Report any architectural conflicts.

Then implement the Qt6 GUI.

Do not rewrite working backend code merely to accommodate the GUI.

Create service adapters where necessary.

Do not invent backend methods and pretend they exist.

Do not substitute sample data for real results.

Do not leave buttons disconnected.

Do not leave placeholder screens masquerading as finished features.

If a backend capability is incomplete, make that status visible and identify the missing integration.

# 23. Suggested GUI package organization

Adapt names to the existing repository:

    gui/
        __init__.py
        main.py
        main_window.py

        core/
            application.py
            service_registry.py
            settings.py
            signals.py

        models/
            research_model.py
            search_model.py
            document_model.py
            entity_model.py
            relationship_model.py
            sitemap_model.py
            url_tree_model.py
            crawl_queue_model.py

        views/
            overview_view.py
            research_view.py
            discovery_view.py
            site_explorer_view.py
            search_view.py
            documents_view.py
            entities_view.py
            relationships_view.py
            collections_view.py
            crawl_queue_view.py
            reports_view.py
            settings_view.py

        widgets/
            command_bar.py
            query_preview.py
            result_viewer.py
            document_preview.py
            storage_indicator.py
            progress_panel.py
            filter_panel.py

        workers/
            worker.py
            worker_manager.py

        styles/
            light.qss
            dark.qss

This is a suggested organization, not permission to duplicate existing modules.

# 24. Required deliverables

Provide:

1. Fully implemented PySide6 GUI.
2. Actual application entry point.
3. Backend integration.
4. Functional navigation.
5. Functional search and command interface.
6. Research workspace.
7. Four synchronized Site Explorer views.
8. Document and entity workspaces.
9. Crawl queue controls.
10. Storage dashboard.
11. Settings and persistence.
12. Light and dark themes.
13. Keyboard shortcuts.
14. Installation and launch instructions.
15. GUI tests.
16. Integration test results.
17. List of incomplete backend dependencies.

Provide exact file paths for all created and modified files.

Provide the exact command to launch the GUI.

# 25. Acceptance criteria

The GUI is not complete until:

- The application launches using PySide6.
- No Tkinter dependency exists.
- All major workspaces open.
- Navigation preserves active state.
- Natural-language commands produce editable previews.
- Search executes real backend queries.
- Research starts and displays actual results.
- Research can be paused and resumed.
- Sitemap hierarchy is visible.
- URL path hierarchy is visible.
- Internal-link relationships are separately represented.
- Selecting URLs synchronizes the explorer views.
- Documents display structured extracted content.
- Entity searches return actual extracted entities.
- Relationships show source evidence.
- Crawl jobs can be controlled.
- Storage usage reflects actual backend accounting.
- The 5 GiB storage limit cannot be bypassed.
- Background work does not freeze the GUI.
- Window preferences persist.
- The application shuts down safely.
- No visible control is merely decorative.

**Final requirement: Build a real Qt6 desktop research workstation. PySide6 is mandatory. Tkinter is explicitly prohibited.**
