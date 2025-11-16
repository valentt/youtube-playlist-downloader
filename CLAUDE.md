# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Playlist Downloader - A cross-platform tool with dual CLI/GUI interfaces for downloading YouTube playlists, tracking changes over time, and monitoring video status (live/deleted/private). Features JSON versioning, parallel downloads, authentication support, comments archival, and archive.org integration for preserving deleted/private videos.

## Running the Application

**Always use the launcher scripts** (they handle virtual environment automatically):

```bash
# Windows
run_gui.bat          # Launch GUI
run_cli.bat --help   # Launch CLI with help

# Linux/macOS
./run_gui.sh         # Launch GUI
./run_cli.sh --help  # Launch CLI with help
```

**Setup (first time only):**
```bash
# Windows
setup.bat

# Linux/macOS
chmod +x setup.sh
./setup.sh
```

## Architecture Overview

### Core Data Flow

```
Fetch Playlist → PlaylistFetcher (yt-dlp) → PlaylistMetadata
                                                   ↓
                                            PlaylistStorage
                                            ↓             ↓
                                  current_state.json   version_history.json
                                            ↓
                                    DownloadManager → Downloads + Comments
                                            ↓
                                    ArchiveManager → Archive.org Upload
```

### Key Architectural Patterns

#### 1. **State Merging Pattern** (storage.py:192-262)
The `update_playlist()` method implements intelligent state merging:
- Preserves download history (video_path, audio_path, comments_path)
- Maintains status_history across updates
- Detects videos removed from playlist and marks them DELETED
- Never loses historical data - removed videos stay in JSON with updated status

**Critical:** When fetching metadata for existing videos, always preserve:
- `download_status`, `video_path`, `audio_path`, `comments_path`
- `first_seen`, `status_history`, `playlist_index`

#### 2. **Dual-Speed Fetch Pattern** (playlist_fetcher.py:24-88)
Two fetch modes with different trade-offs:
- **Fast mode** (`extract_flat='in_playlist'`): ~30 seconds, basic info only
- **Detailed mode** (`extract_flat=False`): ~5-10 minutes, full metadata + error messages

Detailed mode includes:
- 1-2 second delay between videos (rate-limiting protection)
- Full error messages for unavailable videos
- Complete metadata extraction

#### 3. **Unavailable Video Handling** (playlist_fetcher.py:135-168)
When yt-dlp returns `None` entries (rate-limited/unavailable):
- Create placeholder VideoMetadata with `unavailable_{index}` ID
- Set status to UNAVAILABLE
- Store in JSON to preserve playlist structure
- Never skip - all videos must be tracked

#### 4. **Background Thread Pattern** (gui/main.py)
All long-running operations use QThread with signals:
- `FetchThread` - playlist fetching
- `DownloadThread` - parallel downloads + comments
- `EnrichThread` - metadata enrichment
- `SingleVideoDownloadThread` - individual video/audio downloads
- `ArchiveThread` - archive.org uploads

**Thread Safety:** Always reload playlist from storage after thread completion to pick up updated paths.

### Module Responsibilities

**core/models.py**
- Dataclasses for all entities: `VideoMetadata`, `PlaylistMetadata`, `PlaylistVersion`
- Enums: `VideoStatus` (live/deleted/private/unavailable), `DownloadStatus`, `ArchiveStatus`
- `VideoMetadata.comments_path` - tracks markdown comments file
- `VideoMetadata.archive_*` fields - track archive.org upload status and URLs
- `.to_dict()` / `.from_dict()` for JSON serialization

**core/storage.py**
- JSON persistence with versioning
- State merging logic (preserves history)
- Version snapshot creation (compares states, records changes)
- File structure: `playlists/{playlist_id}/current_state.json` + `version_history.json`

**core/playlist_fetcher.py**
- yt-dlp wrapper with authentication
- Fast/detailed fetch modes
- `enrich_playlist_metadata()` - upgrades fast → detailed
- Rate-limiting delays in detailed mode
- Handles None entries from yt-dlp

**core/downloader.py**
- Parallel video downloads (ThreadPoolExecutor)
- `download_comments()` - extracts comments to markdown
- Auto-resume, quality selection, audio extraction
- Sanitizes filenames for cross-platform compatibility
- Format: `{index:03d} - {title}.{ext}` (e.g., "001 - Video Title.mp4")

**core/auth.py**
- Cookie-based authentication (Netscape format)
- OAuth 2.0 flow for YouTube API
- Archive.org S3 credentials management
- Config storage in `~/.ytpl_downloader/` and `~/.config/ia.ini`

**core/archiver.py**
- Archive.org upload manager using `internetarchive` library
- Single and batch upload with retry logic (exponential backoff)
- Comprehensive metadata generation (YouTube data + archival context)
- Identifier collision detection (checks if item already exists)
- Format: `youtube-{video_id}` items on archive.org
- Uploads video/audio/comments/metadata JSON files

**cli/main.py**
- Click-based CLI with subcommands: fetch, download, list, update, history, playlists, auth, archive, archive-status
- All commands work with playlist IDs extracted from URLs
- Archive commands support filtering by status and single/batch operations

**gui/main.py**
- PySide6 GUI with 3 tabs: Playlists, Videos, Settings
- Context menus for single-item operations (download, archive, enrich)
- Real-time progress tracking with progress bars
- Table shows: Video DL ✓/✗, Audio DL ✓/✗, Comments ✓/✗, Archive ✓/✗
- Archive.org configuration dialog in Settings tab

## Critical Implementation Details

### Metadata Preservation Chain
When enriching or fetching single videos, preserve these fields:
```python
detailed.download_status = video.download_status
detailed.video_path = video.video_path
detailed.audio_path = video.audio_path
detailed.comments_path = video.comments_path
detailed.archive_status = video.archive_status
detailed.archive_identifier = video.archive_identifier
detailed.archive_url = video.archive_url
detailed.archive_date = video.archive_date
detailed.archive_error = video.archive_error
detailed.first_seen = video.first_seen
detailed.status_history = video.status_history
detailed.playlist_index = video.playlist_index
```

### Download Manager Arguments
`download_video(video, output_dir: Path, quality, audio_only)` expects:
- `output_dir` as Path object (use `get_playlist_download_dir(playlist)`)
- NOT the playlist object itself

### Comments Format
Markdown files saved as `{index:03d} - {title}_comments.md` with:
- Header: video metadata, download timestamp, comment count
- Each comment: author, date, likes, favorited status, text
- Indentation for replies (`  > `)

### GUI Reload Pattern
After background operations that modify files:
```python
# Reload playlist from storage to get updated paths
reloaded = self.storage.load_playlist(self.current_playlist.playlist_id)
if reloaded:
    self.current_playlist = reloaded
self.display_playlist()  # Refresh UI
```

### Rate Limiting Protection
Detailed fetch and enrichment use delays:
- `sleep_interval: 1`, `max_sleep_interval: 2` in yt-dlp options
- `time.sleep(1)` between individual video fetches in enrichment

### Authentication Modes & Rate Limiting

#### Anonymous Mode (Public Playlists Only)
When no cookies or OAuth credentials are configured, the tool operates in **anonymous mode**:
- **Access**: Public playlists and videos only
- **Rate limits**: More restrictive than authenticated mode
- **Use case**: Avoid account rate-limiting or access public content without login

**When to use anonymous mode:**
- Your YouTube account was rate-limited or blocked
- You only need to access public playlists
- You want to reduce the risk of account restrictions

#### Authenticated Mode (Cookies or OAuth)
With cookies or OAuth configured:
- **Access**: Public and private playlists, unlisted videos
- **Rate limits**: More generous than anonymous mode
- **Risk**: Heavy usage may trigger YouTube rate limiting on your account

#### Switching Between Modes

**GUI:**
- Settings tab → "Clear" button next to "Set Cookies"
- Settings tab → "Clear" button next to "Setup OAuth"
- Confirmation dialog warns about switching to anonymous mode

**CLI:**
```bash
# Clear cookies (switch to anonymous mode)
ytpl auth clear-cookies

# Clear OAuth token
ytpl auth clear-oauth

# Check current authentication status
ytpl auth status
```

#### Rate Limiting Best Practices

**If your account gets rate-limited or blocked:**
1. **Clear cookies immediately**: `ytpl auth clear-cookies` (GUI or CLI)
2. **Wait before retrying**: Give YouTube's rate limiter time to reset (1-24 hours)
3. **Switch to anonymous mode**: Continue with public playlists only
4. **Reduce request frequency**: Follow guidelines below

**To avoid rate limiting:**

1. **Use Fast Mode**:
   - GUI: Uncheck "Fetch Detailed Metadata"
   - CLI: Default fetch behavior (fast mode)
   - ~30 seconds vs 5-10 minutes for detailed mode

2. **Reduce Parallel Workers**:
   - GUI: Settings tab → Download Workers: 2-3 instead of 5
   - CLI: `--workers 2` or `--workers 3`

3. **Add Manual Delays**:
   - Wait between operations (fetches, enrichments, downloads)
   - Don't fetch multiple large playlists back-to-back

4. **Avoid Detailed Fetch Unless Necessary**:
   - Only use detailed fetch for archival purposes
   - Fast mode is sufficient for basic playlist tracking

5. **Monitor for Warning Signs**:
   - Error messages mentioning "rate limit" or "try again later"
   - Repeated "Video unavailable" errors for known public videos
   - Slow response times from YouTube

**Recovery from rate limiting:**
- Symptom: "The current session has been rate-limited by YouTube for up to an hour"
- Solution: Clear cookies, wait 1+ hours, switch to anonymous mode temporarily
- Prevention: Follow best practices above

#### Authentication Status Check

**GUI:** Settings tab shows green/red indicators for:
- Cookies: Available / Not set
- OAuth: Available / Not set
- Archive.org: Configured / Not configured

**CLI:**
```bash
ytpl auth status

# Output shows:
# Authentication Status:
#   Cookies:     [OK] Available  or  [FAIL] Not set
#   OAuth:       [OK] Available  or  [FAIL] Not set
#   Archive.org: [OK] Configured or  [FAIL] Not configured
```

## Common Patterns

### Adding New Download Types
1. Add path field to `VideoMetadata` in models.py
2. Create download method in downloader.py
3. Add checkbox to GUI download options
4. Add column to videos table
5. Update preservation logic in fetcher and GUI
6. Add context menu option

### Adding CLI Commands
```python
@cli.command()
@click.argument('playlist_id')
@click.option('--option', default=value)
def command_name(playlist_id, option):
    # Use core modules
    pass
```

### Thread Creation Pattern
```python
class NewThread(QThread):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, int, str)  # optional

    def __init__(self, manager, params):
        super().__init__()
        self.manager = manager
        self.params = params

    def run(self):
        try:
            result = self.manager.operation(self.params)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

## Testing

No formal test suite exists. Test manually:
1. Fast fetch → verify videos table populates
2. Detailed fetch → verify unavailable videos appear with proper status
3. Download with comments → verify .md files created
4. Single item download → verify table checkmarks update
5. Update existing playlist → verify version_history.json tracks changes

## Recent Improvements (v1.1.0)

### Two-Step Fetch Pattern
The fetch system now uses a two-step approach:
1. **Always** use `extract_flat: 'in_playlist'` first to get all video IDs (including unavailable)
2. In detailed mode, automatically call `enrich_playlist_metadata()` to fetch full details

This ensures video IDs are captured even when yt-dlp returns `None` for unavailable videos.

### Video ID Extraction for Unavailable Videos
New helper function `extract_video_id()` (playlist_fetcher.py:169-188):
- Tries `entry['id']` field first
- Falls back to regex parsing from URL fields
- Extracts 11-character YouTube video IDs even from minimal entry data
- Pattern: `(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})`

### Human-Friendly Folder Naming
Playlist folders now use format: `"Channel - PlaylistName"` instead of playlist IDs.

**Implementation** (storage.py):
- `_get_human_friendly_folder_name()` - generates safe folder names
- `get_playlist_dir()` - searches by playlist_id in JSON files
- `save_playlist()` - auto-renames folders with collision detection
- `migrate_to_human_friendly_names()` - one-time migration for existing folders

**Migration Script:** `scripts/migrate_folders.py` - renames existing playlist folders

### Enrichment Improvements
- Skip placeholder IDs (`unavailable_*`, `unknown_*`, `invalid_*`) during enrichment
- Better CLI logging with `[OK]` and `[SKIP]` markers
- Windows console compatibility (removed Unicode symbols ✓/✗)

### Better Status Detection
More accurate differentiation between:
- **PRIVATE**: `'private' in error_msg` or `entry.get('availability') == 'private'`
- **DELETED**: `'deleted' in error_msg`
- **UNAVAILABLE**: Default fallback

## Archive.org Integration

### Overview
The archiver module enables preservation of deleted, private, or unavailable YouTube videos by uploading them to the Internet Archive.

### Key Features
- **Automatic metadata generation**: Creates comprehensive archive.org metadata from YouTube video data
- **Smart collision detection**: Checks if video already archived by others, avoids duplicates
- **Retry logic**: Exponential backoff (30s, 60s, 120s) for failed uploads
- **Progress tracking**: Real-time upload progress in both CLI and GUI
- **Identifier format**: `youtube-{video_id}` (e.g., `youtube-dQw4w9WgXcQ`)

### Archive.org Metadata Structure
Each uploaded item includes:
```python
{
    'mediatype': 'movies',
    'collection': 'opensource_movies',
    'title': video.title,
    'creator': video.channel,
    'date': video.upload_date,  # YYYY-MM-DD format
    'description': formatted_description,  # Original + archival context
    'subject': tags,  # Video tags + status tags
    'runtime': 'HH:MM:SS',
    'originalurl': 'https://youtube.com/watch?v=...',
    'youtube_video_id': video_id,
    'youtube_channel': channel_name,
    'youtube_channel_id': channel_id,
    'archived_date': timestamp,
    'archived_reason': 'deleted'|'private'|'unavailable'|'user_request'
}
```

### Files Uploaded Per Item
```
youtube-{video_id}/
├── {index:03d} - {title}.mp4       # Video file (if downloaded)
├── {index:03d} - {title}.m4a       # Audio file (if downloaded)
├── {index:03d} - {title}_comments.md  # Comments (if downloaded)
└── youtube-{video_id}_metadata.json   # Full YouTube metadata
```

### Upload Workflow
1. **Pre-upload validation**:
   - Check archive.org credentials configured
   - Verify at least one file exists (video/audio/comments)
   - Skip LIVE videos by default (override with `--force`)
   - Check if item already exists on archive.org

2. **Collision handling**:
   - If item exists and uploaded by us: Skip
   - If item exists by others: Mark as SKIPPED, save URL

3. **Upload process**:
   - Generate identifier: `youtube-{video_id}`
   - Create comprehensive metadata dict
   - Create metadata.json file
   - Upload all files with retry logic and **real-time progress tracking**
   - Update VideoMetadata with archive_status, archive_url, archive_date

4. **Post-upload**:
   - Save playlist state to persist archive status
   - Reload in GUI to update table display

### Upload Progress Tracking (v1.2.0)

Real-time upload progress monitoring shows percentage, speed, and ETA during archive.org uploads.

**Implementation:**
- **UploadProgress class** (archiver.py): Tracks bytes sent, calculates speed & ETA
- **ProgressFileWrapper class** (archiver.py): Wraps file objects to intercept `read()` calls
- **Progress callbacks**: Optional callback parameter in `upload_video()`

**CLI Progress Display:**
```bash
$ ytpl archive PLxxx video_id

[1/1] Video Title...
  video.mp4: [████████████░░░░░░] 67% (123.4MB/184.2MB) @ 2.3 MB/s - ETA: 26s
```

- Progress bar updates on same line (carriage return)
- Shows filename, percentage, bytes transferred, speed (MB/s), and estimated time remaining
- Separate progress shown for each file (video, audio, comments, metadata)

**GUI Progress Display:**

Status bar shows: `"Uploading filename: 45% (12.3MB/27.5MB) @ 2.1 MB/s - ETA: 1m 23s"`

- Real-time updates without freezing UI (uses Qt signals/slots)
- `ArchiveThread.file_progress` signal emits: filename, bytes_sent, total_bytes, speed_mbps
- `MainWindow.on_archive_file_progress()` slot updates status bar

**Technical Details:**

File wrapper pattern monitors upload progress:
1. `ProgressFileWrapper` wraps the file being uploaded
2. Intercepts every `read()` call during upload
3. Tracks cumulative bytes sent
4. Calculates speed: `(bytes_sent / elapsed_time) / (1024 * 1024)` MB/s
5. Calculates ETA: `(bytes_remaining / bytes_per_second)`
6. Calls progress callback with current stats
7. Callback updates CLI display or GUI status bar

**Progress Callback Signature:**
```python
def progress_callback(
    filename: str,       # Remote filename being uploaded
    bytes_sent: int,     # Bytes transferred so far
    total_bytes: int,    # Total file size
    speed_mbps: float    # Current upload speed in MB/s
) -> None:
```

**Why File Wrapper?**
- `internetarchive` library doesn't provide progress callbacks
- Wrapping file objects allows monitoring without library modifications
- Compatible with library's internal upload mechanism
- Works transparently without breaking existing functionality

### CLI Commands
```bash
# Configure credentials
ytpl auth archive
# Prompts for access key and secret key from https://archive.org/account/s3.php

# Archive single video
ytpl archive <playlist_id> <video_id>

# Archive all videos with files
ytpl archive <playlist_id> --all

# Archive only deleted videos
ytpl archive <playlist_id> --status deleted

# Archive private videos
ytpl archive <playlist_id> --status private

# Force archive of live videos
ytpl archive <playlist_id> --all --force

# Check archive status
ytpl archive-status <playlist_id>        # Summary
ytpl archive-status <playlist_id> -v     # Detailed table
```

### GUI Operations
1. **Configure Archive.org**: Settings tab → Archive.org section → Configure button
2. **Archive single video**: Right-click video → "Archive to Archive.org"
3. **Open archived video**: Right-click archived video → "Open on Archive.org"
4. **Retry failed upload**: Right-click failed video → "Retry Archive Upload"
5. **View status**: Archive column shows: ✓ (archived), ✗ (failed), ⊘ (skipped), ○ (not archived)

### Opening Downloaded Files
Right-click any video to open downloaded files with default OS viewer:
- **Open Video File** - Opens .mp4/.webm with default video player
- **Open Audio File** - Opens .m4a/.mp3 with default audio player
- **Open Comments File** - Opens .md with default text editor/markdown viewer
- Options only appear if files exist

### ArchiveStatus Enum
- `NOT_ARCHIVED`: Default state, not yet uploaded
- `UPLOADING`: Upload in progress (shown in GUI only)
- `ARCHIVED`: Successfully uploaded to archive.org
- `FAILED`: Upload failed after retries (error stored in `archive_error`)
- `SKIPPED`: Already exists on archive.org (by another user)

### Error Handling
- Retry with exponential backoff: 30s, 60s, 120s
- Save error message to `archive_error` field
- Continue with next video in batch operations
- Show summary: X successful, Y failed, Z skipped

### Best Practices
- **Archive proactively**: Tool archives LIVE videos by default (for preservation before deletion)
- **Use detailed fetch first**: Ensures accurate metadata for archival
- **Archive deleted videos promptly**: May not be recoverable later
- **Include comments**: Valuable historical context
- **Check existing archives**: Tool automatically detects duplicates

### Archive Behavior
- **Default**: Archives ANY video when explicitly requested, regardless of status (LIVE, deleted, private, etc.)
- **Philosophy**: If you explicitly choose to archive, the tool respects your decision
- **Preservation First**: Designed for proactive preservation before videos disappear

## External Resources

**docs/youtube-metadata-analysis.md**: Analysis of potential Filmot.com integration for deleted video metadata recovery. See this file for future enhancement opportunities.

**docs/archive-org-integration-plan.md**: Detailed implementation plan for archive.org integration including research, architecture decisions, and testing strategy.

**docs/archive-upload-progress-plan.md**: Detailed implementation plan for upload progress tracking.

**docs/archival-options-idea.md**: Research on future archival backend options (IPFS, Arweave, PeerTube, etc.).

## Important Notes

- **Never commit** `cookies.txt`, `client_secrets.json`, `oauth_token.json`, `.venv/`, `downloads/`, `~/.config/ia.ini`
- **Virtual environment** is required - launcher scripts handle this
- **FFmpeg** must be installed separately (not in requirements.txt)
- **Playlist IDs** are extracted from URLs automatically in CLI
- **Downloads** resume automatically if interrupted
- **Version history** only created if there are actual changes
- **Fast mode** doesn't capture error messages - use detailed for archival
- **Migration script** (`scripts/migrate_folders.py`) can be deleted after first run
- **Archive.org credentials** obtained from https://archive.org/account/s3.php
- **Archive.org uploads** use `internetarchive>=5.4.2` library (security-patched version)
- remember to use powershell --command