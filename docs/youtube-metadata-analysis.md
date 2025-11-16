# YouTube Metadata Repository Analysis

**Date:** 2025-10-10
**Repository:** https://github.com/mattwright324/youtube-metadata
**Purpose:** Evaluate potential integration opportunities for YouTube Playlist Downloader

---

## Executive Summary

The **youtube-metadata** tool is a web-based YouTube metadata explorer that uses the YouTube Data API v3. Its most valuable feature for our project is **Filmot.com integration** for retrieving metadata from deleted/private videos, which could significantly enhance our playlist tracking capabilities.

---

## What youtube-metadata Does

### Core Features

- **Web-based YouTube metadata explorer** using YouTube Data API v3
- **Comprehensive metadata extraction** for videos, playlists, and channels
- **Deleted/private video recovery** via Filmot.com integration
- **Export capabilities**: JSON/CSV with ZIP packaging
- **Geolocation visualization** with Google Maps integration
- **Multiple thumbnail quality levels** with reverse image search
- **Language/country code translation**
- **OSINT research tool** for investigative purposes

### Technology Stack

- **Frontend:** JavaScript-based (client-side web app)
- **API:** YouTube Data API v3 (requires API key)
- **External Integrations:**
  - **Filmot.com**: Deleted video metadata archive
  - **Archive.org**: Video/thumbnail archives
  - **Google Maps**: Geolocation display

---

## Comparison with Current Implementation

| Feature | Your Tool (yt-dlp) | youtube-metadata |
|---------|-------------------|------------------|
| **Backend** | Python + yt-dlp | JavaScript + YouTube API v3 |
| **Auth** | Cookies/OAuth | YouTube API Key |
| **Deleted Videos** | Basic status detection | **Filmot integration** for full metadata |
| **Metadata Source** | yt-dlp extraction | YouTube API v3 |
| **Geolocation** | ❌ Not extracted | ✅ Maps integration |
| **API Quota** | No quota limits | API quota limits apply |
| **Offline Mode** | ✅ Works with cookies | ❌ Requires API key |
| **Thumbnails** | Single URL | Multiple qualities + reverse search |
| **Export** | JSON versioning | JSON + CSV + ZIP |
| **Desktop App** | ✅ GUI + CLI | ❌ Web-based only |
| **Parallel Downloads** | ✅ 5 workers | ❌ No download feature |

---

## What Filmot.com Offers

### Overview

**Filmot** is a YouTube metadata search engine that archives and provides access to metadata from deleted, private, and unavailable videos.

### How It Works

1. **API Endpoint:** `https://filmot.com/api/getvideos?id={videoId}`
2. **Web Interface:** `https://filmot.com/video/{videoId}`
3. **Channel Browsing:** `https://filmot.com/channel/{channelId}`

### Recoverable Information

- Original video title
- Channel name and ID
- Upload date
- View count and statistics
- Subtitles (if archived)
- Original thumbnail

### Limitations

- Not all deleted videos are archived
- Recovery depends on prior indexing by Filmot
- Some metadata may be partial or incomplete
- No guarantees of availability

---

## Potential Enhancements for Our Project

### 1. Filmot Integration for Deleted Videos ⭐ **HIGHLY RECOMMENDED**

**Current State:**
- When a video is deleted, we show: `[Deleted Video]` or `[Unavailable Video]`
- Video ID may be missing for some deleted videos
- No information about what was deleted

**With Filmot Integration:**
- Query Filmot API when video status is DELETED/UNAVAILABLE/PRIVATE
- Retrieve and store original metadata:
  - Original title
  - Channel name
  - Upload date
  - View statistics
- Mark metadata as `[ARCHIVED FROM FILMOT]`

**Implementation Estimate:** ~100 lines of code

**Benefits:**
- Users can see **what was deleted** instead of generic placeholders
- Better historical preservation of playlist data
- Improved archival/research capabilities
- Better tracking of content removal patterns

**Sample Implementation:**

```python
# ytpl_downloader/core/filmot_enricher.py (NEW FILE)
import requests
from typing import Optional, Dict
from .models import VideoMetadata

class FilmotEnricher:
    """Enrich deleted video metadata from Filmot archive."""

    BASE_URL = "https://filmot.com/api/getvideos"

    def get_deleted_video_info(self, video_id: str) -> Optional[Dict]:
        """Retrieve metadata for deleted video from Filmot."""
        try:
            response = requests.get(
                f"{self.BASE_URL}?id={video_id}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data
            return None
        except Exception as e:
            print(f"Filmot enrichment failed for {video_id}: {e}")
            return None

    def enrich_video_metadata(self, video: VideoMetadata) -> VideoMetadata:
        """Enrich unavailable video with Filmot data if available."""
        if video.status in ['DELETED', 'UNAVAILABLE', 'PRIVATE']:
            filmot_data = self.get_deleted_video_info(video.video_id)

            if filmot_data:
                # Update video with archived data
                video.title = filmot_data.get('title', video.title)
                video.channel = filmot_data.get('channel', video.channel)
                video.view_count = filmot_data.get('views')
                video.upload_date = filmot_data.get('upload_date')

                # Mark as archived
                if not video.description.startswith('[ARCHIVED'):
                    video.description = f"[ARCHIVED DATA] {video.description}"

        return video
```

**Usage in playlist_fetcher.py:**

```python
from .filmot_enricher import FilmotEnricher

class PlaylistFetcher:
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or AuthManager()
        self.filmot = FilmotEnricher()  # Add Filmot enricher

    def enrich_playlist_metadata(self, playlist, progress_callback):
        # ... existing code ...

        for video_id, video in playlist.videos.items():
            detailed = self.fetch_video_metadata(video_id)

            if not detailed or detailed.status != VideoStatus.LIVE:
                # Try Filmot enrichment for unavailable videos
                detailed = self.filmot.enrich_video_metadata(detailed or video)

            # ... rest of enrichment code ...
```

---

### 2. Enhanced Thumbnail Storage

**Current State:**
- Single thumbnail URL stored: `video.thumbnail`

**Enhancement:**
- Store all available thumbnail qualities

```python
# In models.py
class VideoMetadata:
    thumbnails: Dict[str, str] = field(default_factory=dict)
    # {
    #   'default': 'url',    # 120x90
    #   'medium': 'url',     # 320x180
    #   'high': 'url',       # 480x360
    #   'standard': 'url',   # 640x480
    #   'maxres': 'url'      # 1280x720
    # }
```

**Benefits:**
- Better quality thumbnails for deleted video identification
- Flexible display options in GUI
- Higher quality for archival purposes

**Implementation Estimate:** ~20 lines of code

---

### 3. CSV Export Option

**Current State:**
- Export to JSON only

**Enhancement:**
- Add CSV export for spreadsheet analysis

```python
# In storage.py
def export_to_csv(self, playlist_id: str, output_file: Path) -> None:
    """Export playlist to CSV format."""
    import csv

    playlist = self.load_playlist(playlist_id)
    if not playlist:
        raise ValueError(f"Playlist {playlist_id} not found")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Position', 'Video ID', 'Title', 'Channel', 'Upload Date',
            'Duration', 'Status', 'Download Status', 'View Count', 'URL'
        ])

        # Data rows
        for video in sorted(playlist.videos.values(),
                          key=lambda v: v.playlist_index):
            writer.writerow([
                video.playlist_index,
                video.video_id,
                video.title,
                video.channel,
                video.upload_date,
                video.duration,
                video.status.value,
                video.download_status,
                video.view_count,
                video.webpage_url
            ])
```

**Benefits:**
- Easy analysis in Excel/Google Sheets
- Better for non-technical users
- Quick filtering and sorting

**Implementation Estimate:** ~50 lines of code

---

### 4. Geolocation Data (Optional)

**Current State:**
- Not extracted

**Enhancement:**
- Extract `recordingDetails.location` from video metadata
- Store latitude/longitude
- Generate Google Maps links

```python
# In models.py
@dataclass
class VideoMetadata:
    # ... existing fields ...
    geolocation: Optional[Dict[str, float]] = None  # {'lat': x, 'lng': y}

    def get_maps_url(self) -> Optional[str]:
        """Generate Google Maps URL for video location."""
        if self.geolocation:
            lat = self.geolocation['lat']
            lng = self.geolocation['lng']
            return f"https://maps.google.com/?q={lat},{lng}"
        return None
```

**Use Cases:**
- Travel vlogs
- Location-based playlists
- Geographic research

**Priority:** Low (niche use case)

---

### 5. Live Stream Metadata (Optional)

**Current State:**
- Basic duration/title only

**Enhancement:**
- Extract livestream-specific fields

```python
# In models.py
@dataclass
class VideoMetadata:
    # ... existing fields ...
    is_livestream: bool = False
    livestream_scheduled_start: Optional[str] = None
    livestream_actual_end: Optional[str] = None
    livestream_concurrent_viewers: Optional[int] = None
```

**Use Cases:**
- Livestream archives
- Event tracking
- Concurrent viewer statistics

**Priority:** Low (niche use case)

---

## What NOT to Take from youtube-metadata

### 1. YouTube API v3 Dependency
**Reason:** Your yt-dlp approach is superior
- ✅ No API quota limits
- ✅ No API key required
- ✅ More resilient to API changes
- ✅ Works with cookies for private playlists

### 2. Web-based UI
**Reason:** Desktop GUI is more appropriate
- ✅ Your PySide6 GUI is better for desktop use
- ✅ Better performance for large playlists
- ✅ Offline capability
- ✅ No browser dependency

### 3. JavaScript Stack
**Reason:** Python is the right choice
- ✅ Better integration with yt-dlp
- ✅ Easier file system operations
- ✅ Better performance for batch processing
- ✅ Existing ecosystem (Click, PySide6)

---

## Priority Recommendations

### ⭐⭐⭐ Priority 1: Filmot Integration

**Impact:** HIGH
**Effort:** MEDIUM (~100 lines)
**Value:** Fills biggest gap in current implementation

**Why:**
- Shows **what was deleted** instead of generic placeholders
- Major improvement for archival/research use cases
- Unique feature that sets you apart from basic downloaders

**Implementation Steps:**
1. Create `filmot_enricher.py` module
2. Add Filmot API integration
3. Update `playlist_fetcher.py` to use enricher
4. Add `[ARCHIVED]` prefix to enriched metadata
5. Test with known deleted videos

---

### ⭐⭐ Priority 2: Enhanced Thumbnail Storage

**Impact:** MEDIUM
**Effort:** LOW (~20 lines)
**Value:** Better deleted video identification

**Why:**
- Higher quality thumbnails for archival
- Better visual identification of deleted videos
- Flexible display options in GUI

---

### ⭐ Priority 3: CSV Export

**Impact:** MEDIUM
**Effort:** MEDIUM (~50 lines)
**Value:** Better data analysis for users

**Why:**
- Easier analysis in spreadsheets
- Better for non-technical users
- Complements existing JSON export

---

### Optional: Geolocation & Livestream Metadata

**Impact:** LOW
**Effort:** LOW-MEDIUM
**Value:** Niche use cases only

**When to implement:**
- Only if users explicitly request it
- After completing higher priority features

---

## Proposed Integration Architecture

### New Module: `filmot_enricher.py`

```
ytpl_downloader/
├── core/
│   ├── auth.py
│   ├── models.py
│   ├── playlist_fetcher.py
│   ├── storage.py
│   ├── downloader.py
│   └── filmot_enricher.py      # NEW: Filmot integration
```

### Modified Modules

1. **models.py**: Add optional fields for enhanced metadata
2. **playlist_fetcher.py**: Integrate Filmot enrichment
3. **storage.py**: Add CSV export method
4. **gui/main.py**: Add export options

---

## External Services Integration

### Filmot.com
- **Purpose:** Deleted video metadata recovery
- **Endpoint:** `https://filmot.com/api/getvideos?id={videoId}`
- **Rate Limits:** Unknown (implement respectful delays)
- **Cost:** Free

### Archive.org (Future Consideration)
- **Purpose:** Video thumbnail/content recovery
- **Endpoint:** Wayback Machine API
- **Use Case:** Fallback if Filmot doesn't have data

---

## Risks and Considerations

### Filmot Integration Risks

1. **Service Availability**
   - Filmot may go offline or change API
   - Mitigation: Graceful fallback, cache results

2. **Data Quality**
   - Not all deleted videos are archived
   - Metadata may be incomplete
   - Mitigation: Mark as `[ARCHIVED]` to indicate uncertainty

3. **Rate Limiting**
   - Unknown rate limits
   - Mitigation: Implement delays, respect robots.txt

4. **Legal/ToS**
   - Check Filmot terms of service
   - Ensure compliance with data usage policies

### Implementation Considerations

1. **Caching**: Cache Filmot responses to avoid repeated requests
2. **Timeout**: Set reasonable timeouts (10 seconds recommended)
3. **Error Handling**: Graceful degradation if Filmot unavailable
4. **User Privacy**: Don't send user's auth data to Filmot

---

## Conclusion

The **youtube-metadata** repository offers valuable insights, particularly for **deleted video metadata recovery** via Filmot integration. This feature would significantly enhance your playlist tracking capabilities and differentiate your tool from basic YouTube downloaders.

### Recommended Action Plan

1. **Phase 1** (Next Release - v1.2.0):
   - Implement Filmot integration for deleted videos
   - Add enhanced thumbnail storage

2. **Phase 2** (Future Release - v1.3.0):
   - Add CSV export functionality
   - Improve deleted video display in GUI

3. **Phase 3** (On Demand):
   - Geolocation metadata (if requested)
   - Livestream metadata (if requested)
   - Archive.org integration as Filmot fallback

### Expected Impact

- **User Value:** HIGH - Finally see what was deleted
- **Development Effort:** MEDIUM - ~150-200 lines total
- **Maintenance:** LOW - Minimal ongoing updates needed
- **Differentiation:** HIGH - Unique feature in this space

---

**Next Steps:**

Would you like me to implement the Filmot integration for v1.2.0?
