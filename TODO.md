# TODO

 - [x] entry list screen
 - [x] sources list screen
 - [x] database screen
 - [x] configuration screen
 - [x] jobs screen
 - [x] logs screen
 - [x] **Entry Detail & Edit Screens**: Implement `EntryDetailView` (`/entries/<id>`) with media preview, voting, tags editing, read-later toggle, status controls, and `EntryEditScreen` (`/entries/new`, `/entries/<id>/edit`).
 - [x] link source process job
 - [x] **Link Update Data Background Job**: `JOB_LINK_UPDATE_DATA = "link-update-data"` enqueued when links are added by user, worker thread fetches BaseUrl/RemoteUrl title and description and updates entry metadata.
- [ ] **Entry Rules & URL Preview**: Implement `EntryRulesScreen` (`/rules`) for URL regex rules (block, trust, auto-tag) and `UrlPreview` (`/preview`) to verify whether links are blocked by rules.
- [ ] **Data Import & Export**: Implement OPML import/export for sources and JSON/link lists import/export for database entries.
- [ ] **Remote Database Download**: Provide functionality to download and replace the active SQLite database from a remote URL.
- [ ] **UI Polish & Bug Fixes**: Address initial search filter layout and clarify worker/online status indicators (from `BUGS.md`).
 - link validation / sanitization - is it fully implemented?
 - link batch operations (delete?)
 - search views - ability to add / edit search views
 - provide docker compose script and Dockerfile
 - On hold - introduce system operations table
 - if database file is replaced, how thread should be restarted?
 - provide ability to block entries (blockentries tbale)
 - provide ability to add many sources
 - provide dbupdate scripts
 - page properties tool
 - source list: order by errors
 - user should be able to trigger link update
 - link update job updates title, and description. should update much more

 - do not fallback on beautiful soup
Webtools service. Do not fall back on response, nor to use beautiful soup. Either BaseUrl/RemoteUrl works, or not.
  Please. I think webtools_service.py needs to be updated. Also PROJECT.md should be clear about it. webtoolkit was
  introduced to provide parsing and reading of titles and descriptions.

 - source detail fetch update should create a job link-update
