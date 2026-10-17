# TODO

- [x] **Entry Detail & Edit Screens**: Implement `EntryDetailView` (`/entries/<id>`) with media preview, voting, tags editing, read-later toggle, status controls, and `EntryEditScreen` (`/entries/new`, `/entries/<id>/edit`).
- [ ] **Entry Rules & URL Preview**: Implement `EntryRulesScreen` (`/rules`) for URL regex rules (block, trust, auto-tag) and `UrlPreview` (`/preview`) to verify whether links are blocked by rules.
- [ ] **Data Import & Export**: Implement OPML import/export for sources and JSON/link lists import/export for database entries.
- [ ] **Remote Database Download**: Provide functionality to download and replace the active SQLite database from a remote URL.
- [ ] **UI Polish & Bug Fixes**: Address initial search filter layout and clarify worker/online status indicators (from `BUGS.md`).
 - link validation / sanitization
 - link batch operations (delete?)
 - search views - ability to add / edit search views
 - implement entry builder, which checks if entry can be inserted (checks rules?)
 - provide docker compose script and Dockerfile
 - On hold - introduce system operations table
 - if database file is replaced, how thread should be restarted?
 - provide ability to block entries
 - provide ability to add many sources
 - provide ability to add many entries
 - provide dbupdate scripts
 - page properties tool
 - source list: order by errors


There is     JOB_LINK_UPDATE_DATA = "link-update-data" background job. We have a worker thread, currently it
  processes sources. If there are no jobs, it adds outdated jobs into queue, and starts processing them. When links
  are added this job is added. Thread processes this job by obtaining Url like in webtools_service.py (either
  BaseUrl, or RemoteUrl). Fetches BaseUrl.get_title(), BaseUrl.get_description() and updates entry(link) with these
  properties. You can refactor webtools_service.py. Update PROJECT.md if needed. Update ARCHITECTURE.md if needed.
