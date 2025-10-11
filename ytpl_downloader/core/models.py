"""Data models for YouTube playlist tracking."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class VideoStatus(str, Enum):
    """Status of a video in the playlist."""
    LIVE = "live"
    DELETED = "deleted"
    PRIVATE = "private"
    UNAVAILABLE = "unavailable"


class DownloadStatus(str, Enum):
    """Download status of a video."""
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class ArchiveStatus(str, Enum):
    """Archive.org upload status of a video."""
    NOT_ARCHIVED = "not_archived"
    UPLOADING = "uploading"
    ARCHIVED = "archived"
    FAILED = "failed"
    SKIPPED = "skipped"  # Already exists on IA by someone else


@dataclass
class StatusChange:
    """Represents a status change event for a video."""
    timestamp: str
    old_status: str
    new_status: str
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoMetadata:
    """Complete metadata for a YouTube video."""
    video_id: str
    title: str
    channel: str
    channel_id: str
    uploader: str
    upload_date: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    webpage_url: str = ""

    # Playlist-specific metadata
    playlist_index: int = 0

    # Status tracking
    status: VideoStatus = VideoStatus.LIVE
    download_status: DownloadStatus = DownloadStatus.NOT_DOWNLOADED

    # File paths
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    comments_path: Optional[str] = None

    # Archive.org tracking
    archive_status: ArchiveStatus = ArchiveStatus.NOT_ARCHIVED
    archive_identifier: Optional[str] = None  # e.g., "youtube-dQw4w9WgXcQ"
    archive_url: Optional[str] = None  # Full URL to archive.org item
    archive_date: Optional[str] = None  # ISO format timestamp
    archive_error: Optional[str] = None  # Last error message if failed

    # Timestamps
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checked: str = field(default_factory=lambda: datetime.now().isoformat())
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())

    # History
    status_history: List[StatusChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['download_status'] = self.download_status.value
        data['archive_status'] = self.archive_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoMetadata':
        """Create from dictionary (JSON deserialization)."""
        # Convert status strings to enums
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = VideoStatus(data['status'])
        if 'download_status' in data and isinstance(data['download_status'], str):
            data['download_status'] = DownloadStatus(data['download_status'])
        if 'archive_status' in data and isinstance(data['archive_status'], str):
            data['archive_status'] = ArchiveStatus(data['archive_status'])

        # Convert status_history dicts to StatusChange objects
        if 'status_history' in data:
            data['status_history'] = [
                StatusChange(**change) if isinstance(change, dict) else change
                for change in data['status_history']
            ]

        return cls(**data)

    def update_status(self, new_status: VideoStatus, note: Optional[str] = None):
        """Update video status and record the change in history."""
        if self.status != new_status:
            change = StatusChange(
                timestamp=datetime.now().isoformat(),
                old_status=self.status.value,
                new_status=new_status.value,
                note=note
            )
            self.status_history.append(change)
            self.status = new_status
            self.last_modified = datetime.now().isoformat()


@dataclass
class PlaylistMetadata:
    """Metadata for a YouTube playlist."""
    playlist_id: str
    title: str
    description: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    uploader: Optional[str] = None
    video_count: int = 0
    webpage_url: str = ""

    # Tracking
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Videos
    videos: Dict[str, VideoMetadata] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['videos'] = {vid_id: video.to_dict() for vid_id, video in self.videos.items()}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistMetadata':
        """Create from dictionary (JSON deserialization)."""
        if 'videos' in data:
            data['videos'] = {
                vid_id: VideoMetadata.from_dict(video) if isinstance(video, dict) else video
                for vid_id, video in data['videos'].items()
            }
        return cls(**data)


@dataclass
class PlaylistVersion:
    """A snapshot/version of a playlist at a specific time."""
    version: int
    timestamp: str
    videos_added: List[str] = field(default_factory=list)
    videos_removed: List[str] = field(default_factory=list)
    videos_status_changed: List[Dict[str, Any]] = field(default_factory=list)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistVersion':
        return cls(**data)
