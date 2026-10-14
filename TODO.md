# TODO

- [ ] **Entry Detail & Edit Screens**: Implement `EntryDetailView` (`/entries/<id>`) with media preview, voting, tags editing, read-later toggle, status controls, and `EntryEditScreen` (`/entries/new`, `/entries/<id>/edit`).
- [ ] **Configuration View & Settings**: Add `ConfigurationView` (`/configuration`) and navbar button to manage display styles (standard, gallery, content-centric, search engine, links-only) and user preferences.
- [ ] **Entry Rules & URL Preview**: Implement `EntryRulesScreen` (`/rules`) for URL regex rules (block, trust, auto-tag) and `UrlPreview` (`/preview`) to verify whether links are blocked by rules.
- [ ] **Data Import & Export**: Implement OPML import/export for sources and JSON/link lists import/export for database entries.
- [ ] **Remote Database Download**: Provide functionality to download and replace the active SQLite database from a remote URL.
- [ ] **UI Polish & Bug Fixes**: Address initial search filter layout and clarify worker/online status indicators (from `BUGS.md`).
 - implement entry builder, which checks if entry can be inserted (checks rules?)
 - On hold - introduce system operations table
