# YAFR URL & Endpoint Specification

This document details the complete routing matrix for YAFR, encompassing both **HTML Page Views** and **RESTful JSON API Endpoints**.

---

## 1. HTML View Routes (Page Navigation)

| Route Path | HTTP Method | View / Screen | Purpose & Behavior | Offline Capable? |
| :--- | :--- | :--- | :--- | :--- |
| `/` or `/entries` | `GET` | **EntriesListView** | Default Google-like search view. If query is empty, displays a prominent centered search input. If query is present, displays search input at the top with results list, filter dropdown, and batch controls. | **Yes** |
| `/entries/<int:id>` | `GET` | **EntryDetailView** | Displays complete metadata for a single entry, video playback frame (if YouTube/video), vote widget, tags with edit icon, comments, and entry navigation transition pane. | **Yes** |
| `/entries/new` | `GET`, `POST` | **EntryEditScreen** | Form to manually create a new link entry. | **Yes** |
| `/entries/<int:id>/edit`| `GET`, `POST` | **EntryEditScreen** | Form to edit existing link entry metadata (title, URL, description, tags, author, language). | **Yes** |
| `/sources` | `GET` | **SourcesListView** | Displays list of sources (RSS/Email) with pull-to-refresh, refresh progress bar, search input, outdated red dot badges, and consecutive error badges. | **Yes** |
| `/sources/<int:id>` | `GET` | **SourceDetailScreen** | Displays detailed source metrics, operational hash status (`page_hash`, `body_hash`), fetch history, and fetch trigger button. | **Yes** |
| `/sources/new/rss` | `GET`, `POST` | **SourceRssEditScreen** | Form to add or edit an RSS source. | **Yes** |
| `/sources/<int:id>/edit-rss` | `GET`, `POST` | **SourceRssEditScreen** | Form to edit an existing RSS source. | **Yes** |
| `/sources/new/email` | `GET`, `POST` | **SourceEmailEditScreen** | Form to configure an IMAP Email source (server host, port, credentials). Saves credentials into `credentials` table. | **Yes** |
| `/sources/<int:id>/edit-email`| `GET`, `POST` | **SourceEmailEditScreen** | Form to edit an existing IMAP Email source. | **Yes** |
| `/sources/new/parse` | `GET`, `POST` | **SourceParseEditScreen** | Form to configure custom XPath/HTML parsing source. | **Yes** |
| `/sources/<int:id>/edit-parse`| `GET`, `POST` | **SourceParseEditScreen** | Form to edit an existing parse source. | **Yes** |
| `/credentials` | `GET` | **CredentialsScreen** | Displays and manages stored email/IMAP credentials. | **Yes** |
| `/jobs` | `GET` | **JobsView** | Displays table of background jobs, orderable by priority, date created, or error count, with type filters and pause/resume/delete actions. | **Yes** |
| `/logs` | `GET` | **LogsView** | Displays entries from `applogging` table, filterable by severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL). | **Yes** |
| `/rules` | `GET`, `POST` | **EntryRulesScreen** | Displays and configures URL regex rules (`trigger_rule_url`), actions (block, trust, auto-tag), and age limits. | **Yes** |
| `/database` | `GET` | **DatabaseView** | Displays database path, creation date, last refresh, row counts, cache clear buttons, and remote DB download form. | **Yes** |
| `/status` | `GET` | **StatusView** | Displays health of the application, background task runner status, active worker loops, and network connectivity state. | **Yes** |
| `/configuration` | `GET`, `POST` | **ConfigurationView** | Allows user to modify display styles (`style-light`, `style-dark`), display types (`standard`, `gallery`, etc.), alphas, and quotas. | **Yes** |
| `/about` | `GET` | **AboutScreen** | Displays application version, project links, and system environment info. | **Yes** |
| `/preview` | `GET` | **UrlPreview** | Dedicated link preview screen displaying metadata, embed player, and indicating if the URL is blocked by an entry rule. | **Yes** (embeds require internet) |

---

## 2. RESTful JSON API Endpoints

Following the project requirement to **"prefer having small server functions that return JSON data"**, all client-side interactions and background updates use lightweight JSON endpoints.

### 2.1 Entry API (`/api/entries`)

#### `GET /api/entries/search-history`
- **Purpose**: Provides autocomplete search query suggestions based on past queries stored in `SearchHistory`.
- **Query Parameters**:
  - `q` (string, optional): Search prefix substring.
  - `limit` (int, default `10`): Max suggestions to return.
- **Response**:
  ```json
  {
    "success": true,
    "suggestions": ["python tutorials", "sqlite performance", "yt-dlp tricks"]
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/vote`
- **Purpose**: Submits or updates a user rating vote (-100 to 100) for an entry.
- **Request Body**:
  ```json
  { "vote": 75 }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "page_rating_votes": 75,
    "message": "Vote recorded."
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/read-later`
- **Purpose**: Toggles Read Later bookmark status for an entry.
- **Request Body**: None (toggles state) or `{ "active": true }`.
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "is_read_later": true
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/mark-active`
- **Purpose**: Sets `manual_status_code = 200` (marking the entry as verified active).
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "manual_status_code": 200
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/mark-dead`
- **Purpose**: Sets `manual_status_code = 400` (marking the entry as dead, applying dead alpha styling).
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "manual_status_code": 400
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/update-data`
- **Purpose**: Enqueues or executes an immediate metadata refresh for the entry link via `webtoolkit`/`yt-dlp`.
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "job_id": 105,
    "message": "Link update queued."
  }
  ```
- **Offline Capable**: No (requires internet). Disabled if offline.

#### `POST /api/entries/<int:id>/reset-data`
- **Purpose**: Resets extracted metadata (hashes, description, thumbnails) back to raw state.
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "message": "Link data reset."
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/visit`
- **Purpose**: Records entry visit in `entryvisithistory` and logs navigation transition in `entrytransitionhistory` if navigated from a previous entry.
- **Request Body**:
  ```json
  { "from_entry_id": 39 }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "visit_count": 5
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/<int:id>/tags`
- **Purpose**: Updates tags for an entry. Updates `entrycompactedtags` and global `compactedtags` table.
- **Request Body**:
  ```json
  { "tags": ["python", "sqlite", "news"] }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "entry_id": 42,
    "tags": ["python", "sqlite", "news"]
  }
  ```
- **Offline Capable**: Yes.

#### `DELETE /api/entries/<int:id>`
- **Purpose**: Removes an entry and cascades deletion to dependent rows (`entrycompactedtags`, `socialdata`, `readlater`, `entryvisithistory`).
- **Response**:
  ```json
  {
    "success": true,
    "deleted_id": 42,
    "message": "Entry and associated data removed."
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/batch-delete`
- **Purpose**: Removes multiple selected entries in a single transaction.
- **Request Body**:
  ```json
  { "entry_ids": [10, 11, 15, 22] }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "deleted_count": 4
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/entries/mark-all-read`
- **Purpose**: Marks all entries in current search filter as read/visited.
- **Request Body**:
  ```json
  { "entry_ids": [10, 11, 15, 22] }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "updated_count": 4
  }
  ```
- **Offline Capable**: Yes.

---

### 2.2 Source API (`/api/sources`)

#### `POST /api/sources/<int:id>/fetch`
- **Purpose**: Triggers an immediate refresh/fetch of a specific source (RSS/Email).
- **Response**:
  ```json
  {
    "success": true,
    "source_id": 7,
    "status": "fetching",
    "message": "Fetch started."
  }
  ```
- **Offline Capable**: No (requires internet).

#### `POST /api/sources/<int:id>/disable`
- **Purpose**: Sets `enabled = False` on the source.
- **Response**:
  ```json
  {
    "success": true,
    "source_id": 7,
    "enabled": false
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/sources/<int:id>/enable`
- **Purpose**: Sets `enabled = True` on the source.
- **Response**:
  ```json
  {
    "success": true,
    "source_id": 7,
    "enabled": true
  }
  ```
- **Offline Capable**: Yes.

#### `DELETE /api/sources/<int:id>`
- **Purpose**: Removes a source and cascades deletion to `sourceoperationaldata`.
- **Response**:
  ```json
  {
    "success": true,
    "deleted_source_id": 7
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/sources/fetch-all`
- **Purpose**: Triggers a batch refresh for all outdated sources (`date_fetched > 1h`) or sources with consecutive errors.
- **Request Body**:
  ```json
  { "include_errors": true }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "queued_sources_count": 12,
    "message": "Batch refresh initiated."
  }
  ```
- **Offline Capable**: No (requires internet).

#### `GET /api/sources/refresh-status`
- **Purpose**: Returns progress data for the linear progress bar during source refresh operations.
- **Response**:
  ```json
  {
    "is_running": true,
    "total_sources": 12,
    "completed_sources": 5,
    "current_source_title": "Linux News Weekly",
    "percentage": 41.6,
    "errors_encountered": 0
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/sources/batch-delete`
- **Purpose**: Deletes multiple selected sources.
- **Request Body**:
  ```json
  { "source_ids": [2, 5, 8] }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "deleted_count": 3
  }
  ```
- **Offline Capable**: Yes.

---

### 2.3 Job API (`/api/jobs`)

#### `POST /api/jobs/create`
- **Purpose**: Adds a new background task to `backgroundjob`.
- **Request Body**:
  ```json
  {
    "job": "link-update-data",
    "subject": "https://example.com/item",
    "priority": 1,
    "args": "{\"download_media\": true}"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "job_id": 204
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/jobs/<int:id>/pause`
- **Purpose**: Pauses a pending job (`enabled = False`).
- **Response**:
  ```json
  {
    "success": true,
    "job_id": 204,
    "enabled": false
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/jobs/<int:id>/resume`
- **Purpose**: Resumes a paused job (`enabled = True`).
- **Response**:
  ```json
  {
    "success": true,
    "job_id": 204,
    "enabled": true
  }
  ```
- **Offline Capable**: Yes.

#### `DELETE /api/jobs/<int:id>`
- **Purpose**: Removes a job from the queue.
- **Response**:
  ```json
  {
    "success": true,
    "deleted_job_id": 204
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/jobs/batch-action`
- **Purpose**: Executes pause, resume, or delete across multiple selected jobs.
- **Request Body**:
  ```json
  {
    "job_ids": [101, 102],
    "action": "pause"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "affected_count": 2
  }
  ```
- **Offline Capable**: Yes.

---

### 2.4 Entry Rules & URL Preview API (`/api/rules`, `/api/preview`)

#### `POST /api/rules/test`
- **Purpose**: Evaluates a given URL against all registered regex rules (`trigger_rule_url`) to check matching actions.
- **Request Body**:
  ```json
  { "url": "https://old.reddit.com/r/python" }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "matched_rule_id": 4,
    "rule_name": "Reddit Community Rule",
    "is_blocked": false,
    "is_trusted": true,
    "auto_tags": ["reddit", "social"],
    "age_limit": 0
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/preview/inspect`
- **Purpose**: Resolves preview metadata for a URL (extracts title, favicon, checks if blocked, detects YouTube player embed).
- **Request Body**:
  ```json
  { "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "is_blocked": false,
    "blocking_rule": null,
    "media_type": "video",
    "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
  }
  ```
- **Offline Capable**: Partially (local rule check works offline; metadata extraction requires internet).

---

### 2.5 Database & Storage API (`/api/database`)

#### `GET /api/database/stats`
- **Purpose**: Retrieves table row counts and file size statistics.
- **Response**:
  ```json
  {
    "success": true,
    "database_file": "data/table.db",
    "file_size_bytes": 81641472,
    "tables": {
      "linkdatamodel": 47915,
      "sourcedatamodel": 3221,
      "entrycompactedtags": 8839,
      "usertags": 3848,
      "configurationentry": 1,
      "searchhistory": 0,
      "entryvisithistory": 0,
      "readlater": 0
    }
  }
  ```
- **Offline Capable**: Yes.

#### `POST /api/database/clear-search-history`
- **Purpose**: Truncates `searchhistory` table.
- **Response**:
  ```json
  { "success": true, "message": "Search history cleared." }
  ```
- **Offline Capable**: Yes.

#### `POST /api/database/clear-visited`
- **Purpose**: Truncates `entryvisithistory` table.
- **Response**:
  ```json
  { "success": true, "message": "Visit history cleared." }
  ```
- **Offline Capable**: Yes.

#### `POST /api/database/clear-read-later`
- **Purpose**: Truncates `readlater` table.
- **Response**:
  ```json
  { "success": true, "message": "Read later list cleared." }
  ```
- **Offline Capable**: Yes.

#### `POST /api/database/clear-social-data`
- **Purpose**: Truncates `socialdata` table.
- **Response**:
  ```json
  { "success": true, "message": "Social data cleared." }
  ```
- **Offline Capable**: Yes.

#### `POST /api/database/replace-from-url`
- **Purpose**: Downloads a remote SQLite database file from a URL, validates integrity, and atomically swaps it with the current active database.
- **Request Body**:
  ```json
  { "remote_url": "https://example.com/backups/feed_archive.db" }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Database downloaded, verified, and replaced successfully."
  }
  ```
- **Offline Capable**: No (requires internet).

---

### 2.6 Configuration API (`/api/config`)

#### `POST /api/config/style`
- **Purpose**: Quickly switches display style theme (`style-light` / `style-dark`).
- **Request Body**:
  ```json
  { "display_style": "style-dark" }
  ```
- **Response**:
  ```json
  { "success": true, "display_style": "style-dark" }
  ```
- **Offline Capable**: Yes.

#### `POST /api/config/display-type`
- **Purpose**: Switches entry layout type (`standard`, `gallery`, `search-engine`, `content-centric`, `links-only`).
- **Request Body**:
  ```json
  { "display_type": "gallery" }
  ```
- **Response**:
  ```json
  { "success": true, "display_type": "gallery" }
  ```
- **Offline Capable**: Yes.

---

### 2.7 System Status API (`/api/status`)

#### `GET /api/status/health`
- **Purpose**: System health monitor. Reports worker loop status, network availability, and badge alert counts.
- **Response**:
  ```json
  {
    "status": "healthy",
    "worker_running": true,
    "network_online": true,
    "badges": {
      "sources_outdated": 3,
      "sources_errors": 1,
      "jobs_errors": 0
    }
  }
  ```
- **Offline Capable**: Yes.
