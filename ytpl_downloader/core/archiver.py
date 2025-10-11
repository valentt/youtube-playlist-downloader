"""Archive.org upload manager for preserving YouTube videos."""

import os
import re
import time
import json
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .models import VideoMetadata, PlaylistMetadata, VideoStatus, ArchiveStatus
from .storage import PlaylistStorage


class UploadProgress:
    """Tracks upload progress with two phases: caching and uploading."""

    def __init__(self, filename: str, file_size: int):
        self.filename = filename
        self.file_size = file_size
        self.bytes_sent = 0
        self.start_time = time.time()
        self.last_update_time = time.time()

        # Phase tracking (caching vs uploading)
        self.phase = "caching"  # "caching" or "uploading"
        self.phase_start_bytes = 0
        self.phase_start_time = time.time()
        self.caching_complete = False

        # Sliding window for speed calculation
        self.speed_window = []  # List of (timestamp, bytes_sent) tuples
        self.window_size = 2.0  # seconds

        # Speed threshold to detect phase transition (MB/s)
        # If speed drops below this, we've switched from caching to uploading
        self.speed_threshold = 10.0  # MB/s
        self.min_samples_for_transition = 3  # Need consistent slow speed

    def update(self, bytes_sent: int):
        """Update progress with new bytes sent."""
        current_time = time.time()
        self.bytes_sent = bytes_sent
        self.last_update_time = current_time

        # Add to sliding window
        self.speed_window.append((current_time, bytes_sent))

        # Remove old entries outside window
        cutoff_time = current_time - self.window_size
        self.speed_window = [(t, b) for t, b in self.speed_window if t > cutoff_time]

        # Detect phase transition from caching to uploading
        if self.phase == "caching" and len(self.speed_window) >= self.min_samples_for_transition:
            current_speed = self._calculate_speed()

            # If speed has dropped significantly, we've finished caching
            if current_speed < self.speed_threshold and current_speed > 0:
                self.phase = "uploading"
                self.phase_start_bytes = bytes_sent
                self.phase_start_time = current_time
                self.caching_complete = True

    def _calculate_speed(self) -> float:
        """Calculate current speed in MB/s."""
        if len(self.speed_window) < 2:
            return 0.0

        oldest_time, oldest_bytes = self.speed_window[0]
        newest_time, newest_bytes = self.speed_window[-1]

        time_diff = newest_time - oldest_time
        bytes_diff = newest_bytes - oldest_bytes

        if time_diff == 0:
            return 0.0

        mb_sent = bytes_diff / (1024 * 1024)
        return mb_sent / time_diff

    @property
    def should_report(self) -> bool:
        """Always report progress."""
        return True

    @property
    def percentage(self) -> int:
        """Calculate percentage complete for current phase."""
        if self.file_size == 0:
            return 0

        if self.phase == "caching":
            # First pass through file (0-100%)
            pct = int((self.bytes_sent / self.file_size) * 100)
            return min(100, pct)
        else:
            # Second pass (uploading) - calculate from phase start
            bytes_in_phase = self.bytes_sent - self.phase_start_bytes
            pct = int((bytes_in_phase / self.file_size) * 100)
            return min(100, pct)

    @property
    def speed_mbps(self) -> float:
        """Calculate speed in MB/s."""
        if self.phase == "caching":
            # Don't show speed during caching (too fast to be meaningful)
            return 0.0
        else:
            return self._calculate_speed()

    @property
    def eta_seconds(self) -> int:
        """Calculate estimated time remaining in seconds."""
        if self.phase == "caching":
            return 0  # Don't show ETA during caching

        speed = self.speed_mbps
        if speed == 0:
            return 0

        bytes_in_phase = self.bytes_sent - self.phase_start_bytes
        bytes_remaining = max(0, self.file_size - bytes_in_phase)
        mb_remaining = bytes_remaining / (1024 * 1024)

        return int(mb_remaining / speed)

    @property
    def status_message(self) -> str:
        """Get current phase status message."""
        if self.phase == "caching":
            return "Caching"
        else:
            return "Uploading"

    @property
    def bytes_in_current_phase(self) -> int:
        """Get bytes processed in current phase (for display purposes)."""
        if self.phase == "caching":
            return self.bytes_sent
        else:
            # Uploading phase - return bytes since phase started
            return self.bytes_sent - self.phase_start_bytes


class ProgressFileWrapper:
    """File wrapper that tracks read progress for uploads."""

    def __init__(self, filepath: Path, progress_tracker: UploadProgress, callback: Optional[Callable] = None):
        self.filepath = filepath
        self.progress = progress_tracker
        self.callback = callback
        self.file = None

    def __enter__(self):
        self.file = open(self.filepath, 'rb')
        return self

    def __exit__(self, *args):
        if self.file:
            self.file.close()

    def read(self, size=-1):
        """Read from file and update progress."""
        chunk = self.file.read(size)
        if chunk:
            self.progress.update(self.progress.bytes_sent + len(chunk))
            # Call progress callback with phase info
            if self.callback and self.progress.should_report:
                self.callback(
                    self.progress.filename,
                    self.progress.bytes_in_current_phase,  # Phase-relative bytes
                    self.progress.file_size,
                    self.progress.speed_mbps,
                    self.progress.percentage,
                    self.progress.status_message
                )
        return chunk

    def seek(self, *args, **kwargs):
        return self.file.seek(*args, **kwargs)

    def tell(self):
        return self.file.tell()

    def __iter__(self):
        return iter(self.file)

    def __next__(self):
        return next(self.file)


class ArchiveManager:
    """Manages uploading videos to Internet Archive."""

    def __init__(self, storage: PlaylistStorage):
        """
        Initialize the archive manager.

        Args:
            storage: PlaylistStorage instance for updating metadata
        """
        self.storage = storage

    def upload_video(
        self,
        video: VideoMetadata,
        playlist: PlaylistMetadata,
        video_path: Optional[Path] = None,
        audio_path: Optional[Path] = None,
        comments_path: Optional[Path] = None,
        retries: int = 3,
        skip_live: bool = False,  # Default: archive all videos when explicitly requested
        progress_callback: Optional[Callable[[str, int, int, float, int, str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Upload a single video to archive.org.

        Args:
            video: Video metadata
            playlist: Parent playlist metadata
            video_path: Path to video file (if downloaded)
            audio_path: Path to audio file (if downloaded)
            comments_path: Path to comments markdown (if downloaded)
            retries: Number of retry attempts on failure
            skip_live: Skip videos with LIVE status
            progress_callback: Function(filename, bytes_sent, total_bytes, speed_mbps, percentage, status) for progress updates

        Returns:
            (success: bool, message: str)
        """
        try:
            from internetarchive import get_item
        except ImportError:
            return (False, "internetarchive library not installed")

        # Pre-upload validation
        should_upload, reason = self._should_archive_video(
            video, video_path, audio_path, comments_path, skip_live
        )

        if not should_upload:
            return (False, f"Skipped: {reason}")

        # Generate identifier
        identifier = self._generate_identifier(video.video_id)

        # Check if item already exists
        exists, is_ours, existing_url = self._check_item_exists(identifier, video)

        if exists:
            if is_ours:
                return (False, f"Already archived at {existing_url}")
            else:
                # Item exists but uploaded by someone else
                video.archive_status = ArchiveStatus.SKIPPED
                video.archive_url = existing_url
                video.archive_identifier = identifier
                return (False, f"Already exists (by another user): {existing_url}")

        # Prepare files for upload
        files_to_upload = {}

        if video_path and video_path.exists():
            files_to_upload[video_path.name] = str(video_path)

        if audio_path and audio_path.exists():
            files_to_upload[audio_path.name] = str(audio_path)

        if comments_path and comments_path.exists():
            files_to_upload[comments_path.name] = str(comments_path)

        # Create metadata JSON
        metadata_json = self._create_metadata_json(video)
        metadata_filename = f"{identifier}_metadata.json"

        # Write metadata to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(metadata_json)
            temp_metadata_path = f.name

        files_to_upload[metadata_filename] = temp_metadata_path

        # Generate archive.org item metadata
        ia_metadata = self._create_metadata(video, playlist)

        # Upload with retries
        for attempt in range(retries):
            try:
                # Update status
                video.archive_status = ArchiveStatus.UPLOADING

                # Get item
                item = get_item(identifier)

                # Upload files
                self._upload_files(
                    item=item,
                    files=files_to_upload,
                    metadata=ia_metadata,
                    progress_callback=progress_callback
                )

                # Success!
                archive_url = f"https://archive.org/details/{identifier}"
                video.archive_status = ArchiveStatus.ARCHIVED
                video.archive_identifier = identifier
                video.archive_url = archive_url
                video.archive_date = datetime.now().isoformat()
                video.archive_error = None

                # Cleanup temp file
                try:
                    os.unlink(temp_metadata_path)
                except:
                    pass

                return (True, f"Archived successfully: {archive_url}")

            except Exception as e:
                error_msg = str(e)

                if attempt < retries - 1:
                    # Wait before retry (exponential backoff)
                    sleep_time = (2 ** attempt) * 30  # 30s, 60s, 120s
                    time.sleep(sleep_time)
                else:
                    # Final attempt failed
                    video.archive_status = ArchiveStatus.FAILED
                    video.archive_error = error_msg

                    # Cleanup temp file
                    try:
                        os.unlink(temp_metadata_path)
                    except:
                        pass

                    return (False, f"Upload failed after {retries} attempts: {error_msg}")

        return (False, "Upload failed")

    def upload_batch(
        self,
        videos: List[VideoMetadata],
        playlist: PlaylistMetadata,
        max_workers: int = 3,
        progress_callback: Optional[Callable[[str, bool, str], None]] = None,
        stop_event: Optional[threading.Event] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Upload multiple videos in parallel.

        Args:
            videos: List of videos to upload
            playlist: Parent playlist metadata
            max_workers: Number of parallel uploads
            progress_callback: Function(video_id, success, message) called after each upload
            stop_event: Threading event to signal stop request

        Returns:
            Dictionary mapping video_id to (success, message)
        """
        results = {}

        for video in videos:
            # Check stop signal
            if stop_event and stop_event.is_set():
                break

            # Get file paths
            video_path = Path(video.video_path) if video.video_path else None
            audio_path = Path(video.audio_path) if video.audio_path else None
            comments_path = Path(video.comments_path) if video.comments_path else None

            # Upload
            success, message = self.upload_video(
                video, playlist,
                video_path, audio_path, comments_path
            )

            results[video.video_id] = (success, message)

            # Save after each upload
            self.storage.save_playlist(playlist)

            # Notify callback
            if progress_callback:
                progress_callback(video.video_id, success, message)

        return results

    def _should_archive_video(
        self,
        video: VideoMetadata,
        video_path: Optional[Path],
        audio_path: Optional[Path],
        comments_path: Optional[Path],
        skip_live: bool
    ) -> Tuple[bool, str]:
        """
        Determine if video should be archived.

        Returns:
            (should_archive: bool, reason: str)
        """
        # Check if already archived
        if video.archive_status == ArchiveStatus.ARCHIVED:
            return (False, "Already archived")

        # Check if any files available
        has_files = any([
            video_path and video_path.exists(),
            audio_path and audio_path.exists(),
            comments_path and comments_path.exists()
        ])

        if not has_files:
            return (False, "No files to archive")

        # Check video status (optional - can be overridden with skip_live=False)
        if video.status == VideoStatus.LIVE and skip_live:
            return (False, "Video still available on YouTube (skipping by policy)")

        return (True, "Ready to archive")

    def _generate_identifier(self, video_id: str) -> str:
        """
        Generate archive.org identifier.

        Args:
            video_id: YouTube video ID

        Returns:
            Archive.org identifier (e.g., "youtube-dQw4w9WgXcQ")
        """
        # Sanitize to meet IA requirements (alphanumeric, dash, underscore)
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
        return f"youtube-{safe_id}"

    def _check_item_exists(
        self,
        identifier: str,
        video: VideoMetadata
    ) -> Tuple[bool, bool, Optional[str]]:
        """
        Check if item exists on archive.org and if we uploaded it.

        Args:
            identifier: Archive.org identifier
            video: Video metadata

        Returns:
            (exists: bool, is_ours: bool, url: Optional[str])
        """
        try:
            from internetarchive import get_item

            item = get_item(identifier)

            # Check if item exists
            if item.exists:
                url = f"https://archive.org/details/{identifier}"

                # Check if it's ours by comparing video_id in metadata
                item_metadata = item.item_metadata.get('metadata', {})
                stored_video_id = item_metadata.get('youtube_video_id')

                is_ours = (stored_video_id == video.video_id)

                return (True, is_ours, url)

            return (False, False, None)

        except Exception as e:
            # If we can't check, assume it doesn't exist
            return (False, False, None)

    def _create_metadata(
        self,
        video: VideoMetadata,
        playlist: PlaylistMetadata
    ) -> Dict[str, Any]:
        """
        Generate comprehensive Internet Archive metadata.

        Args:
            video: Video metadata
            playlist: Parent playlist metadata

        Returns:
            Metadata dictionary for archive.org
        """
        metadata = {
            'mediatype': 'movies',
            'collection': 'opensource_movies',
            'title': video.title or 'Untitled',
            'creator': video.channel or playlist.channel or 'Unknown',
            'description': self._format_description(video, playlist),
            'subject': self._generate_tags(video),
            'language': 'eng',  # Default to English
            'originalurl': video.webpage_url or f'https://youtube.com/watch?v={video.video_id}',
        }

        # Add date if available
        if video.upload_date:
            try:
                # Convert YYYYMMDD to YYYY-MM-DD
                if len(video.upload_date) == 8 and video.upload_date.isdigit():
                    formatted_date = f"{video.upload_date[:4]}-{video.upload_date[4:6]}-{video.upload_date[6:8]}"
                    metadata['date'] = formatted_date
                else:
                    metadata['date'] = video.upload_date
            except:
                pass

        # Add runtime if available
        if video.duration:
            metadata['runtime'] = self._format_runtime(video.duration)

        # Add video-specific metadata
        metadata['sound'] = 'sound'
        metadata['color'] = 'color'
        metadata['aspect_ratio'] = '16:9'

        # Add YouTube-specific custom metadata
        metadata['youtube_video_id'] = video.video_id
        metadata['youtube_channel'] = video.channel or 'Unknown'
        metadata['youtube_channel_id'] = video.channel_id or ''
        metadata['youtube_upload_date'] = video.upload_date or ''

        if video.view_count is not None:
            metadata['youtube_view_count'] = str(video.view_count)
        if video.like_count is not None:
            metadata['youtube_like_count'] = str(video.like_count)
        if video.comment_count is not None:
            metadata['youtube_comment_count'] = str(video.comment_count)

        # Add archival metadata
        metadata['archived_date'] = datetime.now().isoformat()
        metadata['archived_reason'] = self._get_archive_reason(video)

        return metadata

    def _format_description(
        self,
        video: VideoMetadata,
        playlist: PlaylistMetadata
    ) -> str:
        """
        Format description with archival context.

        Args:
            video: Video metadata
            playlist: Parent playlist metadata

        Returns:
            Formatted description
        """
        parts = []

        # Original description
        if video.description:
            parts.append("=== Original YouTube Description ===")
            parts.append(video.description)
            parts.append("")

        # Archival information
        parts.append("=== Archival Information ===")
        parts.append(f"Archived from YouTube: {video.webpage_url or f'https://youtube.com/watch?v={video.video_id}'}")
        parts.append(f"Original Channel: {video.channel or 'Unknown'}")

        if video.upload_date:
            parts.append(f"Original Upload Date: {video.upload_date}")

        parts.append(f"Archived Date: {datetime.now().strftime('%Y-%m-%d')}")
        parts.append(f"Status at Archive Time: {video.status.value}")
        parts.append(f"Playlist: {playlist.title}")

        if video.view_count is not None:
            parts.append(f"Views: {video.view_count:,}")
        if video.like_count is not None:
            parts.append(f"Likes: {video.like_count:,}")
        if video.comment_count is not None:
            parts.append(f"Comments: {video.comment_count:,}")

        parts.append("")
        parts.append("This video was archived for preservation purposes using YouTube Playlist Downloader.")
        parts.append("https://github.com/valentt/youtube-playlist-downloader")

        return "\n".join(parts)

    def _generate_tags(self, video: VideoMetadata) -> List[str]:
        """
        Generate subject tags from video metadata.

        Args:
            video: Video metadata

        Returns:
            List of tags
        """
        tags = ['youtube', 'video', 'archived']

        # Add video tags
        if video.tags:
            tags.extend(video.tags[:10])  # Limit to 10 tags

        # Add categories
        if video.categories:
            tags.extend(video.categories)

        # Add status-based tags
        if video.status == VideoStatus.DELETED:
            tags.append('deleted')
        elif video.status == VideoStatus.PRIVATE:
            tags.append('private')
        elif video.status == VideoStatus.UNAVAILABLE:
            tags.append('unavailable')

        # Remove duplicates and return
        return list(set(tags))

    def _format_runtime(self, duration: int) -> str:
        """
        Convert duration in seconds to HH:MM:SS format.

        Args:
            duration: Duration in seconds

        Returns:
            Formatted runtime string
        """
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _get_archive_reason(self, video: VideoMetadata) -> str:
        """
        Determine archival reason from video status.

        Args:
            video: Video metadata

        Returns:
            Archival reason string
        """
        if video.status == VideoStatus.DELETED:
            return 'deleted'
        elif video.status == VideoStatus.PRIVATE:
            return 'private'
        elif video.status == VideoStatus.UNAVAILABLE:
            return 'unavailable'
        else:
            return 'user_request'

    def _create_metadata_json(self, video: VideoMetadata) -> str:
        """
        Create metadata JSON file content (full video metadata).

        Args:
            video: Video metadata

        Returns:
            JSON string
        """
        return json.dumps(video.to_dict(), indent=2)

    def _upload_files(
        self,
        item: Any,
        files: Dict[str, str],
        metadata: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int, int, float, int, str], None]] = None
    ) -> None:
        """
        Upload files to archive.org item with progress tracking.

        Args:
            item: internetarchive.Item instance
            files: Dictionary mapping remote filename to local filepath
            metadata: Item metadata
            progress_callback: Function(filename, bytes_sent, total_bytes, speed_mbps, percentage, status) for progress updates
        """
        # Upload each file individually with progress tracking
        for remote_name, local_path in files.items():
            filepath = Path(local_path)

            if not filepath.exists():
                continue

            file_size = filepath.stat().st_size

            # Create progress tracker
            progress = UploadProgress(remote_name, file_size)

            # Wrap file with progress tracking
            with ProgressFileWrapper(filepath, progress, progress_callback) as wrapped_file:
                # Upload single file with wrapped progress
                # Note: internetarchive library accepts file-like objects
                response = item.upload(
                    {remote_name: wrapped_file},
                    metadata=metadata if remote_name == list(files.keys())[0] else {},
                    verbose=False,
                    retries=3,
                    retries_sleep=30,
                    checksum=True,
                    queue_derive=False  # Only derive after all files uploaded
                )

            # Report 100% completion
            if progress_callback and file_size > 0:
                progress_callback(
                    remote_name,
                    file_size,
                    file_size,
                    progress.speed_mbps,
                    100,
                    "Uploading"
                )

        # Queue derivation after all files are uploaded
        try:
            item.modify_metadata({'queue-derive': '1'})
        except:
            pass  # Not critical if this fails


def sanitize_identifier(identifier: str) -> str:
    """
    Ensure identifier meets archive.org requirements.

    Args:
        identifier: Proposed identifier

    Returns:
        Sanitized identifier (alphanumeric, dash, underscore only)
    """
    return re.sub(r'[^a-zA-Z0-9_-]', '', identifier)


def validate_metadata(metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate metadata meets archive.org requirements.

    Args:
        metadata: Metadata dictionary

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    required_fields = ['mediatype', 'title']

    for field in required_fields:
        if field not in metadata or not metadata[field]:
            return (False, f"Missing required field: {field}")

    return (True, None)


def format_file_size(bytes_size: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"
