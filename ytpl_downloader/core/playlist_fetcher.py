"""Playlist fetcher module for extracting YouTube playlist metadata."""

import yt_dlp
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from .models import PlaylistMetadata, VideoMetadata, VideoStatus
from .auth import AuthManager


class PlaylistFetcher:
    """Fetches YouTube playlist metadata using yt-dlp."""

    def __init__(self, auth_manager: Optional[AuthManager] = None):
        """
        Initialize the playlist fetcher.

        Args:
            auth_manager: AuthManager instance for authentication
        """
        self.auth_manager = auth_manager or AuthManager()

    def fetch_playlist(self, playlist_url: str, quiet: bool = False) -> PlaylistMetadata:
        """
        Fetch complete metadata for a YouTube playlist.

        Args:
            playlist_url: URL of the YouTube playlist
            quiet: If True, suppress yt-dlp output

        Returns:
            PlaylistMetadata object with all videos

        Raises:
            Exception: If playlist cannot be fetched
        """
        # Base yt-dlp options
        ydl_opts = {
            'quiet': quiet,
            'no_warnings': quiet,
            'extract_flat': False,  # Get full metadata for each video
            'skip_download': True,  # Don't download videos
            'ignoreerrors': True,  # Continue on errors (unavailable videos)
        }

        # Add authentication if available
        auth_params = self.auth_manager.get_ytdlp_params()
        ydl_opts.update(auth_params)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if not quiet:
                    print(f"Fetching playlist: {playlist_url}")

                playlist_info = ydl.extract_info(playlist_url, download=False)

                if not playlist_info:
                    raise Exception("Failed to fetch playlist information")

                # Create PlaylistMetadata object
                playlist = self._convert_playlist_info(playlist_info)

                if not quiet:
                    print(f"Fetched {len(playlist.videos)} videos from playlist: {playlist.title}")

                return playlist

        except Exception as e:
            raise Exception(f"Error fetching playlist: {str(e)}")

    def _convert_playlist_info(self, info: Dict[str, Any]) -> PlaylistMetadata:
        """
        Convert yt-dlp playlist info to PlaylistMetadata.

        Args:
            info: Raw playlist info from yt-dlp

        Returns:
            PlaylistMetadata object
        """
        playlist_id = info.get('id', '')

        playlist = PlaylistMetadata(
            playlist_id=playlist_id,
            title=info.get('title', 'Unknown Playlist'),
            description=info.get('description'),
            channel=info.get('channel') or info.get('uploader'),
            channel_id=info.get('channel_id') or info.get('uploader_id'),
            uploader=info.get('uploader'),
            webpage_url=info.get('webpage_url', ''),
        )

        # Process each video in the playlist
        entries = info.get('entries', [])
        videos = {}

        for idx, entry in enumerate(entries, start=1):
            if entry is None:
                # Video might be unavailable/deleted
                continue

            try:
                video = self._convert_video_info(entry, playlist_index=idx)
                videos[video.video_id] = video
            except Exception as e:
                # Handle unavailable videos
                video_id = entry.get('id', f'unknown_{idx}')
                video = VideoMetadata(
                    video_id=video_id,
                    title=entry.get('title', '[Unavailable Video]'),
                    channel='Unknown',
                    channel_id='',
                    uploader='Unknown',
                    playlist_index=idx,
                    status=VideoStatus.UNAVAILABLE,
                    webpage_url=entry.get('url', '') or entry.get('webpage_url', '')
                )
                videos[video_id] = video

        playlist.videos = videos
        playlist.video_count = len(videos)

        return playlist

    def _convert_video_info(self, info: Dict[str, Any], playlist_index: int = 0) -> VideoMetadata:
        """
        Convert yt-dlp video info to VideoMetadata.

        Args:
            info: Raw video info from yt-dlp
            playlist_index: Position in playlist

        Returns:
            VideoMetadata object
        """
        # Handle unavailable videos
        if info.get('_type') == 'url' and not info.get('duration'):
            # This might be a private or deleted video
            status = VideoStatus.UNAVAILABLE
        else:
            status = VideoStatus.LIVE

        # Extract upload date
        upload_date = info.get('upload_date')
        if upload_date:
            # Convert YYYYMMDD to YYYY-MM-DD
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        video = VideoMetadata(
            video_id=info.get('id', ''),
            title=info.get('title', '[Unknown]'),
            channel=info.get('channel') or info.get('uploader', 'Unknown'),
            channel_id=info.get('channel_id', '') or info.get('uploader_id', ''),
            uploader=info.get('uploader', 'Unknown'),
            upload_date=upload_date,
            duration=info.get('duration'),
            description=info.get('description'),
            thumbnail=info.get('thumbnail'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            tags=info.get('tags', []) or [],
            categories=info.get('categories', []) or [],
            webpage_url=info.get('webpage_url', '') or f"https://www.youtube.com/watch?v={info.get('id', '')}",
            playlist_index=playlist_index,
            status=status,
        )

        return video

    def check_video_availability(self, video_id: str) -> VideoStatus:
        """
        Check if a specific video is still available.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoStatus indicating availability
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'ignoreerrors': True,
        }

        # Add authentication if available
        auth_params = self.auth_manager.get_ytdlp_params()
        ydl_opts.update(auth_params)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(url, download=False)

                if info is None:
                    return VideoStatus.UNAVAILABLE

                # Check for private/deleted indicators
                if info.get('is_private'):
                    return VideoStatus.PRIVATE
                elif info.get('availability') in ['private', 'premium_only', 'subscriber_only']:
                    return VideoStatus.PRIVATE
                elif info.get('availability') in ['needs_auth', 'unlisted']:
                    # Unlisted videos can still be accessed with the link
                    return VideoStatus.LIVE
                else:
                    return VideoStatus.LIVE

        except Exception as e:
            error_msg = str(e).lower()
            if 'private' in error_msg:
                return VideoStatus.PRIVATE
            elif 'deleted' in error_msg or 'not available' in error_msg:
                return VideoStatus.DELETED
            else:
                return VideoStatus.UNAVAILABLE
