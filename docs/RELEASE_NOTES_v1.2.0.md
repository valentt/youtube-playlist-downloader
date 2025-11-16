# v1.2.0 - Archive.org Integration & Upload Progress Tracking

## 🎉 Major Release: Archive.org Integration

This release adds comprehensive Internet Archive integration with advanced upload progress tracking!

### 🆕 New Features

#### Archive.org Integration
- **Upload to Internet Archive**: Preserve YouTube videos, audio, and comments on archive.org
- **S3 Authentication**: Configure access/secret keys in Settings tab
- **Comprehensive Metadata**: Preserves title, channel, views, likes, comments, upload date, and more
- **Archive Status Tracking**: Track ARCHIVED/UPLOADING/FAILED status per video
- **Batch Operations**: Upload multiple videos in parallel
- **Smart Duplicate Detection**: Skip videos already archived
- **Archival Reason Tracking**: Records why video was archived (deleted/private/unavailable/user_request)

#### Upload Progress Tracking
- **Two-Phase Progress**: Separate tracking for caching (buffering) and uploading phases
- **Real-time Metrics**: Speed (MB/s), percentage, and ETA display
- **Smart Phase Detection**: Automatically detects transition from caching to upload (10 MB/s threshold)
- **CLI & GUI Progress**: Progress bars in both interfaces
- **Phase-Relative Counting**: Accurate byte counting prevents >100% display bugs

#### UX Improvements
- **Double-Click Playlist Loading**: Double-click any playlist to load and switch to Videos tab
- **Anonymous Mode**: Download public playlists without authentication
- **Context Menu File Opening**: Right-click videos to open files in default system viewer

### 🔧 Technical Improvements
- `UploadProgress` class with sliding window speed calculation (2-second window)
- `ProgressFileWrapper` for file read interception during uploads
- Thread-safe progress callbacks for GUI background operations
- Phase-relative byte tracking prevents double-counting
- Archive CLI commands: `upload`, `batch-upload`, `status`

### 📚 Documentation
- **CLAUDE.md**: Complete project architecture guide
- **archive-org-integration-plan.md**: Integration planning and decisions
- **archive-upload-progress-plan.md**: Progress tracking implementation details
- **youtube-metadata-analysis.md**: Research on deleted video metadata recovery

### 🐛 Bug Fixes
- Fixed upload progress showing >100% due to double file reads
- Fixed negative ETA calculations during uploads
- Fixed byte display during upload phase (now shows phase-relative bytes)
- Fixed CLI progress output not displaying

### 📦 Dependencies
- Added `internetarchive` library for archive.org uploads

### 🔍 Archive.org Features
- Automatic identifier generation: `youtube-{video_id}`
- Full YouTube metadata saved as separate JSON file
- Retry logic with exponential backoff (30s, 60s, 120s)
- Checksum verification for data integrity
- Support for uploading videos still live on YouTube (user override)

---

**Full Changelog**: https://github.com/valentt/youtube-playlist-downloader/compare/v1.1.0...v1.2.0

🤖 Generated with [Claude Code](https://claude.com/claude-code)
