"""Filmot.com integration for deleted video metadata recovery."""

import time
import requests
from typing import Optional, Dict, Any
from .models import VideoMetadata, VideoStatus


class FilmotEnricher:
    """Enrich deleted video metadata from Filmot archive."""

    BASE_URL = "https://filmot.com/api/getvideos"
    WEB_URL = "https://filmot.com/video"

    # Respectful delays to avoid overwhelming the service
    REQUEST_DELAY = 1.0  # seconds between requests

    def __init__(self):
        """Initialize Filmot enricher."""
        self.last_request_time = 0

    def _rate_limit(self):
        """Implement respectful rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()

    def get_deleted_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for deleted video from Filmot.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video metadata if found, None otherwise
        """
        try:
            # Rate limiting
            self._rate_limit()

            # Query Filmot API
            response = requests.get(
                f"{self.BASE_URL}?id={video_id}",
                timeout=10,
                headers={
                    'User-Agent': 'YouTube-Playlist-Downloader/1.2.0 (github.com/valentt/youtube-playlist-downloader)'
                }
            )

            if response.status_code == 200:
                data = response.json()

                # Filmot returns array of videos, get first result
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif isinstance(data, dict):
                    return data

            return None

        except requests.exceptions.Timeout:
            print(f"Filmot request timeout for video {video_id}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Filmot request failed for {video_id}: {e}")
            return None
        except Exception as e:
            print(f"Filmot enrichment error for {video_id}: {e}")
            return None

    def enrich_video_metadata(self, video: VideoMetadata) -> tuple[VideoMetadata, bool]:
        """
        Enrich unavailable video with Filmot data if available.

        Args:
            video: Video metadata to enrich

        Returns:
            Tuple of (enriched_video, was_enriched)
        """
        # Only enrich videos that are unavailable
        if video.status not in [VideoStatus.DELETED, VideoStatus.UNAVAILABLE, VideoStatus.PRIVATE]:
            return video, False

        # Skip if we don't have a valid video ID
        if not video.video_id or video.video_id.startswith(('unavailable_', 'unknown_', 'invalid_')):
            return video, False

        # Check if already enriched
        if video.description and '[ARCHIVED FROM FILMOT]' in video.description:
            return video, False

        # Query Filmot
        filmot_data = self.get_deleted_video_info(video.video_id)

        if not filmot_data:
            return video, False

        # Update video with archived data
        enriched = False

        # Title
        if 'title' in filmot_data and filmot_data['title']:
            if not video.title or video.title == video.video_id or 'Deleted video' in video.title:
                video.title = filmot_data['title']
                enriched = True

        # Channel name
        if 'channel_title' in filmot_data and filmot_data['channel_title']:
            if not video.channel or video.channel == 'Unknown':
                video.channel = filmot_data['channel_title']
                enriched = True

        # Channel ID
        if 'channel_id' in filmot_data and filmot_data['channel_id']:
            if not video.channel_id:
                video.channel_id = filmot_data['channel_id']
                enriched = True

        # Upload date (Filmot format: "YYYY-MM-DD HH:MM:SS")
        if 'published_at' in filmot_data and filmot_data['published_at']:
            if not video.upload_date:
                # Convert to YYYYMMDD format
                date_str = filmot_data['published_at'].split(' ')[0]  # Get date part
                video.upload_date = date_str.replace('-', '')  # YYYYMMDD
                enriched = True

        # View count
        if 'view_count' in filmot_data and filmot_data['view_count'] is not None:
            if video.view_count is None or video.view_count == 0:
                video.view_count = int(filmot_data['view_count'])
                enriched = True

        # Like count
        if 'like_count' in filmot_data and filmot_data['like_count'] is not None:
            if video.like_count is None:
                video.like_count = int(filmot_data['like_count'])
                enriched = True

        # Duration
        if 'duration' in filmot_data and filmot_data['duration']:
            if not video.duration:
                video.duration = self._parse_duration(filmot_data['duration'])
                enriched = True

        # Description
        if 'description' in filmot_data and filmot_data['description']:
            if not video.description or video.description == '':
                video.description = filmot_data['description']
                enriched = True

        # Mark as archived data
        if enriched:
            filmot_url = f"{self.WEB_URL}/{video.video_id}"
            archive_note = f"[ARCHIVED FROM FILMOT: {filmot_url}]"

            if video.description:
                video.description = f"{archive_note}\n\n{video.description}"
            else:
                video.description = archive_note

        return video, enriched

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """
        Parse duration string to seconds.

        Filmot formats: "HH:MM:SS" or "MM:SS" or "PT#M#S" (ISO 8601)

        Args:
            duration_str: Duration string

        Returns:
            Duration in seconds, or None if parsing fails
        """
        try:
            # Handle ISO 8601 format (PT1H2M3S)
            if duration_str.startswith('PT'):
                duration_str = duration_str[2:]  # Remove PT
                hours = 0
                minutes = 0
                seconds = 0

                if 'H' in duration_str:
                    hours, duration_str = duration_str.split('H')
                    hours = int(hours)
                if 'M' in duration_str:
                    minutes, duration_str = duration_str.split('M')
                    minutes = int(minutes)
                if 'S' in duration_str:
                    seconds = int(duration_str.replace('S', ''))

                return hours * 3600 + minutes * 60 + seconds

            # Handle HH:MM:SS or MM:SS format
            parts = duration_str.split(':')
            if len(parts) == 3:
                # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                # SS
                return int(parts[0])

            return None

        except (ValueError, AttributeError):
            return None

    def enrich_playlist(
        self,
        videos: list[VideoMetadata],
        progress_callback=None
    ) -> tuple[int, int]:
        """
        Enrich multiple videos from a playlist.

        Args:
            videos: List of videos to enrich
            progress_callback: Optional callback(current, total, video_id, success)

        Returns:
            Tuple of (enriched_count, total_attempted)
        """
        enriched_count = 0
        attempted_count = 0

        # Filter to only unavailable videos
        unavailable_videos = [
            v for v in videos
            if v.status in [VideoStatus.DELETED, VideoStatus.UNAVAILABLE, VideoStatus.PRIVATE]
        ]

        total = len(unavailable_videos)

        for i, video in enumerate(unavailable_videos, 1):
            attempted_count += 1

            enriched_video, was_enriched = self.enrich_video_metadata(video)

            if was_enriched:
                enriched_count += 1

            if progress_callback:
                progress_callback(i, total, video.video_id, was_enriched)

        return enriched_count, attempted_count

    def get_filmot_web_url(self, video_id: str) -> str:
        """
        Get Filmot web URL for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Filmot web URL
        """
        return f"{self.WEB_URL}/{video_id}"


def test_filmot_enricher():
    """Test Filmot enricher with a known deleted video."""
    enricher = FilmotEnricher()

    # Test with a known deleted video ID (you'll need to replace with actual deleted video)
    test_video_id = "dQw4w9WgXcQ"  # Replace with actual deleted video

    print(f"Testing Filmot enricher with video: {test_video_id}")

    # Create test video metadata
    from .models import VideoMetadata
    test_video = VideoMetadata(
        video_id=test_video_id,
        title="[Deleted Video]",
        channel="Unknown",
        status=VideoStatus.DELETED
    )

    # Enrich
    enriched, was_enriched = enricher.enrich_video_metadata(test_video)

    if was_enriched:
        print(f"✓ Successfully enriched video:")
        print(f"  Title: {enriched.title}")
        print(f"  Channel: {enriched.channel}")
        print(f"  Upload Date: {enriched.upload_date}")
        print(f"  Views: {enriched.view_count}")
    else:
        print(f"✗ Could not enrich video (may not be in Filmot archive)")


if __name__ == '__main__':
    test_filmot_enricher()
