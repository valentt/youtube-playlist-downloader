"""Playlist fetcher module for extracting YouTube playlist metadata."""

import yt_dlp
import time
from typing import Optional, Dict, Any, List, Callable
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

    def fetch_playlist(
        self,
        playlist_url: str,
        quiet: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        fast_mode: bool = False
    ) -> PlaylistMetadata:
        """
        Fetch metadata for a YouTube playlist.

        Args:
            playlist_url: URL of the YouTube playlist
            quiet: If True, suppress yt-dlp output
            progress_callback: Optional callback(current, total, message) for progress updates
            fast_mode: If True, use fast fetch (30s-1min). If False, use detailed fetch (5-10min)

        Returns:
            PlaylistMetadata object with videos

        Raises:
            Exception: If playlist cannot be fetched

        Note:
            Fast mode: Quick fetch with basic info (title, ID, channel). ~30 seconds.
            Detailed mode: Full metadata including error messages. ~5-10 minutes for 200+ videos.
                Includes 1-2 second delay between videos to avoid YouTube rate-limiting.
                Unavailable/rate-limited videos are saved with UNAVAILABLE status.
        """
        # Extract playlist ID and create clean URL
        # Handles URLs like: https://www.youtube.com/watch?v=VIDEO&list=PLAYLIST
        import re
        playlist_id_match = re.search(r'[?&]list=([^&]+)', playlist_url)
        if playlist_id_match:
            playlist_id = playlist_id_match.group(1)
            # Use clean playlist URL for better compatibility with private playlists
            clean_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        else:
            clean_url = playlist_url

        # Base yt-dlp options
        # ALWAYS use extract_flat first to get all video IDs (including unavailable ones)
        # Then optionally enrich with detailed metadata
        ydl_opts = {
            'quiet': quiet,
            'no_warnings': quiet,
            'extract_flat': 'in_playlist',  # Always get basic info with IDs first
            'skip_download': True,  # Don't download videos
            'ignoreerrors': True,  # Continue on errors (unavailable videos)
            'yes_playlist': True,  # Force playlist extraction, don't fall back to video
        }

        # Add authentication if available
        auth_params = self.auth_manager.get_ytdlp_params()
        ydl_opts.update(auth_params)

        # Debug: Print authentication status
        if auth_params.get('cookiefile'):
            if not quiet:
                print(f"Using cookies from: {auth_params['cookiefile']}")
        else:
            if not quiet:
                print("WARNING: No authentication configured. Private playlists may not work.")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if not quiet:
                    print(f"Fetching playlist: {clean_url}")

                if progress_callback:
                    if fast_mode:
                        progress_callback(0, 1, "Fetching playlist (fast mode)...")
                    else:
                        progress_callback(0, 1, "Fetching detailed metadata... This may take 5-10 minutes for large playlists.")

                playlist_info = ydl.extract_info(clean_url, download=False)

                if not playlist_info:
                    raise Exception("Failed to fetch playlist information")

                if progress_callback and not fast_mode:
                    progress_callback(0, 1, "Processing fetched metadata...")

                # Create PlaylistMetadata object with progress tracking
                playlist = self._convert_playlist_info(playlist_info, progress_callback, quiet=quiet)

                if not quiet:
                    print(f"Fetched {len(playlist.videos)} videos from playlist: {playlist.title}")

                # If detailed mode, enrich with full metadata
                if not fast_mode:
                    if not quiet:
                        print(f"\nDetailed mode: Fetching full metadata for all videos...")

                    playlist = self.enrich_playlist_metadata(playlist, progress_callback)

                if progress_callback:
                    progress_callback(1, 1, "Complete!")

                return playlist

        except Exception as e:
            raise Exception(f"Error fetching playlist: {str(e)}")

    def _convert_playlist_info(
        self,
        info: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        quiet: bool = False
    ) -> PlaylistMetadata:
        """
        Convert yt-dlp playlist info to PlaylistMetadata.

        Args:
            info: Raw playlist info from yt-dlp
            progress_callback: Optional callback for progress updates
            quiet: If True, suppress print output

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
        total_videos = len(entries)

        if not quiet:
            print(f"\nProcessing {total_videos} videos from playlist...")
            print(f"Playlist: {playlist.title}")
            print(f"Channel: {playlist.channel or 'Unknown'}\n")

        for idx, entry in enumerate(entries, start=1):
            # Extract video ID helper function
            def extract_video_id(entry_data):
                """Try to extract video ID from entry, even for unavailable videos."""
                if not isinstance(entry_data, dict):
                    return None

                # Try direct ID field
                if entry_data.get('id'):
                    return entry_data['id']

                # Try to parse from URL or webpage_url
                import re
                for url_field in ['url', 'webpage_url', 'ie_key']:
                    url = entry_data.get(url_field, '')
                    if url and 'youtube.com' in url or 'youtu.be' in url:
                        # Extract video ID from YouTube URL
                        match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
                        if match:
                            return match.group(1)

                return None

            # Report progress - update every video for better feedback
            if progress_callback:
                if entry is None:
                    video_title = '[Unavailable Video]'
                else:
                    video_title = entry.get('title', 'Unknown') if isinstance(entry, dict) else 'Unknown'
                # Truncate long titles
                if len(video_title) > 50:
                    video_title = video_title[:47] + '...'
                progress_callback(idx, total_videos, f"Processing {idx}/{total_videos}: {video_title}")

            # Handle None entries (videos that failed to fetch due to errors/rate-limiting)
            if entry is None:
                # Create entry for unavailable video with placeholder ID
                # Note: When entry is None, yt-dlp provided no data at all for this video
                video_id = f'unavailable_{idx}'
                video = VideoMetadata(
                    video_id=video_id,
                    title=f'[Unavailable Video #{idx}]',
                    channel='Unknown',
                    channel_id='',
                    uploader='Unknown',
                    playlist_index=idx,
                    status=VideoStatus.UNAVAILABLE,
                    webpage_url='',
                    description='This video was completely unavailable during fetch. No video ID could be extracted.'
                )
                videos[video_id] = video
                continue

            # Try to extract video ID even if entry is minimal
            if not isinstance(entry, dict):
                video_id = f'invalid_{idx}'
                video = VideoMetadata(
                    video_id=video_id,
                    title=f'[Invalid Entry #{idx}]',
                    channel='Unknown',
                    channel_id='',
                    uploader='Unknown',
                    playlist_index=idx,
                    status=VideoStatus.UNAVAILABLE,
                    webpage_url=''
                )
                videos[video_id] = video
                continue

            # Always try to extract the video ID first
            video_id = extract_video_id(entry)

            try:
                video = self._convert_video_info(entry, playlist_index=idx)
                videos[video.video_id] = video
            except Exception as e:
                # Handle unavailable videos - but use extracted ID if we got one
                if not video_id:
                    video_id = f'unknown_{idx}'

                # Determine status from error or entry data
                status = VideoStatus.UNAVAILABLE
                error_msg = str(e).lower()
                if 'private' in error_msg or entry.get('availability') == 'private':
                    status = VideoStatus.PRIVATE
                elif 'deleted' in error_msg:
                    status = VideoStatus.DELETED

                video = VideoMetadata(
                    video_id=video_id,
                    title=entry.get('title', '[Unavailable Video]'),
                    channel=entry.get('channel') or entry.get('uploader', 'Unknown'),
                    channel_id=entry.get('channel_id', ''),
                    uploader=entry.get('uploader', 'Unknown'),
                    playlist_index=idx,
                    status=status,
                    webpage_url=entry.get('url', '') or entry.get('webpage_url', '') or f'https://www.youtube.com/watch?v={video_id}',
                    description=f'Error during fetch: {str(e)}'
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
            channel=info.get('channel') or info.get('uploader') or info.get('creator', 'Unknown'),
            channel_id=info.get('channel_id', '') or info.get('uploader_id', '') or info.get('channel_url', ''),
            uploader=info.get('uploader') or info.get('creator', 'Unknown'),
            upload_date=upload_date,
            duration=info.get('duration'),
            description=info.get('description', ''),
            # Save best quality thumbnail (important for deleted video identification)
            thumbnail=info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else ''),
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

    def fetch_video_metadata(self, video_id: str) -> Optional[VideoMetadata]:
        """
        Fetch detailed metadata for a single video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoMetadata object or None if video cannot be fetched
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
                    return None

                return self._convert_video_info(info)

        except Exception as e:
            print(f"Error fetching video {video_id}: {e}")
            return None

    def enrich_playlist_metadata(
        self,
        playlist: PlaylistMetadata,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> PlaylistMetadata:
        """
        Fetch detailed metadata for all videos in a playlist that lack it.

        Useful for upgrading a fast-fetched playlist to have detailed metadata.

        Args:
            playlist: PlaylistMetadata object to enrich
            progress_callback: Optional callback for progress updates

        Returns:
            Updated PlaylistMetadata with detailed info

        Note:
            Includes 1 second delay between video fetches to avoid YouTube rate-limiting.
        """
        total_videos = len(playlist.videos)
        print(f"\nEnriching playlist: {playlist.title}")
        print(f"Fetching detailed metadata for {total_videos} videos...")
        print("This may take several minutes. Progress will be shown below.\n")

        for idx, (video_id, video) in enumerate(playlist.videos.items(), start=1):
            # Skip placeholder IDs (unavailable_X, unknown_X, invalid_X)
            if video_id.startswith(('unavailable_', 'unknown_', 'invalid_')):
                print(f"[{idx}/{total_videos}] Skipping placeholder ID: {video_id}")
                if progress_callback:
                    progress_callback(idx, total_videos, f"Skipping {idx}/{total_videos}: {video.title[:50]}")
                continue

            # Truncate title for display
            display_title = video.title[:50] + '...' if len(video.title) > 50 else video.title

            print(f"[{idx}/{total_videos}] Enriching: {display_title}")

            if progress_callback:
                progress_callback(idx, total_videos, f"Enriching {idx}/{total_videos}: {display_title}")

            # Add delay to avoid rate-limiting (skip first iteration)
            if idx > 1:
                time.sleep(1)  # 1 second delay between fetches

            # Fetch detailed metadata
            detailed = self.fetch_video_metadata(video_id)

            if detailed:
                # Preserve existing data that shouldn't be overwritten
                detailed.download_status = video.download_status
                detailed.video_path = video.video_path
                detailed.audio_path = video.audio_path
                detailed.comments_path = video.comments_path
                detailed.first_seen = video.first_seen
                detailed.status_history = video.status_history
                detailed.playlist_index = video.playlist_index

                playlist.videos[video_id] = detailed
                print(f"  [OK] Enriched successfully")
            else:
                print(f"  [SKIP] Failed to fetch metadata")

        print(f"\nEnrichment complete! Updated {total_videos} videos.\n")
        return playlist

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
