"""Download manager for YouTube videos with parallel downloads and resume capability."""

import yt_dlp
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

from .models import PlaylistMetadata, VideoMetadata, DownloadStatus, VideoStatus
from .auth import AuthManager
from .storage import PlaylistStorage


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for cross-platform compatibility.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters for Windows/Linux
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Trim spaces and dots from the end
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


class DownloadProgress:
    """Progress information for a download."""

    def __init__(self, video_id: str, title: str):
        self.video_id = video_id
        self.title = title
        self.status = DownloadStatus.DOWNLOADING
        self.progress_percent = 0.0
        self.speed = ""
        self.eta = ""
        self.error = None


class DownloadManager:
    """Manages video downloads with parallel processing and resume capability."""

    def __init__(
        self,
        auth_manager: Optional[AuthManager] = None,
        storage: Optional[PlaylistStorage] = None,
        download_dir: Optional[Path] = None,
        max_workers: int = 5
    ):
        """
        Initialize the download manager.

        Args:
            auth_manager: AuthManager instance for authentication
            storage: PlaylistStorage instance
            download_dir: Base directory for downloads. Defaults to ./downloads
            max_workers: Maximum number of parallel downloads
        """
        self.auth_manager = auth_manager or AuthManager()
        self.storage = storage or PlaylistStorage()

        if download_dir is None:
            download_dir = Path.cwd() / 'downloads'

        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers

    def get_playlist_download_dir(self, playlist: PlaylistMetadata) -> Path:
        """Get download directory for a specific playlist."""
        safe_title = sanitize_filename(playlist.title)
        playlist_dir = self.download_dir / safe_title
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return playlist_dir

    def download_video(
        self,
        video: VideoMetadata,
        output_dir: Path,
        quality: str = "1080p",
        audio_only: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> bool:
        """
        Download a single video.

        Args:
            video: VideoMetadata object
            output_dir: Directory to save the video
            quality: Video quality (e.g., "1080p", "720p", "best")
            audio_only: If True, download audio only
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        if video.status != VideoStatus.LIVE:
            print(f"Skipping {video.title} - Status: {video.status.value}")
            return False

        # Create filename with playlist index
        safe_title = sanitize_filename(video.title)
        index_str = f"{video.playlist_index:03d}"
        filename_base = f"{index_str} - {safe_title}"

        output_template = str(output_dir / f"{filename_base}.%(ext)s")

        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'continuedl': True,  # Resume downloads
            'nooverwrites': True,  # Don't re-download if file exists
        }

        # Add authentication
        auth_params = self.auth_manager.get_ytdlp_params()
        ydl_opts.update(auth_params)

        # Configure format based on quality and audio_only
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            # Map quality to format
            if quality == "best":
                format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == "1080p":
                format_str = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best'
            elif quality == "720p":
                format_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
            else:
                format_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best'

            ydl_opts['format'] = format_str
            ydl_opts['merge_output_format'] = 'mp4'

        # Add progress hook if callback provided
        if progress_callback:
            def progress_hook(d):
                progress_callback(d)

            ydl_opts['progress_hooks'] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_url = video.webpage_url or f"https://www.youtube.com/watch?v={video.video_id}"
                print(f"Downloading: {video.title}")
                ydl.download([video_url])

                # Update video metadata with file path
                if audio_only:
                    video.audio_path = str(output_dir / f"{filename_base}.mp3")
                else:
                    video.video_path = str(output_dir / f"{filename_base}.mp4")

                video.download_status = DownloadStatus.COMPLETED
                return True

        except Exception as e:
            print(f"Error downloading {video.title}: {e}")
            video.download_status = DownloadStatus.FAILED
            return False

    def download_playlist(
        self,
        playlist: PlaylistMetadata,
        quality: str = "1080p",
        audio_only: bool = False,
        download_metadata_only: bool = False,
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, bool]:
        """
        Download all videos in a playlist with parallel processing.

        Args:
            playlist: PlaylistMetadata object
            quality: Video quality
            audio_only: If True, download audio only
            download_metadata_only: If True, only save metadata without downloading videos
            max_workers: Override default max_workers
            progress_callback: Optional callback(video_id, progress_dict)

        Returns:
            Dictionary mapping video_id to success status
        """
        output_dir = self.get_playlist_download_dir(playlist)

        if download_metadata_only:
            print(f"Metadata-only mode: Saving playlist data without downloading videos")
            self.storage.update_playlist(playlist)
            self.storage.save_playlist(playlist)
            return {}

        # Filter videos that need to be downloaded
        videos_to_download = [
            video for video in playlist.videos.values()
            if video.status == VideoStatus.LIVE
            and video.download_status != DownloadStatus.COMPLETED
        ]

        if not videos_to_download:
            print("No videos to download")
            return {}

        print(f"Downloading {len(videos_to_download)} videos to: {output_dir}")
        print(f"Using {max_workers or self.max_workers} parallel downloads")

        results = {}

        # Create progress callbacks for each video
        def make_progress_callback(video_id: str):
            def callback(d):
                if progress_callback:
                    progress_callback(video_id, d)
            return callback

        # Download videos in parallel
        workers = max_workers or self.max_workers
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all download tasks
            future_to_video = {
                executor.submit(
                    self.download_video,
                    video,
                    output_dir,
                    quality,
                    audio_only,
                    make_progress_callback(video.video_id)
                ): video
                for video in videos_to_download
            }

            # Process completed downloads
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    success = future.result()
                    results[video.video_id] = success

                    # Update storage after each download
                    self.storage.save_playlist(playlist, create_version=False)

                except Exception as e:
                    print(f"Exception downloading {video.title}: {e}")
                    results[video.video_id] = False
                    video.download_status = DownloadStatus.FAILED

        # Save final state with version
        self.storage.save_playlist(playlist, create_version=True)

        # Print summary
        successful = sum(1 for success in results.values() if success)
        print(f"\nDownload complete: {successful}/{len(results)} videos successful")

        return results

    def download_videos_by_ids(
        self,
        playlist: PlaylistMetadata,
        video_ids: List[str],
        quality: str = "1080p",
        audio_only: bool = False
    ) -> Dict[str, bool]:
        """
        Download specific videos from a playlist.

        Args:
            playlist: PlaylistMetadata object
            video_ids: List of video IDs to download
            quality: Video quality
            audio_only: If True, download audio only

        Returns:
            Dictionary mapping video_id to success status
        """
        output_dir = self.get_playlist_download_dir(playlist)

        # Filter to requested videos
        videos_to_download = [
            playlist.videos[vid_id]
            for vid_id in video_ids
            if vid_id in playlist.videos
        ]

        if not videos_to_download:
            print("No matching videos found")
            return {}

        print(f"Downloading {len(videos_to_download)} specific videos")

        results = {}

        for video in videos_to_download:
            success = self.download_video(video, output_dir, quality, audio_only)
            results[video.video_id] = success

        # Save updated playlist
        self.storage.save_playlist(playlist)

        return results
