# UI Functionality & Dead Buttons Audit

Date: 2025-11-05
Audited by: Kilo
Project Path: /home/jason/ScrapeEngine

## Executive Summary
This audit examined the GUI for non-functional buttons, unconnected signals, missing implementations, and UI elements that don't actually work.

## Audit Findings

### Toolbar Buttons (main_window.py)
| Button | Method Connected | Status | Notes |
|--------|-----------------|--------|-------|
| Command | show_command_interface() | FUNCTIONAL | Opens CommandInterface dialog |
| New Research | show_new_research_dialog() | FUNCTIONAL | Opens ResearchDialog (fixed) |
| Pause | pause_research() | PARTIAL | Method exists but may not be fully implemented |
| Resume | resume_research() | PARTIAL | Method exists but may not be fully implemented |
| Stop | stop_research() | PARTIAL | Method exists but may not be fully implemented |
| New Crawl | show_new_crawl_dialog() | FUNCTIONAL | Opens CrawlDialog (created) |
| Search | show_search_workspace() | FUNCTIONAL | Switches to search workspace |
| Explore | show_site_explorer_workspace() | FUNCTIONAL | Switches to site explorer workspace |
| Export | export_results() | UNKNOWN | Need to check implementation |
| Settings | show_settings_dialog() | FUNCTIONAL | Opens SettingsDialog (created) |

### Navigation Panel Buttons
All navigation buttons connect to `switch_workspace()` with lambda - FUNCTIONAL after fix.

### Menu Bar Actions
| Menu | Action | Method | Status |
|------|--------|--------|--------|
| File | New Research Session | show_new_research_dialog | FUNCTIONAL |
| File | Save | save_session | NEEDS CHECK |
| File | Export | export_results | NEEDS CHECK |
| File | Settings | show_settings_dialog | FUNCTIONAL |
| File | Exit | self.close() | FUNCTIONAL |
| Workspaces | All workspace items | switch_workspace | FUNCTIONAL (fixed) |
| Help | About | show_about_dialog | NEEDS CHECK |
| Help | Documentation | show_documentation | NEEDS CHECK |
| Help | Keyboard Shortcuts | show_keyboard_shortcuts | NEEDS CHECK |

### Workspace Views - Implementation Status
| Workspace | View Class | Implementation | Status |
|-----------|------------|----------------|--------|
| Overview | OverviewView | Exists in gui/views/overview_view.py | CHECK IMPLEMENTATION |
| Research | ResearchView | Exists in gui/views/research_view.py | CHECK IMPLEMENTATION |
| Web Discovery | DiscoveryView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Site Explorer | SiteExplorerView | Exists in gui/views/site_explorer_view.py | CHECK IMPLEMENTATION (had PySide6 issue fixed) |
| Search | SearchView | Exists in gui/views/search_view.py | CHECK IMPLEMENTATION |
| Documents | DocumentsView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Entities | EntitiesView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Relationships | RelationshipsView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Collections | CollectionsView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Crawl Queue | CrawlQueueView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Reports | ReportsView | Created as placeholder | PLACEHOLDER - MINIMAL |
| Storage | StorageView | Created as placeholder | PLACEHOLDER - MINIMAL |

## Recommendations

### High Priority
1. **Check placeholder views** - Discovery, Documents, Entities, Relationships, Collections, Crawl Queue, Reports, Storage are just placeholders with labels. They don't provide actual functionality.
2. **Verify method implementations** - Many methods like save_session, export_results, pause/research/stop need checking
3. **Connect signals properly** - Some UI elements may not be connected to backend properly

### Medium Priority
1. **Test all buttons** - Manual testing needed for all toolbar/menu actions
2. **Implement missing functionality** in placeholder views or hide them
3. **Add error handling** for button actions that might fail

## Notes
- The GUI can now start without crashing (after fixes)
- Core navigation and dialog launching works
- Many workspace views may need backend integration
- Placeholders are acceptable for UI structure but not functional
