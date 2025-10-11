# Archive.org Integration Plan

## Overview

This document outlines the plan to add archive.org upload functionality to the YouTube Playlist Downloader, allowing users to preserve deleted, private, or unavailable YouTube videos to the Internet Archive.

## Research Summary

### Library & Dependencies

**Package**: `internetarchive`
- **Latest Version**: v5.5.1 (September 2025)
- **Minimum Required**: v5.4.2+ (critical security vulnerability in earlier versions)
- **Python Requirement**: Python ≥3.9
- **Installation**: `pip install internetarchive>=5.4.2`

### Authentication Methods

The internetarchive library supports two authentication approaches:

1. **Config File Method**
   - Location: `~/.config/ia.ini` (Linux/macOS) or `%USERPROFILE%\.config\ia.ini` (Windows)
   - Created via CLI: `ia configure`
   - Created via Python: `internetarchive.configure(access_key, secret_key)`

2. **Environment Variables Method**
   - `IA_ACCESS_KEY_ID` - Your access key
   - `IA_SECRET_ACCESS_KEY` - Your secret key
   - Obtainable from: https://archive.org/account/s3.php

### Archive.org Best Practices

Based on Archive Team guidelines and official documentation:

#### Archival Policy
- **Only archive unavailable videos** - Archive.org advises against uploading still-available YouTube content due to storage concerns
- **Preserve complete context** - Include all available metadata, comments, and related files
- **Use yt-dlp metadata** - Include `.info.json` file with full YouTube metadata
- **Include comments** - Comments are considered part of the archival record

#### Metadata Standards

**Write-Once Fields** (cannot be changed after upload):
- `mediatype` - Must be set correctly on first upload
- `collection` - Item's collection, defaults to 'opensource' if not specified
- `identifier` - Unique item identifier

**Recommended Metadata for Movies/Videos**:

| Field | Description | Example | Editable |
|-------|-------------|---------|----------|
| `mediatype` | Content type | `movies` | No (write-once) |
| `collection` | Collection name | `opensource_movies` | No (write-once) |
| `title` | Video title | Original YouTube title | Yes |
| `creator` | Content creator | Channel name | Yes |
| `date` | Original date | `2023-01-15` (YYYY-MM-DD) | Yes |
| `description` | Full description | Video description + archival context | Yes |
| `subject` | Tags/keywords | `['music', 'tutorial', 'youtube']` | Yes |
| `runtime` | Duration | `00:05:32` (HH:MM:SS) | Yes |
| `language` | Video language | `English` | Yes |
| `licenseurl` | License URL | `http://creativecommons.org/...` | Yes |
| `originalurl` | Source URL | `https://youtube.com/watch?v=...` | Yes |
| `sound` | Audio presence | `sound` or `silent` | Yes |
| `color` | Color format | `color` or `B&W` | Yes |
| `aspect_ratio` | Video aspect | `16:9` or `4:3` | Yes |

**YouTube-Specific Custom Fields**:
- `youtube_channel` - Channel display name
- `youtube_channel_id` - Channel ID
- `youtube_video_id` - Video ID (11 characters)
- `youtube_upload_date` - Original upload date (ISO format)
- `youtube_view_count` - Views at archival time
- `youtube_like_count` - Likes at archival time
- `youtube_comment_count` - Comments at archival time
- `archived_date` - Date archived to Internet Archive
- `archived_reason` - Reason for archival (`deleted`, `private`, `unavailable`, `user_request`)

### Upload API Features

The `item.upload()` method supports:

```python
item.upload(
    files,                    # Dict or list of files to upload
    metadata=metadata_dict,   # Item metadata
    verbose=True,            # Show progress bar
    retries=3,               # Number of retry attempts
    retries_sleep=30,        # Seconds to sleep between retries
    checksum=True,           # Verify uploads with MD5
    queue_derive=True        # Auto-generate derivative formats (thumbnails, streams)
)
```

---

## Implementation Architecture

### Identifier Strategy

**Format**: `youtube-{video_id}`

**Example**: `youtube-dQw4w9WgXcQ`

**Collision Handling**:
If an item with the same identifier already exists on archive.org:
1. Check if we uploaded it (compare metadata/uploader)
2. If ours: Skip with "Already archived" status
3. If someone else's:
   - Option 1: Skip and link to existing archive
   - Option 2: Upload with modified identifier: `youtube-{video_id}-{username}`
   - Option 3: User choice (prompt in GUI/CLI)

### File Organization

Each archive.org item will contain:

```
youtube-{video_id}/
├── video.mp4              # Original video file (if downloaded)
├── audio.m4a              # Audio-only file (if downloaded)
├── comments.md            # Comments in markdown format (if downloaded)
├── metadata.json          # Full YouTube metadata from yt-dlp
└── [auto-generated]       # Archive.org creates: thumbnails, web-streams, etc.
```

### Data Model Changes

**New Enum**: `ArchiveStatus` (core/models.py)
```python
class ArchiveStatus(Enum):
    NOT_ARCHIVED = "not_archived"  # Default state
    UPLOADING = "uploading"        # Upload in progress
    ARCHIVED = "archived"          # Successfully archived
    FAILED = "failed"              # Upload failed
    SKIPPED = "skipped"            # Already exists on IA (by others)
```

**VideoMetadata Extensions**:
```python
@dataclass
class VideoMetadata:
    # ... existing fields ...

    # Archive.org fields
    archive_status: ArchiveStatus = ArchiveStatus.NOT_ARCHIVED
    archive_identifier: Optional[str] = None      # e.g., "youtube-dQw4w9WgXcQ"
    archive_url: Optional[str] = None             # e.g., "https://archive.org/details/youtube-dQw4w9WgXcQ"
    archive_date: Optional[datetime] = None       # When archived
    archive_error: Optional[str] = None           # Last error message if failed
```

---

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Add Dependencies
**File**: `requirements.txt`
```
internetarchive>=5.4.2  # Security-patched version
```

#### 1.2 Update Data Models
**File**: `core/models.py`

Add `ArchiveStatus` enum and extend `VideoMetadata` class with archive tracking fields.

**Preservation Logic**: Update `to_dict()` and `from_dict()` methods to handle new fields.

#### 1.3 Authentication Management
**File**: `core/auth.py`

Add functions:
```python
def configure_archive_org(access_key: str, secret_key: str) -> None:
    """Configure Internet Archive credentials"""

def get_archive_org_credentials() -> Optional[Tuple[str, str]]:
    """Retrieve configured IA credentials"""

def is_archive_org_configured() -> bool:
    """Check if IA credentials are available"""
```

### Phase 2: Archive Manager Module

**New File**: `core/archiver.py`

#### Core Class: `ArchiveManager`

```python
class ArchiveManager:
    def __init__(self, storage: PlaylistStorage):
        self.storage = storage

    def upload_video(
        self,
        video: VideoMetadata,
        playlist: PlaylistMetadata,
        video_path: Optional[Path] = None,
        audio_path: Optional[Path] = None,
        comments_path: Optional[Path] = None,
        retries: int = 3,
        skip_live: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, str]:
        """
        Upload a single video to archive.org

        Args:
            video: Video metadata
            playlist: Parent playlist metadata
            video_path: Path to video file (if downloaded)
            audio_path: Path to audio file (if downloaded)
            comments_path: Path to comments markdown (if downloaded)
            retries: Number of retry attempts on failure
            skip_live: Skip videos with LIVE status
            progress_callback: Function(percent: int) for progress updates

        Returns:
            (success: bool, message: str)
        """

    def upload_batch(
        self,
        videos: List[VideoMetadata],
        playlist: PlaylistMetadata,
        max_workers: int = 3,
        progress_callback: Optional[Callable] = None,
        stop_event: Optional[threading.Event] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Upload multiple videos in parallel

        Returns:
            Dictionary mapping video_id to (success, message)
        """

    def _generate_identifier(self, video_id: str) -> str:
        """Generate archive.org identifier: youtube-{video_id}"""

    def _check_item_exists(self, identifier: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Check if item exists and ownership

        Returns:
            (exists: bool, is_ours: bool, url: Optional[str])
        """

    def _create_metadata(
        self,
        video: VideoMetadata,
        playlist: PlaylistMetadata
    ) -> dict:
        """
        Generate comprehensive Internet Archive metadata

        Returns:
            Metadata dictionary for upload
        """

    def _format_description(self, video: VideoMetadata) -> str:
        """
        Format description with archival context

        Example:
        '''
        [Original YouTube Description]
        {video.description}

        ---
        Archived from YouTube: {original_url}
        Original Channel: {channel_name}
        Original Upload Date: {upload_date}
        Archived Date: {archive_date}
        Reason: {reason}
        '''
        """

    def _generate_tags(self, video: VideoMetadata) -> List[str]:
        """Generate subject tags from video metadata"""

    def _format_runtime(self, duration: Optional[int]) -> Optional[str]:
        """Convert seconds to HH:MM:SS format"""

    def _get_archive_reason(self, video: VideoMetadata) -> str:
        """Determine archival reason from video status"""

    def _create_metadata_json(self, video: VideoMetadata) -> str:
        """Create metadata.json file content (full yt-dlp metadata)"""

    def _upload_files(
        self,
        identifier: str,
        files: Dict[str, Path],
        metadata: dict,
        retries: int,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """
        Upload files to archive.org with retry logic

        Uses internetarchive library's upload method with:
        - Checksum verification
        - Automatic retries
        - Progress reporting
        - Derivative generation (thumbnails, streams)
        """
```

#### Helper Functions

```python
def sanitize_identifier(identifier: str) -> str:
    """Ensure identifier meets IA requirements (alphanumeric, dash, underscore)"""

def validate_metadata(metadata: dict) -> Tuple[bool, Optional[str]]:
    """Validate metadata meets IA requirements"""

def format_file_size(bytes: int) -> str:
    """Convert bytes to human-readable format"""
```

### Phase 3: GUI Integration

#### 3.1 Background Thread
**File**: `gui/main.py`

```python
class ArchiveThread(QThread):
    finished = Signal(dict)          # {video_id: (success, message)}
    error = Signal(str)              # Fatal error
    progress = Signal(int, int, str) # (current, total, status_message)
    video_started = Signal(str)      # video_id
    video_progress = Signal(str, int)# (video_id, percentage)
    video_finished = Signal(str, bool, str)  # (video_id, success, message)

    def __init__(
        self,
        videos: List[VideoMetadata],
        archive_manager: ArchiveManager,
        playlist: PlaylistMetadata,
        storage: PlaylistStorage
    ):
        super().__init__()
        self.videos = videos
        self.archive_manager = archive_manager
        self.playlist = playlist
        self.storage = storage
        self.stop_requested = False

    def request_stop(self):
        """Gracefully stop after current upload"""
        self.stop_requested = True

    def run(self):
        """Upload videos with progress reporting"""
        results = {}

        for i, video in enumerate(self.videos):
            if self.stop_requested:
                break

            self.video_started.emit(video.video_id)

            # Get file paths
            video_path = Path(video.video_path) if video.video_path else None
            audio_path = Path(video.audio_path) if video.audio_path else None
            comments_path = Path(video.comments_path) if video.comments_path else None

            # Progress callback
            def on_progress(percent):
                self.video_progress.emit(video.video_id, percent)

            # Upload
            try:
                success, message = self.archive_manager.upload_video(
                    video, self.playlist,
                    video_path, audio_path, comments_path,
                    progress_callback=on_progress
                )
                results[video.video_id] = (success, message)
                self.video_finished.emit(video.video_id, success, message)

                # Update storage
                if success:
                    video.archive_status = ArchiveStatus.ARCHIVED
                else:
                    video.archive_status = ArchiveStatus.FAILED
                    video.archive_error = message
                self.storage.save_playlist(self.playlist)

            except Exception as e:
                error_msg = str(e)
                results[video.video_id] = (False, error_msg)
                self.video_finished.emit(video.video_id, False, error_msg)

            self.progress.emit(i + 1, len(self.videos), f"Uploaded {i + 1}/{len(self.videos)}")

        self.finished.emit(results)
```

#### 3.2 UI Changes

**Videos Table Enhancements**:
1. Add "Archive" column showing archive status icon:
   - ✓ (green) - ARCHIVED (clickable link to archive.org)
   - ✗ (red) - FAILED (tooltip shows error)
   - ⟳ (blue) - UPLOADING
   - ○ (gray) - NOT_ARCHIVED
   - ⊘ (orange) - SKIPPED

2. Add checkbox column for batch selection (similar to download)

**Context Menu Additions**:
- "Archive to Archive.org" - Single video upload
- "Archive Selected to Archive.org" - Batch upload
- "Open on Archive.org" - Open archived video (if ARCHIVED status)
- "Retry Archive Upload" - Retry failed uploads

**Toolbar Additions**:
- Button: "Archive Selected" (enabled when checkboxes selected)
- Button: "Configure Archive.org" (opens auth dialog)

**Progress Dialog**:
```
┌─────────────────────────────────────────────────┐
│ Archiving to Internet Archive                   │
├─────────────────────────────────────────────────┤
│ Overall Progress: [████████░░░░░░░░] 8/28      │
│                                                  │
│ Current: 009 - Video Title                      │
│ Status: Uploading video.mp4                     │
│ Progress: [██████████░░░░░░] 65%               │
│ Speed: 2.5 MB/s                                 │
│ ETA: 00:03:42                                   │
│                                                  │
│ Completed: 7 successful, 0 failed, 1 skipped    │
│                                                  │
│ [Stop]  [Hide]                                  │
└─────────────────────────────────────────────────┘
```

#### 3.3 Settings Tab Enhancement

Add new section: "Archive.org Integration"

```
Archive.org Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ✓ Configured    [Configure]
Access Key: IAS3_****...****

Upload Options:
☑ Skip live/available videos (only archive deleted/private)
☑ Include comments when available
☐ Upload audio-only items (no video file)
☑ Verify uploads with checksum

Parallel Uploads: [3] ▼   (1-5)
Retry Attempts: [3] ▼     (1-10)
```

### Phase 4: CLI Integration

**File**: `cli/main.py`

#### New Command: `archive`

```bash
# Configure credentials
ytpl auth archive

# Upload single video
ytpl archive <playlist_id> <video_id>

# Upload all downloaded videos
ytpl archive <playlist_id> --all

# Upload only deleted videos
ytpl archive <playlist_id> --status deleted

# Upload only private videos
ytpl archive <playlist_id> --status private

# Upload specific range
ytpl archive <playlist_id> --range 1-10

# Upload with options
ytpl archive <playlist_id> --all --force-live --no-skip-existing

# Check archive status
ytpl archive-status <playlist_id>
```

#### Implementation

```python
@cli.command()
@click.argument('playlist_id')
@click.argument('video_id', required=False)
@click.option('--all', is_flag=True, help='Archive all downloaded videos')
@click.option('--status', type=click.Choice(['deleted', 'private', 'unavailable']),
              help='Archive only videos with specific status')
@click.option('--range', 'video_range', help='Archive videos in range (e.g., 1-10)')
@click.option('--force-live', is_flag=True, help='Archive even if video is still live')
@click.option('--no-skip-existing', is_flag=True, help='Re-upload even if archived')
@click.option('--retries', default=3, help='Number of retry attempts')
def archive(playlist_id, video_id, all, status, video_range, force_live, no_skip_existing, retries):
    """Archive videos to Internet Archive"""

@cli.command()
@click.argument('playlist_id')
def archive_status(playlist_id):
    """Show archive status for playlist videos"""
```

**CLI Output Example**:

```
Archiving videos to Internet Archive...

[1/28] 001 - First Video Title
  Status: Deleted
  Files: video.mp4 (125.3 MB), comments.md (42.1 KB)
  Uploading... [████████████████████] 100% (2.3 MB/s)
  [OK] Archived: https://archive.org/details/youtube-dQw4w9WgXcQ

[2/28] 002 - Second Video Title
  Status: Private
  Files: audio.m4a (8.2 MB), comments.md (15.3 KB)
  Uploading... [████████████████████] 100% (1.8 MB/s)
  [OK] Archived: https://archive.org/details/youtube-kXYZ1234567

[3/28] 003 - Third Video Title
  Status: Live
  [SKIP] Video still available on YouTube (use --force-live to override)

[4/28] 004 - Fourth Video Title
  Status: Deleted
  Files: None
  [SKIP] No files to archive

Summary:
  Total: 28 videos
  Archived: 15 successful
  Failed: 2 (see errors above)
  Skipped: 11 (8 live, 3 no files)
```

### Phase 5: Safety & UX Features

#### 5.1 Pre-Upload Validation

Before uploading, check:

1. **Credentials**
   - Verify archive.org credentials are configured
   - Show configuration instructions if missing

2. **File Availability**
   - At least one file must exist (video OR audio OR comments)
   - Warn if no files available

3. **Video Status**
   - Default: Skip LIVE videos (warn user)
   - Option: Allow override with `--force-live` (CLI) or checkbox (GUI)

4. **Existing Items**
   - Check if identifier already exists on archive.org
   - If exists and ours: Skip with message
   - If exists and not ours: Prompt user for action

5. **Metadata Completeness**
   - Warn if critical metadata missing (title, date, etc.)
   - Allow upload but log warning

#### 5.2 Upload Strategy & Filters

**Default Behavior**:
- Only upload videos with at least one downloaded file
- Skip videos with LIVE status
- Skip videos already archived (archive_status = ARCHIVED)

**User Options**:
- Force upload of LIVE videos
- Upload comments-only items (no video/audio)
- Re-upload previously archived items

**Smart Filtering**:
```python
def should_archive_video(video: VideoMetadata, options: ArchiveOptions) -> Tuple[bool, str]:
    """
    Determine if video should be archived

    Returns:
        (should_archive: bool, reason: str)
    """
    # Check if already archived
    if video.archive_status == ArchiveStatus.ARCHIVED and not options.reupload:
        return (False, "Already archived")

    # Check if any files available
    has_files = any([video.video_path, video.audio_path, video.comments_path])
    if not has_files:
        return (False, "No files to archive")

    # Check status
    if video.status == VideoStatus.LIVE and not options.force_live:
        return (False, "Video still available on YouTube")

    return (True, "Ready to archive")
```

#### 5.3 Error Handling & Retry Logic

**Retry Strategy**:
```python
def upload_with_retry(item, files, metadata, retries=3):
    """Upload with exponential backoff"""
    for attempt in range(retries):
        try:
            item.upload(files, metadata=metadata, checksum=True)
            return (True, "Upload successful")
        except Exception as e:
            if attempt < retries - 1:
                sleep_time = 2 ** attempt * 30  # 30s, 60s, 120s
                time.sleep(sleep_time)
            else:
                return (False, f"Upload failed after {retries} attempts: {str(e)}")
```

**Error Categories**:
1. **Authentication errors** - Invalid credentials
2. **Network errors** - Connection timeout, server unavailable
3. **Quota errors** - Rate limiting, storage quota
4. **Validation errors** - Invalid metadata, forbidden content
5. **File errors** - File not found, corrupted file

**User Feedback**:
- Log all errors to console/log file
- Show user-friendly messages in GUI
- Offer retry button for failed uploads
- Save error details to `archive_error` field

#### 5.4 Progress Monitoring

**Real-time Metrics**:
- Current video being uploaded
- Current file being uploaded (video/audio/comments)
- Upload percentage (0-100%)
- Upload speed (MB/s)
- Estimated time remaining
- Overall progress (X/Y videos)

**Graceful Stop**:
- Stop button in progress dialog
- Finish current file upload
- Mark remaining videos as NOT_ARCHIVED
- Show summary of completed uploads

**Resume Capability**:
- Check `archive_status` before starting batch upload
- Skip videos with ARCHIVED status
- Retry videos with FAILED status
- Continue from last position

---

## Testing Plan

### Manual Testing Checklist

#### Basic Functionality
- [ ] Configure archive.org credentials via GUI
- [ ] Configure archive.org credentials via CLI
- [ ] Upload single deleted video with all files (video, audio, comments)
- [ ] Upload single private video with video only
- [ ] Upload single unavailable video with audio only
- [ ] Upload video with comments only (no media)

#### Batch Operations
- [ ] Upload 5-10 videos in parallel
- [ ] Monitor progress during batch upload
- [ ] Stop batch upload mid-process
- [ ] Resume interrupted batch upload

#### Edge Cases
- [ ] Try to upload LIVE video (should warn/skip)
- [ ] Try to upload video with no files (should skip)
- [ ] Upload video that already exists on IA (collision handling)
- [ ] Upload with missing metadata fields
- [ ] Upload with invalid credentials (error handling)
- [ ] Network failure during upload (retry logic)

#### UI/UX
- [ ] Archive column shows correct status icons
- [ ] Clicking archived video opens archive.org URL
- [ ] Context menu options work correctly
- [ ] Progress dialog updates in real-time
- [ ] Checkboxes allow batch selection
- [ ] Settings persist across sessions

#### CLI
- [ ] `ytpl auth archive` - credential configuration
- [ ] `ytpl archive <id> <video_id>` - single upload
- [ ] `ytpl archive <id> --all` - batch upload
- [ ] `ytpl archive <id> --status deleted` - filtered upload
- [ ] `ytpl archive-status <id>` - status report

#### Data Persistence
- [ ] Archive status saved to JSON
- [ ] Archive URL saved and persisted
- [ ] Archive date recorded correctly
- [ ] Error messages saved on failure
- [ ] Version history tracks archive status changes

### Test Videos

Create test playlist with:
1. 1 deleted video (with files)
2. 1 private video (with files)
3. 1 unavailable video (with files)
4. 1 live video (to test skip behavior)
5. 1 video with comments only (no media)

---

## Implementation Timeline

### Phase 1: Core (Est. 2-3 hours)
- Add dependencies
- Update data models
- Add authentication functions

### Phase 2: Archive Manager (Est. 4-5 hours)
- Create archiver.py module
- Implement upload logic
- Add metadata generation
- Implement retry logic

### Phase 3: GUI (Est. 3-4 hours)
- Add archive column to table
- Add context menu options
- Create ArchiveThread
- Create progress dialog
- Add settings section

### Phase 4: CLI (Est. 2-3 hours)
- Add archive command
- Add archive-status command
- Add auth archive command
- Implement filtering options

### Phase 5: Testing & Polish (Est. 2-3 hours)
- Manual testing
- Bug fixes
- Documentation updates
- User guide

**Total Estimated Time**: 13-18 hours

---

## Future Enhancements

### V1 (Initial Release)
- Basic upload functionality
- Single and batch uploads
- Progress monitoring
- Error handling and retry

### V2 (Future)
- **Automatic archiving**: Monitor playlist changes, auto-archive deleted videos
- **Bulk metadata editing**: Edit archive.org metadata for multiple items
- **Download from archive.org**: Restore videos from IA to local storage
- **Custom collections**: Create and manage custom IA collections
- **Advanced filters**: Archive based on view count, date range, etc.

### V3 (Advanced)
- **Filmot.com integration**: Fetch deleted video metadata from Filmot
- **Collaboration features**: Share archive links, create public playlists
- **Statistics dashboard**: Show archival statistics, storage usage
- **API integration**: Expose archiving as API endpoint

---

## Security Considerations

### Credential Storage
- Store IA credentials securely in config file (not in code)
- Never commit credentials to version control
- Use environment variables as alternative

### Data Privacy
- Respect video privacy settings
- Don't archive content against creator's wishes
- Include archival notice in description

### Upload Validation
- Validate file integrity before upload
- Use checksum verification
- Implement rate limiting to avoid abuse

### Error Logging
- Don't log sensitive information (credentials)
- Sanitize error messages shown to user
- Keep detailed logs for debugging

---

## Documentation Updates Required

### CLAUDE.md
Add new section: "Archive.org Integration"
- Archiver module overview
- Archive status tracking
- Upload workflow
- Metadata preservation for archived items

### README.md
Add features:
- Archive deleted/private videos to Internet Archive
- Batch archiving with progress tracking
- Archive.org authentication support

### User Guide (new file)
Create `ARCHIVING_GUIDE.md`:
- How to get archive.org credentials
- How to archive videos via GUI
- How to archive videos via CLI
- Best practices for archiving
- Troubleshooting common issues

---

## Open Questions / Decisions Needed

1. **Collection Strategy**:
   - Use standard `opensource_movies` collection?
   - Or create custom collection per user/playlist?

2. **Identifier Collision Handling**:
   - Always skip if exists?
   - Prompt user each time?
   - Auto-append username to identifier?

3. **Upload Filter Defaults**:
   - Archive only if files exist (video OR audio OR comments)?
   - Or require at least video/audio (exclude comments-only)?

4. **Rate Limiting**:
   - Should we implement our own rate limiting?
   - Or rely on archive.org API limits?

5. **Metadata Enrichment**:
   - Should we fetch additional metadata from Filmot.com before archiving deleted videos?
   - Or keep that as separate feature?

---

## Conclusion

This plan provides a comprehensive approach to integrating archive.org upload functionality into the YouTube Playlist Downloader. The implementation follows the existing architecture patterns (background threads, progress tracking, metadata preservation) and maintains consistency with the current codebase.

The phased approach allows for incremental development and testing, ensuring each component works correctly before moving to the next phase.

**Next Steps**:
1. Review and approve this plan
2. Answer open questions above
3. Begin Phase 1 implementation
