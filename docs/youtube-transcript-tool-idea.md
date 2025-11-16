# YouTube Transcript Downloader - Standalone CLI Tool

**Status:** Idea / Feature Request
**Created:** 2025-11-16
**Type:** New Standalone Tool
**Complexity:** Low - Simple CLI tool
**Estimated Time:** 2-4 hours

## Overview

A lightweight, standalone CLI tool for downloading YouTube video transcripts (captions/subtitles). This tool would be separate from the main YouTube Playlist Downloader and focused solely on transcript extraction.

## Problem Statement

While the YouTube Playlist Downloader handles video, audio, and comments downloads, users sometimes only need transcripts without downloading the full video content. Use cases include:

- **Content Analysis:** Extract text for NLP, sentiment analysis, or research
- **Accessibility:** Get readable text versions of video content
- **Translation:** Download transcripts in multiple languages
- **Archival:** Save transcripts for deleted/unavailable videos
- **Note-taking:** Get timestamped text for study/reference
- **Bandwidth Saving:** Get content without downloading large video files

## Proposed Tool: `yt-transcript`

A simple, focused CLI tool for downloading YouTube transcripts.

### Core Features

**Basic Functionality:**
- Download transcripts from single YouTube videos
- Download transcripts from entire playlists
- Support for both auto-generated and manual captions
- Multiple language support
- Save in readable text format with timestamps

**Output Formats:**
- Plain text with timestamps (`[MM:SS] text`)
- Plain text without timestamps (full text paragraph)
- Optional: SRT format (SubRip subtitle format)
- Optional: VTT format (WebVTT subtitle format)
- Optional: JSON format (raw transcript data)

**Language Handling:**
- Auto-detect available languages
- Specify preferred language (e.g., `--lang en`)
- Fallback to English if preferred language not available
- Download multiple languages with `--all-languages`
- List available languages with `--list-languages`

### Command-Line Interface

```bash
# Single video
yt-transcript "https://www.youtube.com/watch?v=VIDEO_ID"

# Specify language
yt-transcript VIDEO_ID --lang es

# Multiple languages
yt-transcript VIDEO_ID --lang en,es,fr

# All available languages
yt-transcript VIDEO_ID --all-languages

# Entire playlist
yt-transcript "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# Custom output directory
yt-transcript VIDEO_ID --output ./transcripts

# Different output format
yt-transcript VIDEO_ID --format srt
yt-transcript VIDEO_ID --format vtt
yt-transcript VIDEO_ID --format json

# List available languages for a video
yt-transcript VIDEO_ID --list-languages

# No timestamps (full text only)
yt-transcript VIDEO_ID --no-timestamps

# Batch mode from file
yt-transcript --batch video_ids.txt
```

### Output Examples

**Text format with timestamps:**
```
Transcript for: How to Code in Python
================================================================================

Channel: Programming Tutorial Channel
Video ID: dQw4w9WgXcQ
Video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Language: en
Type: Auto-generated
Downloaded: 2025-11-16 14:30:00

================================================================================

TRANSCRIPT WITH TIMESTAMPS:
--------------------------------------------------------------------------------

[00:00] Welcome to this Python tutorial
[00:05] Today we're going to learn about functions
[00:10] Functions are reusable blocks of code
...

================================================================================
FULL TEXT (no timestamps):
================================================================================

Welcome to this Python tutorial Today we're going to learn about functions...
```

**SRT format:**
```srt
1
00:00:00,000 --> 00:00:05,000
Welcome to this Python tutorial

2
00:00:05,000 --> 00:00:10,000
Today we're going to learn about functions

3
00:00:10,000 --> 00:00:15,000
Functions are reusable blocks of code
```

### Technical Implementation

**Dependencies:**
```
youtube-transcript-api>=0.6.0
click>=8.1.7
requests>=2.31.0
```

**Project Structure:**
```
yt-transcript/
├── README.md
├── requirements.txt
├── setup.py
├── yt_transcript/
│   ├── __init__.py
│   ├── cli.py          # Click CLI interface
│   ├── downloader.py   # Transcript download logic
│   └── formatters.py   # Output format converters
└── tests/
    └── test_downloader.py
```

**Core Components:**

1. **Transcript Downloader** (using `youtube-transcript-api`)
   - Fetch available transcripts
   - Language selection logic
   - Error handling (no transcript, disabled, rate limits)

2. **Format Converters**
   - Text with timestamps
   - Text without timestamps
   - SRT converter
   - VTT converter
   - JSON exporter

3. **CLI Interface** (using `click`)
   - Command parsing
   - Progress display
   - Error reporting
   - Batch processing

4. **Playlist Handler**
   - Extract video IDs from playlist URLs
   - Batch download with progress
   - Skip unavailable/failed videos

### Usage Examples

**Research/Analysis:**
```bash
# Download transcripts from entire course playlist
yt-transcript "https://www.youtube.com/playlist?list=COURSE_PLAYLIST" \
  --output ./course-transcripts \
  --lang en
```

**Multi-language Content:**
```bash
# Get English and Spanish versions
yt-transcript VIDEO_ID --lang en,es --output ./translations
```

**Subtitle Creation:**
```bash
# Export as SRT for video editing
yt-transcript VIDEO_ID --format srt --output ./subtitles
```

**Content Archival:**
```bash
# Batch download from list of video IDs
yt-transcript --batch deleted_videos.txt --all-languages
```

### Advanced Features (Optional)

**Timestamp Filtering:**
```bash
# Get transcript for specific time range
yt-transcript VIDEO_ID --start 1:30 --end 5:45
```

**Text Processing:**
```bash
# Clean up auto-generated artifacts
yt-transcript VIDEO_ID --clean-text

# Remove filler words
yt-transcript VIDEO_ID --remove-fillers
```

**Translation:**
```bash
# Auto-translate to target language (if supported by YouTube)
yt-transcript VIDEO_ID --translate-to es
```

**Metadata:**
```bash
# Include video metadata in output
yt-transcript VIDEO_ID --include-metadata
```

## Benefits

**For Users:**
- ✅ Fast and lightweight (no video download)
- ✅ Simple, single-purpose tool
- ✅ Works offline once installed
- ✅ No authentication required (public videos)
- ✅ Cross-platform (Windows, Linux, macOS)

**Technical Benefits:**
- ✅ Minimal dependencies
- ✅ Easy to install (`pip install yt-transcript`)
- ✅ Fast execution (API-based, no video processing)
- ✅ No FFmpeg dependency
- ✅ Easy to maintain

## Comparison: Standalone vs. Integration

### Standalone Tool (Proposed)
- ✅ Focused, single-purpose
- ✅ Lightweight (small dependencies)
- ✅ Easy to use for non-technical users
- ✅ Can be used independently
- ✅ Fast installation
- ❌ Separate installation/maintenance

### Integration into Playlist Downloader
- ✅ All-in-one solution
- ✅ Unified interface
- ✅ Shared authentication
- ❌ Heavier dependency chain
- ❌ More complex for simple transcript needs
- ❌ Requires full project setup

**Recommendation:** Standalone tool is better for this use case.

## Installation & Distribution

**PyPI Package:**
```bash
pip install yt-transcript
```

**From Source:**
```bash
git clone https://github.com/USERNAME/yt-transcript.git
cd yt-transcript
pip install -e .
```

**Pre-built Executables:**
- Windows: `yt-transcript.exe`
- Linux: AppImage or binary
- macOS: Universal binary

## Potential Challenges

**Rate Limiting:**
- YouTube may rate-limit transcript API requests
- Solution: Implement delays between requests, respect quotas

**Missing Transcripts:**
- Not all videos have transcripts/captions
- Solution: Clear error messages, optional auto-skip

**Language Availability:**
- Requested language may not be available
- Solution: Fallback logic, list available languages first

**Video Unavailability:**
- Videos may be deleted/private
- Solution: Graceful error handling, skip in batch mode

## Success Metrics

- Downloads complete successfully for 95%+ of videos with transcripts
- Clear error messages for all failure cases
- Performance: <2 seconds per transcript download
- User satisfaction: Easy to use for non-technical users

## Next Steps

1. **Create New Repository:** `yt-transcript` (separate from playlist downloader)
2. **Setup Project Structure:** Basic Python package with Click CLI
3. **Implement Core:** Transcript downloader using `youtube-transcript-api`
4. **Add Formatters:** Text, SRT, VTT output formats
5. **Playlist Support:** Batch downloading from playlists
6. **Testing:** Unit tests and real-world video testing
7. **Documentation:** README with examples and usage guide
8. **PyPI Release:** Package and publish to PyPI
9. **Promote:** Share on GitHub, Reddit (r/Python, r/youtube), HN

## Timeline Estimate

**Phase 1: MVP (2-4 hours)**
- Basic CLI with single video download
- Text output format with timestamps
- Language selection
- Error handling

**Phase 2: Polish (2-3 hours)**
- Playlist support
- Multiple output formats (SRT, VTT)
- Batch mode
- Better error messages

**Phase 3: Distribution (2-4 hours)**
- Package for PyPI
- Documentation
- README with examples
- GitHub setup

**Total:** 6-11 hours for complete, production-ready tool

## Similar Tools / Inspiration

- `youtube-dl` / `yt-dlp` - Video downloaders (we're transcript-focused)
- `youtube-transcript-api` - Library we'll use (our tool is CLI wrapper)
- `subliminal` - Subtitle downloader (different source, OpenSubtitles)

**Our Differentiator:** Focused specifically on YouTube transcripts with clean CLI and multiple output formats.

## License

MIT License (permissive, allows commercial use)

## Questions / Decisions Needed

1. Tool name: `yt-transcript`, `youtube-transcript-dl`, or other?
2. Should we support YouTube Music/Shorts differently?
3. Include web UI in future (Flask/FastAPI)?
4. Support other video platforms (Vimeo, etc.)?

## References

- **youtube-transcript-api:** https://github.com/jdepoix/youtube-transcript-api
- **Click Documentation:** https://click.palletsprojects.com/
- **SRT Format Spec:** https://en.wikipedia.org/wiki/SubRip
- **VTT Format Spec:** https://www.w3.org/TR/webvtt1/

---

**Status:** Awaiting approval to proceed
**Priority:** Medium - Nice to have, not urgent
**Effort:** Low - Simple, well-scoped project

**Ready to implement?** This could be built in a weekend!
